# Contributing a part

One pull request per part (or per tightly related set, e.g. a connector family). The reviewer opens your
symbol and footprint next to the datasheet; make that comparison easy.

## Before you draw anything

1. **Stock first.** Search the stock KiCad libraries (Add Symbol → type the part number or package). If stock
   has the exact part, use it; nothing to submit. If stock has the *package* (footprint) but not the symbol,
   submit only the symbol and link the stock footprint.
2. **Library second.** Search `UWRL_*`. If it exists, use it. If it exists but is wrong, fix it in the same PR
   and say what was wrong.
3. **Datasheet open.** You will copy pin names, pin numbers, the package drawing and the recommended land
   pattern from it. Save the manufacturer's PDF link; a distributor product page is not a datasheet.

## Symbol (`symbols/UWRL_<Category>.kicad_sym`)

- Name = the manufacturer part number as ordered (`AP2112K-3.3`), no vendor suffixes like `TRG1` unless the
  suffix changes the part. Reference `U` for ICs, `J` connectors, `R`/`C`/`L`, `D`, `Q`, `Y` crystals, `SW`.
- Pins on the **50 mil (1.27 mm) grid**, pin numbers exactly as the datasheet, names as the datasheet.
- Electrical types set for real: `power_in` for supply pins, `power_out` for regulator outputs, `input` /
  `output` / `bidirectional` / `passive` / `open_collector` / `no_connect`. ERC uses them.
- Layout: supplies at the top, GND at the bottom, inputs on the left, outputs on the right. Group by function,
  not by pin number. A symbol is read, not soldered.
- Properties: `Footprint` (`UWRL_X:name` or a stock `Lib:name`), `Datasheet` (manufacturer PDF URL),
  `Manufacturer`, `MPN`, `LCSC` (the `C` number if JLCPCB stocks it), `Description` (one line: what it is,
  key rating, package). Hide the fields that should not print on the schematic.
- Run the Symbol Editor's checker (Inspect → Symbol Checker): zero messages.

## Footprint (`footprints/UWRL_<Category>.pretty/`)

- Name = the package as the datasheet calls it, plus the part number if the land pattern is part-specific
  (`SOT-23-5`, `QFN-32_5x5_P0.5_AP33772`, `XF2M-3015-1A`).
- Pads from the datasheet's **recommended land pattern**, not measured off the package drawing. Pad numbers
  match the symbol pin numbers; expose every pad including thermal and mechanical pads.
- Layers: pads on `F.Cu`/`F.Paste`/`F.Mask`; outline on `F.Fab`; silkscreen that does not overlap pads and
  marks pin 1; a closed **courtyard** on `F.CrtYd` (0.25 mm outside the body/pads); `%R` reference on `F.Fab`
  and `F.SilkS`.
- 3D model: STEP in `3dmodels/UWRL_<Category>.3dshapes/`, linked as
  `${KIPRJMOD}/kicad-library/3dmodels/UWRL_<Category>.3dshapes/<file>.step`, aligned to the pads (check in the
  3D viewer). Manufacturer STEP preferred; JLCPCB/EasyEDA bodies are acceptable if dimensions match.
- Run the Footprint Editor's checker (Inspect → Footprint Checker): zero messages.

## The pull request

```sh
git checkout -b part/ap2112k-3.3
python3 scripts/validate.py          # must print 0 errors
git add symbols footprints 3dmodels
git commit -m "add AP2112K-3.3 (Diodes, SOT-23-5 LDO) with footprint and STEP"
git push -u origin part/ap2112k-3.3
```

Open the PR on GitHub; the template asks for the datasheet link and the page you took the pinout and land
pattern from. CI runs `scripts/validate.py`. A team member reviews against the datasheet and merges. Then
bump the submodule in your project (`cd kicad-library && git pull origin main`).

## Review checklist (what the reviewer looks at)

- [ ] pin numbers and names match the datasheet pin table, electrical types are real
- [ ] footprint pads match the recommended land pattern; pad numbers match the symbol
- [ ] courtyard closed, pin 1 marked, nothing on the wrong layer
- [ ] STEP aligned in the 3D viewer, path is `${KIPRJMOD}/kicad-library/3dmodels/...`
- [ ] `Datasheet` is the manufacturer PDF; `MPN`, `Manufacturer`, `LCSC` filled
- [ ] `scripts/validate.py` green in CI
