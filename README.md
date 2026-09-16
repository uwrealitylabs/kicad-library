# kicad-library — the Waterloo Reality Labs KiCad library

Symbols, footprints and 3D models for every Reality Labs board, in KiCad 10 format.
Boards consume it as a **git submodule** at `<project>/kicad-library`, so every project pins the exact
library commit it was designed against and every path inside the library is `${KIPRJMOD}/kicad-library/...`.

New to KiCad here? Start with **[docs/onboarding](docs/onboarding/README.md)** — install, project setup,
making a part, and getting it merged.

## Layout

| path | what |
|---|---|
| `symbols/UWRL_<Category>.kicad_sym` | one symbol library per category (`UWRL_Regulator`, `UWRL_Connector_Wire`, …) |
| `footprints/UWRL_<Category>.pretty/` | footprints, same categories |
| `3dmodels/UWRL_<Category>.3dshapes/` | STEP/WRL bodies; footprints link them as `${KIPRJMOD}/kicad-library/3dmodels/...` |
| `templates/` | KiCad project templates (`4layer-base`: the JLCPCB 4-layer stackup with our design rules) |
| `scripts/validate.py` | the check CI runs on every pull request (`python3 scripts/validate.py`) |
| `scripts/libtables.py` | writes a project's `sym-lib-table` / `fp-lib-table` rows for every UWRL library |
| `stackups/` | submodule: JLCPCB stackup definitions used by the templates |
| `docs/onboarding/` | the KiCad onboarding guide (also on the team Notion) |

Library nicknames are prefixed `UWRL_` so they never shadow the stock KiCad libraries of the same name
(`Regulator_Linear`, `Connector`, …). Stock libraries stay the first place to look for a part; this library
holds what stock does not have, checked against the datasheet by a team member.

## Use it in a project

```sh
cd <your project folder>            # the folder that holds the .kicad_pro
git submodule add https://github.com/uwrealitylabs/kicad-library kicad-library
python3 kicad-library/scripts/libtables.py .
```

Then re-open the project. Every `UWRL_*` library appears in the symbol and footprint choosers.
Cloning a project that already has the submodule: `git clone --recurse-submodules <url>`
(or `git submodule update --init` after a plain clone). Update to a newer library:
`cd kicad-library && git pull origin main && cd .. && git add kicad-library && git commit -m "bump kicad-library"`.

## Add a part

Branch, add the symbol to the right `UWRL_*` library, the footprint to the matching `.pretty`, the STEP to the
matching `.3dshapes`, run `python3 scripts/validate.py`, open a pull request. Details and the review checklist:
[CONTRIBUTING.md](CONTRIBUTING.md). The full walkthrough with screenshots: [docs/onboarding](docs/onboarding/README.md).

Migrating a project from the old `library` repo layout: [MIGRATION.md](MIGRATION.md).
