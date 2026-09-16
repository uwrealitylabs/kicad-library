"""Markdown (the subset used in docs/onboarding) -> Notion API block objects.

convert(text, resolve_link, image_block) -> list of blocks. Keys starting with "_" are local metadata
(strip_meta removes them before an API call): "_only_link" marks a list item that is nothing but one link.

resolve_link(href) -> {"page_id": id} | {"url": url} | None      (None: keep the text, drop the link)
image_block(path, caption_rich_text) -> an image block dict        (path relative to the markdown file)
"""
import re

RICH_LIMIT = 2000
LANGUAGES = {"sh": "shell", "bash": "shell", "zsh": "shell", "shell": "shell", "console": "shell",
             "py": "python", "python": "python", "json": "json", "yaml": "yaml", "yml": "yaml",
             "powershell": "powershell", "ps1": "powershell", "text": "plain text", "txt": "plain text",
             "": "plain text", "diff": "diff", "html": "html", "css": "css", "js": "javascript",
             "javascript": "javascript", "c": "c", "cpp": "c++", "toml": "toml", "ini": "plain text",
             "lisp": "plain text", "kicad": "plain text", "scheme": "plain text"}
INLINE = re.compile(r"(?P<code>`[^`\n]+`)"
                    r"|(?P<link>\[(?P<ltext>[^\]\n]*)\]\((?P<href>[^)\s]+)\))"
                    r"|(?P<auto><(?P<aurl>https?://[^>\s]+)>)"
                    r"|(?P<bold>\*\*(?P<btext>[^*\n]+?)\*\*)"
                    r"|(?P<ital>(?<![\w*])[*_](?P<itext>[^*_\n]+?)[*_](?![\w*]))")
IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\)\s*$")
LIST = re.compile(r"^(?P<indent>\s*)(?:(?P<bullet>[-*])|(?P<num>\d+)[.)])\s+(?P<body>.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def _text(content, link=None, **ann):
    obj = {"type": "text", "text": {"content": content, "link": ({"url": link} if link else None)}}
    ann = {k: v for k, v in ann.items() if v}
    if ann:
        obj["annotations"] = ann
    return obj


def _split_long(items):
    out = []
    for it in items:
        if it["type"] != "text" or len(it["text"]["content"]) <= RICH_LIMIT:
            out.append(it)
            continue
        s = it["text"]["content"]
        for i in range(0, len(s), RICH_LIMIT):
            piece = dict(it)
            piece["text"] = dict(it["text"], content=s[i:i + RICH_LIMIT])
            out.append(piece)
    return out


def rich(text, resolve_link, **ann):
    """Inline markdown -> Notion rich_text array."""
    out, pos = [], 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            out.append(_text(text[pos:m.start()], **ann))
        if m.group("code"):
            out.append(_text(m.group("code")[1:-1], code=True, **ann))
        elif m.group("link"):
            target = resolve_link(m.group("href"))
            if target and "page_id" in target:
                out.append({"type": "mention", "mention": {"type": "page", "page": {"id": target["page_id"]}}})
            elif target and "url" in target:
                out.extend(rich(m.group("ltext"), resolve_link, link=target["url"], **ann) if "link" not in ann
                           else rich(m.group("ltext"), resolve_link, **ann))
            else:
                out.extend(rich(m.group("ltext"), resolve_link, **ann))
        elif m.group("auto"):   # <https://…>: a link whose text is the address without scheme or trailing slash
            url = m.group("aurl")
            shown = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
            out.append(_text(shown, link=None if "link" in ann else url, **ann))
        elif m.group("bold"):
            out.extend(rich(m.group("btext"), resolve_link, bold=True, **{k: v for k, v in ann.items() if k != "bold"}))
        elif m.group("ital"):
            out.extend(rich(m.group("itext"), resolve_link, italic=True, **{k: v for k, v in ann.items() if k != "italic"}))
        pos = m.end()
    if pos < len(text):
        out.append(_text(text[pos:], **ann))
    return _split_long([o for o in out if o["type"] != "text" or o["text"]["content"]])


def _block(kind, rt, **extra):
    body = {"rich_text": rt}
    body.update(extra)
    return {"object": "block", "type": kind, kind: body}


def _code_block(lines, lang):
    src = "\n".join(lines)
    chunks = [src[i:i + RICH_LIMIT] for i in range(0, max(len(src), 1), RICH_LIMIT)] or [""]
    return {"object": "block", "type": "code",
            "code": {"rich_text": [_text(c) for c in chunks], "language": LANGUAGES.get(lang.lower(), "plain text")}}


def _table(rows, resolve_link):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c or "-") for c in r)]
    width = max(len(r) for r in cells)
    children = [{"object": "block", "type": "table_row",
                 "table_row": {"cells": [rich(c, resolve_link) or [_text(" ")] for c in (r + [""] * (width - len(r)))]}}
                for r in cells]
    return {"object": "block", "type": "table",
            "table": {"table_width": width, "has_column_header": True, "has_row_header": False, "children": children}}


def convert(text, resolve_link, image_block):
    lines = text.splitlines()
    blocks, para, i = [], [], 0

    def flush():
        if para:
            blocks.append(_block("paragraph", rich(" ".join(s.strip() for s in para), resolve_link)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            flush()
            lang, j = s[3:].strip(), i + 1
            body = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                body.append(lines[j])
                j += 1
            blocks.append(_code_block(body, lang))
            i = j + 1
            continue
        if not s:
            flush()
            i += 1
            continue
        h = HEADING.match(line)
        if h:
            flush()
            level = min(len(h.group(1)), 3)
            blocks.append(_block(f"heading_{level}", rich(h.group(2), resolve_link)))
            i += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            flush()
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue
        im = IMAGE.match(s)
        if im:
            flush()
            caption, j = [], i + 1
            if j < len(lines) and re.fullmatch(r"[*_][^*_].*[*_]", lines[j].strip()):
                caption = rich(lines[j].strip()[1:-1], resolve_link)
                j += 1
            blocks.append(image_block(im.group("src"), caption))
            i = j
            continue
        if s.startswith(">"):
            flush()
            quote, j = [], i
            while j < len(lines) and lines[j].strip().startswith(">"):
                quote.append(lines[j].strip()[1:].strip())
                j += 1
            blocks.append(_block("callout", rich(" ".join(q for q in quote if q), resolve_link),
                                 icon={"type": "emoji", "emoji": "💡"}))
            i = j
            continue
        if s.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            flush()
            rows, j = [], i
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(lines[j])
                j += 1
            blocks.append(_table(rows, resolve_link))
            i = j
            continue
        lm = LIST.match(line)
        if lm:
            flush()
            j, parent = i, None
            while j < len(lines):
                m = LIST.match(lines[j])
                if not m:
                    if lines[j].strip() and lines[j].startswith("  ") and parent is not None:  # wrapped item text
                        tgt = parent[parent["type"]]
                        tgt["rich_text"] = _split_long(tgt["rich_text"] + rich(" " + lines[j].strip(), resolve_link))
                        j += 1
                        continue
                    break
                kind = "bulleted_list_item" if m.group("bullet") else "numbered_list_item"
                body = m.group("body").strip()
                item = _block(kind, rich(body, resolve_link))
                only = re.fullmatch(r"\[[^\]]+\]\(([^)\s]+)\)", body)
                if only:
                    item["_only_link"] = only.group(1)
                if len(m.group("indent")) >= 2 and parent is not None:
                    parent[parent["type"]].setdefault("children", []).append(item)
                else:
                    blocks.append(item)
                    parent = item
                j += 1
            i = j
            continue
        para.append(line)
        i += 1
    flush()
    return blocks


def strip_meta(block):
    if isinstance(block, dict):
        return {k: strip_meta(v) for k, v in block.items() if not k.startswith("_")}
    if isinstance(block, list):
        return [strip_meta(b) for b in block]
    return block


def plain(block):
    """First line of text in a block, for --dry-run listings."""
    body = block.get(block["type"], {})
    parts = []
    for r in body.get("rich_text", []) or body.get("caption", []):
        parts.append(r.get("plain_text") or (r["text"]["content"] if r["type"] == "text" else "@page"))
    if block["type"] == "table":
        parts.append(f"{body['table_width']} cols x {len(body['children'])} rows")
    if block["type"] == "image":
        parts.insert(0, body.get("_path", body.get("file_upload", {}).get("id", "")))
    return "".join(parts).replace("\n", " ")
