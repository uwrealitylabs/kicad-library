#!/usr/bin/env python3
"""Validate the UWRL KiCad library: every link resolves, every name is unique, every part is identified.

    python3 scripts/validate.py [--strict]

Errors (exit 1): dangling footprint links, dangling 3D model paths, duplicate symbol names, files KiCad 10
cannot parse (when kicad-cli is installed), model paths that are not ${KIPRJMOD}/kicad-library/3dmodels/...
Warnings: missing Datasheet / LCSC / MPN property, shop-page datasheet links, footprints without a courtyard
or a 3D model.  --strict turns warnings into errors.
"""
import argparse, os, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREFIX = "UWRL_"
MODEL_PREFIX = "${KIPRJMOD}/kicad-library/3dmodels/"
STOCK_FOOTPRINTS = [pathlib.Path(p) for p in (
    os.environ.get("KICAD_STOCK_FOOTPRINTS", ""), "/usr/share/kicad/footprints",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
    "C:/Program Files/KiCad/10.0/share/kicad/footprints") if p]
SHOP_RE = re.compile(r"(szlcsc\.com|lcsc\.com/product|jlcpcb\.com/parts|digikey\.[a-z.]+/en/products|mouser\.[a-z]+/ProductDetail)", re.I)


def blocks(text):
    """(head, block) for each top-level child of the root s-expression."""
    i = text.index("(") + 1
    depth, out, start, in_str, j = 0, [], None, False, i
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            if depth == 0:
                start = j
            depth += 1
        elif c == ")":
            if depth == 0:
                break
            depth -= 1
            if depth == 0:
                blk = text[start:j + 1]
                out.append((re.match(r"\(\s*([A-Za-z_]+)", blk).group(1), blk))
        j += 1
    return out


def prop(block, name):
    m = re.search(r'\(property\s+"%s"\s+"((?:[^"\\]|\\.)*)"' % re.escape(name), block)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="warnings fail the run")
    a = ap.parse_args()
    errors, warnings = [], []
    stock = next((p for p in STOCK_FOOTPRINTS if p.is_dir()), None)

    footprints = {}
    for pretty in sorted(ROOT.glob("footprints/*.pretty")):
        if not pretty.name.startswith(PREFIX):
            errors.append(f"{pretty.relative_to(ROOT)}: library name must start with {PREFIX}")
        for mod in sorted(pretty.glob("*.kicad_mod")):
            footprints[f"{pretty.name[:-7]}:{mod.stem}"] = mod
            rel = mod.relative_to(ROOT)
            text = mod.read_text(errors="replace")
            m = re.match(r'\(footprint\s+"((?:[^"\\]|\\.)*)"', text)
            if not m:
                errors.append(f"{rel}: not in current KiCad footprint format (run: kicad-cli fp upgrade --force {pretty.name})")
            elif m.group(1) != mod.stem:
                errors.append(f"{rel}: internal name {m.group(1)!r} != file name")
            models = re.findall(r'\(model\s+"((?:[^"\\]|\\.)*)"', text)
            if not models:
                warnings.append(f"{rel}: no 3D model")
            for mp in models:
                if not mp.startswith(MODEL_PREFIX):
                    errors.append(f"{rel}: model path must start with {MODEL_PREFIX} (got {mp})")
                elif not (ROOT / "3dmodels" / mp[len(MODEL_PREFIX):]).is_file():
                    errors.append(f"{rel}: model file missing: {mp}")
            if "F.CrtYd" not in text and "B.CrtYd" not in text:
                warnings.append(f"{rel}: no courtyard")

    for lib in sorted(ROOT.glob("symbols/*.kicad_sym")):
        nick = lib.stem
        rel = lib.relative_to(ROOT)
        if not nick.startswith(PREFIX):
            errors.append(f"{rel}: library name must start with {PREFIX}")
        text = lib.read_text(errors="replace")
        if not re.search(r"\(version 2025\d{4}\)", text):
            errors.append(f"{rel}: not in KiCad 10 format (run: kicad-cli sym upgrade --force {lib.name})")
        seen = set()
        for head, blk in blocks(text):
            if head != "symbol":
                continue
            name = re.match(r'\(symbol\s+"((?:[^"\\]|\\.)*)"', blk).group(1)
            where = f"{nick}:{name}"
            if name in seen:
                errors.append(f"{where}: duplicate symbol name in {lib.name}")
            seen.add(name)
            if re.match(r'\(symbol\s+"[^"]*"\s*\(extends', blk):
                continue
            if nick == PREFIX + "Power":
                continue  # power symbols carry no footprint or part number
            fp = prop(blk, "Footprint") or ""
            if not fp:
                errors.append(f"{where}: empty Footprint property")
            elif ":" not in fp:
                errors.append(f"{where}: Footprint {fp!r} is not LIB:NAME")
            else:
                fnick, fname = fp.split(":", 1)
                if fnick.startswith(PREFIX):
                    if fp not in footprints:
                        errors.append(f"{where}: footprint {fp} not in this library")
                elif stock is not None:
                    if not (stock / f"{fnick}.pretty" / f"{fname}.kicad_mod").is_file():
                        errors.append(f"{where}: stock footprint {fp} not found under {stock}")
                else:
                    warnings.append(f"{where}: stock footprint {fp} not checked (no KiCad install found)")
            ds = prop(blk, "Datasheet") or ""
            if not ds or ds == "~":
                warnings.append(f"{where}: no Datasheet")
            elif SHOP_RE.search(ds):
                warnings.append(f"{where}: Datasheet is a shop page, link the manufacturer PDF: {ds}")
            if not (prop(blk, "LCSC") or prop(blk, "LCSC Part") or prop(blk, "MPN")):
                warnings.append(f"{where}: no LCSC / MPN property (how will it be ordered?)")

    kicad_cli = shutil.which("kicad-cli")
    if kicad_cli:
        tmp = ROOT / ".validate-tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        (tmp / "sym").mkdir(parents=True)
        for lib in sorted(ROOT.glob("symbols/*.kicad_sym")):
            r = subprocess.run([kicad_cli, "sym", "upgrade", "--force", "-o", str(tmp / "sym" / lib.name), str(lib)], capture_output=True, text=True)
            if r.returncode:
                errors.append(f"{lib.relative_to(ROOT)}: kicad-cli cannot load it: {(r.stdout + r.stderr).strip()[-300:]}")
        for pretty in sorted(ROOT.glob("footprints/*.pretty")):
            r = subprocess.run([kicad_cli, "fp", "upgrade", "--force", "-o", str(tmp / pretty.name), str(pretty)], capture_output=True, text=True)
            if r.returncode:
                errors.append(f"{pretty.relative_to(ROOT)}: kicad-cli cannot load it: {(r.stdout + r.stderr).strip()[-300:]}")
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        warnings.append("kicad-cli not installed: parse check skipped")

    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{sum(1 for _ in ROOT.glob('symbols/*.kicad_sym'))} symbol libraries, {len(footprints)} footprints, "
          f"{sum(1 for _ in ROOT.glob('3dmodels/*/*'))} 3D models: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors or (a.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
