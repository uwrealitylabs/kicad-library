#!/usr/bin/env python3
"""Wire this library into a KiCad project: write (or merge into) the project's sym-lib-table and fp-lib-table.

    python3 kicad-library/scripts/libtables.py <project dir>      # the folder that holds the .kicad_pro
    python3 kicad-library/scripts/libtables.py --print             # just show the rows

Every UWRL_* library gets one row, URI = ${KIPRJMOD}/kicad-library/..., so the tables work on any machine
that cloned the project with the submodule. Existing rows for other libraries are kept; UWRL rows are
rewritten. Re-run after pulling a library update that adds a category.
"""
import pathlib, re, sys

LIB = pathlib.Path(__file__).resolve().parents[1]
SUB = "kicad-library"          # the submodule directory name inside the project


def rows(kind):
    if kind == "sym":
        libs = sorted(p.stem for p in LIB.glob("symbols/UWRL_*.kicad_sym"))
        return [f'  (lib (name "{n}")(type "KiCad")(uri "${{KIPRJMOD}}/{SUB}/symbols/{n}.kicad_sym")(options "")(descr "UWRL library"))' for n in libs]
    libs = sorted(p.name[:-7] for p in LIB.glob("footprints/UWRL_*.pretty"))
    return [f'  (lib (name "{n}")(type "KiCad")(uri "${{KIPRJMOD}}/{SUB}/footprints/{n}.pretty")(options "")(descr "UWRL library"))' for n in libs]


def table(kind, existing=""):
    head = "sym_lib_table" if kind == "sym" else "fp_lib_table"
    keep = []
    for line in existing.splitlines():
        s = line.strip()
        if s.startswith("(lib ") and not re.search(r'\(name "UWRL_', s):
            keep.append("  " + s)
    return f"({head}\n  (version 7)\n" + "\n".join(keep + rows(kind)) + "\n)\n"


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 2
    if argv[0] == "--print":
        print(table("sym")); print(table("fp")); return 0
    proj = pathlib.Path(argv[0]).resolve()
    if not list(proj.glob("*.kicad_pro")):
        print(f"{proj}: no .kicad_pro here; pass the folder that holds the project file"); return 1
    if not (proj / SUB).is_dir():
        print(f"{proj}/{SUB} is missing: run  git submodule add https://github.com/uwrealitylabs/kicad-library {SUB}"); return 1
    for kind, name in (("sym", "sym-lib-table"), ("fp", "fp-lib-table")):
        f = proj / name
        f.write_text(table(kind, f.read_text() if f.exists() else ""))
        print("wrote", f)
    print("Restart KiCad (or re-open the project) so it re-reads the tables.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
