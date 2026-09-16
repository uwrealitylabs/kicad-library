#!/usr/bin/env python3
"""Overwrite guard for notion_publish.py.

The markdown is the source of truth, but people edit Notion directly. Before `--update` replaces a
page body, this module (1) fingerprints what Notion holds now and compares it with what the publisher
wrote last time, (2) writes a JSON backup of the current blocks, and (3) can print a text diff between
the Notion page and the markdown so edits made in Notion can be carried back into the repo.

    fingerprint(client, page_id)          -> sha256 of the page text (child pages excluded)
    snapshot(client, page_id, key)        -> backup file path (~/.local/state/notion/backups/)
    text_diff(client, page_id, blocks)    -> unified diff, Notion (a) vs markdown (b); "" when equal
"""
import difflib, hashlib, json, pathlib, time

BACKUPS = pathlib.Path.home() / ".local/state/notion/backups"
SKIP = ("child_page", "child_database")


def _rich_text(rt):
    out = []
    for r in rt or []:
        if r.get("type") == "text":
            out.append(r.get("plain_text") or r["text"].get("content", ""))
        elif r.get("type") == "mention":
            out.append("@page")
        else:
            out.append(r.get("plain_text", ""))
    return "".join(out)


def block_lines(blocks, client=None, depth=0):
    """One text line per block: 'type: text'. Nested children (tables, nested lists) are included."""
    lines = []
    for b in blocks:
        t = b["type"]
        if t in SKIP:
            continue
        body = b.get(t, {})
        if t == "table_row":
            text = " | ".join(_rich_text(c) for c in body.get("cells", []))
        elif t == "image":
            text = "[image] " + _rich_text(body.get("caption"))
        elif t == "code":
            text = _rich_text(body.get("rich_text"))
        else:
            text = _rich_text(body.get("rich_text"))
        lines.append("  " * depth + f"{t}: {text}")
        kids = body.get("children") or b.get("children")
        if kids is None and client is not None and b.get("has_children") and depth < 3:
            kids = client.children(b["id"])
        if kids:
            lines += block_lines(kids, client, depth + 1)
    return lines


def page_lines(client, page_id):
    return block_lines(client.children(page_id), client)


def fingerprint(client, page_id):
    return hashlib.sha256("\n".join(page_lines(client, page_id)).encode()).hexdigest()


def snapshot(client, page_id, key):
    """Dump the page's current blocks (with nested children) to a backup file before they are deleted."""
    BACKUPS.mkdir(parents=True, exist_ok=True)
    BACKUPS.chmod(0o700)
    blocks = client.children(page_id)
    for b in blocks:
        if b.get("has_children") and b["type"] not in SKIP:
            b["children"] = client.children(b["id"])
    path = BACKUPS / f"{time.strftime('%Y%m%dT%H%M%S')}-{key.replace('.md', '')}.json"
    path.write_text(json.dumps({"page_id": page_id, "blocks": blocks}, indent=1))
    path.chmod(0o600)
    return path


def text_diff(client, page_id, blocks, key=""):
    a = page_lines(client, page_id)
    b = block_lines(blocks)
    return "".join(difflib.unified_diff(a, b, fromfile=f"notion/{key}", tofile=f"markdown/{key}", lineterm="\n"))
