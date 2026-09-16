# Migration from the old layout (September 2026)

The repository was `uwrealitylabs/library` with one `.kicad_sym` file per part inside `<Category>__C.kicad_symdir/` folders
(KiCad has no directory symbol libraries, so every part needed its own library-table row), footprints in
`<Category>__C.pretty/`, models in `packages3d/`, and 3D paths that assumed the library sat *beside* the project (`${KIPRJMOD}/../library/`).

It is now `uwrealitylabs/kicad-library`: one library per category, consumed as a git submodule at `<project>/kicad-library`.

| now | contains |
|---|---|
| `symbols/UWRL_<Category>.kicad_sym` | one library per category, every old symbol merged in unchanged (KiCad 10 format) |
| `footprints/UWRL_<Category>.pretty/` | footprints regrouped by the same categories |
| `3dmodels/UWRL_<Category>.3dshapes/` | STEP/WRL bodies; every footprint links `${KIPRJMOD}/kicad-library/3dmodels/...` |
| `scripts/validate.py` | the check CI runs on every PR |
| `scripts/libtables.py` | writes a project's `sym-lib-table` / `fp-lib-table` rows for every UWRL library |

## Library nickname map

Old symbol `Footprint` properties and project lib tables used these nicknames. New nickname on the right.

| old nickname | new library |
|---|---|
| `Antenna__C` | `UWRL_Antenna` |
| `BEAD__C` | `UWRL_Inductor` |
| `Basic_Capacitors_Resistors__C` | `(split by part: UWRL_Resistor / UWRL_Capacitor)` |
| `CMC__C` | `UWRL_Filter` |
| `Capacitor_SMD__C` | `UWRL_Capacitor` |
| `Capacitor_THT__C` | `UWRL_Capacitor` |
| `Connector_DORABO__C` | `UWRL_Connector_Wire` |
| `Connector_FFC__C` | `UWRL_Connector` |
| `Connector_HRS_BK22__C` | `UWRL_Connector` |
| `Connector_HRS_DF40__C` | `UWRL_Connector` |
| `Connector_Pogo__C` | `UWRL_Connector` |
| `Connector_RF__C` | `UWRL_Connector` |
| `Connector_SH1.0__C` | `UWRL_Connector_Wire` |
| `Connector_USB-custom__C` | `UWRL_Connector_USB` |
| `Connector_USB__C` | `UWRL_Connector_USB` |
| `Connector_XH2.54__C` | `UWRL_Connector_Wire` |
| `Connector__C` | `UWRL_Connector` |
| `Diode__C` | `UWRL_Diode` |
| `Extended_Capacitors_Resistors__C` | `UWRL_Capacitor` |
| `HOTSWAP__C` | `UWRL_Connector` |
| `Inductor__C` | `UWRL_Inductor` |
| `Interface_CAN_LIN__C` | `UWRL_Interface` |
| `Interface_CAN__C` | `UWRL_Interface` |
| `Interface_USB__C` | `UWRL_Interface` |
| `Isolator__C` | `UWRL_Interface` |
| `LED__C` | `UWRL_LED` |
| `Logo__C` | `UWRL_Mechanical` |
| `MCU_Artery__C` | `UWRL_MCU` |
| `MCU_Espressif__C` | `UWRL_MCU` |
| `MCU_RaspberryPi__C` | `UWRL_MCU` |
| `MCU_STM32__C` | `UWRL_MCU` |
| `MCU_WCH__C` | `UWRL_MCU` |
| `MUX__C` | `UWRL_Interface` |
| `Mechanical__C` | `UWRL_Mechanical` |
| `Memory_DRAM__C` | `UWRL_Memory` |
| `Memory_Flash__C` | `UWRL_Memory` |
| `Motor_Driver__C` | `UWRL_Driver_Motor` |
| `Oscillator__C` | `UWRL_Oscillator` |
| `PMIC__C` | `UWRL_Power_Management` |
| `Power_Switch__C` | `UWRL_Power_Management` |
| `Power__C` | `UWRL_Power` |
| `Qwiic__C` | `UWRL_Connector_Wire` |
| `RES__C` | `UWRL_Resistor` |
| `Regulator_Linear__C` | `UWRL_Regulator` |
| `Regulator_Switching__C` | `UWRL_Regulator` |
| `Sensor_Motion__C` | `UWRL_Sensor` |
| `Switch__C` | `UWRL_Switch` |
| `Transistor_BJT__C` | `UWRL_Transistor` |
| `Transistor_FET__C` | `UWRL_Transistor` |
| `footprint` | `(per part, see footprints map)` |

`Basic_Capacitors_Resistors__C` and `RES__C` parts were split by what they are: `0402WGF…`/`0603WAF…`/`R0xxx` → `UWRL_Resistor`, everything else → `UWRL_Capacitor`.
Stock KiCad nicknames (`Capacitor_SMD`, `Resistor_SMD`, `Diode_SMD`, `Inductor_SMD`) are untouched.

## Updating an existing project

1. `git submodule deinit library && git rm library` then `git submodule add https://github.com/uwrealitylabs/kicad-library kicad-library` (or move a side-by-side clone into the project folder as `kicad-library`).
2. `python3 kicad-library/scripts/libtables.py .` (the folder with the `.kicad_pro`) rewrites the two lib tables.
3. In the schematic, Tools → Edit Symbol Library Links: map each old nickname to its new one with the table above (the symbol names did not change).
4. Tools → Update PCB from Schematic; footprints re-link by their new `UWRL_*:name`. 3D models resolve through the footprint, nothing to do.

## Files changed by the migration (not just moved)

- FILTER-SMD_4P-L3.2-W2.5-BL_ACT1210D-101-2P-TL00.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CAP-SMD_BD10.0-L10.3-W10.3-LS11.0-R-RD.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CAP-TH_BD10.0-P5.00-D1.0-FD.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-TH_DB125-2.54-2P-GN.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-TH_DB125-2.54-2P-GN__mirror.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-TH_DB125-2.54-3P-GN.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_4P-P0.40_BAM04-08073-0414.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_DF40C-40DP-0.4V51.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_3P-P1.00_XYECONN_XY-SH1.0-3A61.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_4P-P1.00-WT.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_4P-P1.00_XYECONN_XY-SH1.0-4A61.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_5P-P1.00_XYECONN_XY-SH1.0-5A61.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- CONN-SMD_6P-P1.00_XY-SH1.0-6A51.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- USB-C_SMD-TYPE-C-31-M-12_1.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- HDR-TH_2P-P2.50_XY-XH2.54-2A21.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- HDR-TH_3P-P2.50-H-F-W7.0-N.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- DFN1006-2L-BI.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOD-123FL_L2.7-W1.8-LS3.8-BI.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOD-123FL_L2.7-W1.8-LS3.8.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOD-323_L1.7-W1.3-LS2.6-RD.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOD-323_L1.8-W1.3-LS2.5-RD.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOT-23-6.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SMD_KEYBOARD-SW.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- IND-SMD_L3.0-W3.0_PRS3015.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- DFN-8_L3.0-W3.0-P0.65-BL-EP2.45.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- LED-SMD_4P-L2.0-W1.8_XL-0807RGBC-WS2812B.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- LED-SMD_4P-L3.2-W2.8-LS5.9_SK6812MINI-E.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- LED0603-R-RD_WHITE.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- LED0603-RD.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- UQFN-16_L2.6-W1.8-P0.40-BL.kicad_mod: downgraded nightly footprint format 20260623 -> 20251024
- SMD_BD5.6-D3.6.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- VQFN-40_L7.0-W5.0-P0.50-BL-EP5.7.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- X322512MSB4SI.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- AMS1117-3.3.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOT-23-3_L2.9-W1.6-P1.90-LS2.8-BR.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- VQFN-20_L5.0-W5.0-P0.65-TL-EP.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- DFN3L(1.6x1.6x0.5).kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SW-SMD_4P-L5.2-W5.2-1.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SW-SMD_SKSGAAE010.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- SOT-23-3_L2.9-W1.6-P1.90-LS2.8-BR.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- DFN-8_L3.2-W3.1-P0.65-LS3.4-BL-EP.kicad_mod: downgraded nightly footprint format 20260206 -> 20251024
- footprints/packages3d: not a .pretty library, skipped (2 entries)
- CPG151101S11-16_C41430893.kicad_sym: downgraded nightly file format 20260629 -> 20251024 (dropped in_pos_files)
- symbol TPS7A4700: removed embedded datasheet, Datasheet -> https://www.ti.com/lit/ds/symlink/tps7a4700.pdf
- symbol TS-1187A-B-A-B: stale footprint nick Switch -> Switch__C
- symbol TS1187A26020: stale footprint nick Switch -> Switch__C
- 3d duplicate dropped: MCU__C.3dshapes/LQFP-64_L7.0-W7.0-P0.40-LS9.0-BL.step (kept 3dmodels/UWRL_MCU.3dshapes/LQFP-64_L7.0-W7.0-P0.40-LS9.0-BL.step)
- 3d duplicate dropped: RES__C.3dshapes/R0402.step (kept 3dmodels/UWRL_Resistor.3dshapes/R0402.step)
- footprint DFN-8_L3.0-W3.0-P0.65-BL-EP2.45.kicad_mod: dropped Interface_CAN__C:DFN-8_L3.0-W3.0-P0.65-BL-EP2.45 (0 refs), kept Interface_CAN_LIN__C:DFN-8_L3.0-W3.0-P0.65-BL-EP2.45 (1 refs)
- footprint R0402.kicad_mod: dropped RES__C:R0402 (1 refs), kept Basic_Capacitors_Resistors__C:R0402 (8 refs)

Every symbol and footprint was re-saved by `kicad-cli … upgrade` (KiCad 10.0.6); geometry and pins are unchanged.
