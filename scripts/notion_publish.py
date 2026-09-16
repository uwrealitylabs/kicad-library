#!/usr/bin/env python3
"""Publish docs/onboarding/*.md to the team Notion as "KiCad Onboarding" in the Hardware: Wiki database.

    python3 scripts/notion_publish.py --dry-run          # what would be created; one read-only API call (users/me)
    python3 scripts/notion_publish.py --publish          # create the page tree, upload the screenshots
    python3 scripts/notion_publish.py --update           # re-sync bodies of the pages recorded in .notion-pages.json
    python3 scripts/notion_publish.py --diff             # what differs between Notion and the markdown (read-only)
    python3 scripts/notion_publish.py --update --force   # overwrite pages that were edited in Notion since the last sync

--update refuses to touch a page whose text changed in Notion since the publisher last wrote it (someone edited
it there). Run --diff, carry the edits into the markdown, then --update --force. Every --update writes a JSON
backup of each page to ~/.local/state/notion/backups/ before deleting anything.

Token: ~/.local/state/notion/kicad-onboarding.token (0600, never printed). The index page body is the README
with its list of numbered docs replaced by the child pages themselves; links between docs become page mentions;
links to other repo files become GitHub links. Page ids are stored in docs/onboarding/.notion-pages.json.
"""
import json, mimetypes, os, pathlib, posixpath, re, sys, time, urllib.error, urllib.request, uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from notion_markdown import convert, plain, rich, strip_meta  # noqa: E402
import notion_guard as guard  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_DIR = pathlib.Path(os.environ.get("KICAD_ONBOARDING_DOCS", ROOT / "docs" / "onboarding"))  # override for tests
STATE = DOCS_DIR / ".notion-pages.json"
TOKEN_FILE = pathlib.Path.home() / ".local/state/notion/kicad-onboarding.token"
API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
DATABASE_ID = "110bc072-402f-800a-a2c4-ea9eda959e8c"      # Hardware: Wiki
OWNER_ID = "110d872b-594c-81f5-9c47-0002be31bff8"         # Vincent Xie
REPO_BLOB = "https://github.com/uwrealitylabs/kicad-library/blob/main/"
INDEX_TITLE = "KiCad Onboarding"
TIME_TO_COMPLETION = "3 to 5 hours"
DOCS = [("01-setup.md", "1: Setup"), ("02-finding-parts.md", "2: Finding parts"),
        ("03-making-a-symbol.md", "3: Making a symbol"), ("04-making-a-footprint.md", "4: Making a footprint"),
        ("05-submitting-a-part.md", "5: Submitting a part"), ("06-using-the-part.md", "6: Using the part")]
ICON = {"type": "icon", "icon": {"name": "chip", "color": "blue"}}
ICON_FALLBACK = {"type": "emoji", "emoji": "🟦"}
CHUNK = 100


class Notion:
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def call(self, method, path, body=None, raw=None, content_type="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Notion-Version": VERSION, "Content-Type": content_type})
        for attempt in range(4):
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:400]
                if e.code == 429 or e.code >= 500:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from None
        raise RuntimeError(f"{method} {path}: gave up after retries")

    def me(self):
        return self.call("GET", "/users/me")

    def upload(self, path):
        path = pathlib.Path(path)
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        up = self.call("POST", "/file_uploads", {"filename": path.name, "content_type": ctype})
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        self.call("POST", f"/file_uploads/{up['id']}/send", raw=body, content_type=f"multipart/form-data; boundary={boundary}")
        return up["id"]

    def create_page(self, parent, properties, icon=ICON):
        body = {"parent": parent, "properties": properties}
        if icon:
            body["icon"] = icon
        try:
            return self.call("POST", "/pages", body)
        except RuntimeError as e:
            if "icon" not in str(e) or icon == ICON_FALLBACK:
                raise
            body["icon"] = ICON_FALLBACK
            return self.call("POST", "/pages", body)

    def append(self, block_id, blocks):
        for i in range(0, len(blocks), CHUNK):
            self.call("PATCH", f"/blocks/{block_id}/children", {"children": strip_meta(blocks[i:i + CHUNK])})

    def children(self, block_id):
        out, cursor = [], None
        while True:
            res = self.call("GET", f"/blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else ""))
            out += res["results"]
            if not res.get("has_more"):
                return out
            cursor = res["next_cursor"]

    def delete_children(self, block_id, keep_types=("child_page",)):
        for b in self.children(block_id):
            if b["type"] not in keep_types:
                self.call("DELETE", f"/blocks/{b['id']}")


def link_resolver(ids):
    """href in a docs/onboarding markdown file -> Notion target."""
    def resolve(href):
        if re.match(r"^(https?:|mailto:)", href):
            return {"url": href}
        if href.startswith("#"):
            return None
        target, _, anchor = href.partition("#")
        name = posixpath.basename(target)
        if name in ids:
            return {"page_id": ids[name]}
        rel = posixpath.normpath(posixpath.join("docs/onboarding", target))
        return {"url": REPO_BLOB + rel + (f"#{anchor}" if anchor else "")}
    return resolve


def convert_doc(path, ids, uploads, dry):
    """(blocks, image_paths). In dry mode images get a placeholder id; in publish mode they are uploaded."""
    images = []

    def image_block(src, caption):
        p = (path.parent / src).resolve()
        images.append(p)
        if not p.is_file():
            raise SystemExit(f"{path.name}: image not found: {src}")
        if dry:
            fid = "DRY-RUN"
        else:
            if str(p) not in uploads:
                uploads[str(p)] = uploads["_client"].upload(p)
            fid = uploads[str(p)]
        return {"object": "block", "type": "image", "_path": src,
                "image": {"type": "file_upload", "file_upload": {"id": fid}, "caption": caption}}

    return convert(path.read_text(encoding="utf-8"), link_resolver(ids), image_block), images


def split_index(blocks, child_names):
    """README blocks -> (before, after) around the list of numbered docs (that list becomes the child pages)."""
    def is_doc_link(b):
        href = b.get("_only_link", "")
        return posixpath.basename(href.partition("#")[0]) in child_names
    start = next((i for i, b in enumerate(blocks) if is_doc_link(b)), None)
    if start is None:
        return blocks, []
    end = start
    while end < len(blocks) and is_doc_link(blocks[end]):
        end += 1
    return blocks[:start], blocks[end:]


def title_prop(text):
    return {"title": [{"type": "text", "text": {"content": text}}]}


def show(name, blocks, images):
    print(f"\n== {name}: {len(blocks)} blocks, {len(images)} images")
    for b in blocks:
        print(f"  {b['type']:19s} {plain(b)[:60]}")
    for p in images:
        print(f"  image {'ok     ' if p.is_file() else 'MISSING'} {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}")


def main(argv):
    mode = argv[0] if argv else "--dry-run"
    force = "--force" in argv[1:]
    if mode not in ("--dry-run", "--publish", "--update", "--diff"):
        print(__doc__)
        return 2
    dry = mode == "--dry-run"
    docs = [DOCS_DIR / "README.md"] + [DOCS_DIR / f for f, _ in DOCS]
    missing = [d.name for d in docs if not d.is_file()]
    if missing:
        print("missing markdown:", ", ".join(missing))
        return 1
    client = Notion(TOKEN_FILE.read_text().strip())
    me = client.me()
    print(f"token ok: {me.get('name')} in {me.get('bot', {}).get('workspace_name')}")
    child_names = {f for f, _ in DOCS}
    state = json.loads(STATE.read_text()) if STATE.is_file() else {}
    if mode in ("--update", "--diff") and not state.get("index"):
        print(f"{STATE}: no recorded pages; run --publish first")
        return 1
    ids = dict(state.get("children", {})) if mode in ("--update", "--diff") else {}
    uploads = {"_client": client}

    if dry:
        total = 0
        for d in docs:
            blocks, images = convert_doc(d, ids, uploads, dry=True)
            if d.name == "README.md":
                before, after = split_index(blocks, child_names)
                print(f"\n(index page: {len(before)} blocks before the child pages, {len(after)} after)")
            show(d.name, blocks, images)
            total += len(blocks)
        print(f"\n{len(docs)} pages, {total} blocks; no writes performed")
        return 0

    pages = [("README.md", state.get("index"))] + [(f, state.get("children", {}).get(f)) for f, _ in DOCS]
    if mode == "--diff":
        for key, pid in pages:
            blocks, _ = convert_doc(DOCS_DIR / key, ids, uploads, dry=True)
            if key == "README.md":
                before, after = split_index(blocks, child_names)
                blocks = before + after
            d = guard.text_diff(client, pid, blocks, key)
            print(d if d else f"== {key}: Notion matches the markdown")
        return 0

    if mode == "--update":   # refuse to overwrite a page somebody edited in Notion; back everything up first
        stale = []
        for key, pid in pages:
            now = guard.fingerprint(client, pid)
            was = state.get("fingerprints", {}).get(key)
            if now != was:
                stale.append((key, "no fingerprint recorded" if was is None else "edited in Notion since the last sync"))
        if stale and not force:
            for key, why in stale:
                print(f"REFUSING {key}: {why}")
            print("run --diff, carry the Notion edits into the markdown, then --update --force")
            return 1
        for key, pid in pages:
            print(f"backup {guard.snapshot(client, pid, key)}")

    if mode == "--publish":
        index = client.create_page({"database_id": DATABASE_ID}, {
            "Page": title_prop(INDEX_TITLE), "Tags": {"multi_select": [{"name": "Guide"}]},
            "Time to Completion": {"rich_text": rich(TIME_TO_COMPLETION, lambda h: None)},
            "Owner": {"people": [{"object": "user", "id": OWNER_ID}]}})
        state = {"index": index["id"], "index_url": index["url"], "children": {}, "urls": {}}
        readme_blocks, _ = convert_doc(DOCS_DIR / "README.md", {}, uploads, dry=False)
        before, _after = split_index(readme_blocks, child_names)
        client.append(index["id"], before)                       # intro first, then the child pages land below it
        for fname, title in DOCS:
            page = client.create_page({"page_id": index["id"]}, {"title": title_prop(title)}, icon=None)
            state["children"][fname] = page["id"]
            state["urls"][fname] = page["url"]
        ids = dict(state["children"])
        STATE.write_text(json.dumps(state, indent=1))
        readme_blocks, _ = convert_doc(DOCS_DIR / "README.md", ids, uploads, dry=False)
        _before, after = split_index(readme_blocks, child_names)
        client.append(index["id"], after)
    else:  # --update: bodies only; child pages keep their ids (links stay valid). Index text re-lands after the child list.
        ids = dict(state["children"])
        client.delete_children(state["index"])
        readme_blocks, _ = convert_doc(DOCS_DIR / "README.md", ids, uploads, dry=False)
        before, after = split_index(readme_blocks, child_names)
        client.append(state["index"], before + after)
    for fname, _title in DOCS:
        blocks, _ = convert_doc(DOCS_DIR / fname, ids, uploads, dry=False)
        if mode == "--update":
            client.delete_children(state["children"][fname])
        client.append(state["children"][fname], blocks)
        print(f"{fname}: {len(blocks)} blocks -> {state['urls'].get(fname, state['children'][fname])}")
    state["fingerprints"] = {key: guard.fingerprint(client, pid) for key, pid in
                             [("README.md", state["index"])] + [(f, state["children"][f]) for f, _ in DOCS]}
    STATE.write_text(json.dumps(state, indent=1))
    print(f"index: {state.get('index_url', state['index'])}   ({client.calls} API calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
