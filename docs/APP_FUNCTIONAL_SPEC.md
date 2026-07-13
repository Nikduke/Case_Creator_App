# App Functional Spec

## Scope

Case_Creator_App is a desktop app for building PSCAD study-case Excel input workbooks.

It does not run PSCAD directly. It creates project JSON files and exported `.xlsx` files used by external PSCAD automation.

## Main Concepts

- Project - full app state saved as `.casebuilder.json`.
- Base Case - starting conditions.
- Case Part - a dimension of case generation.
- Case Value - one token/value inside a case part.
- Changes - sparse edits applied by a case value.
- Generated Case - one combination of case values after exclusions.

## Case Logic

Generation starts from Base Case and applies case part values from top to bottom.

Each value stores only changes. A later case part inherits the already-resolved state from previous selected values. This means a case part can create branch-specific base states for following case parts.

Example:

```text
Case part 1: A1, A2, A3
Case part 2: C22, C23, C25
```

Each `C*` value is resolved separately under `A1`, `A2`, and `A3` branches.

Case-name order is separate from logic order. Use Name order to change exported column names without changing application order.

## Validation

Run Check before exporting. Validation covers required labels and tokens, duplicate case-part/value names, incomplete changes, contradictory CB assignments, MM voltage limits, and persisted references. It also rejects duplicate or missing case-part/value IDs, invalid saved name-order entries, and conditional rules with invalid match modes or unknown references.

## Project Options

Project options are project-level, not case-value-specific:

- Project name.
- Exclusions.
- Input_Data settings.
- MM_blocks limits.
- Simple export.
- Include first token in case names.
- Name order.
- Preview.
- Project path/status.

`Res_Flux` and `MM_blocks` output sheets are always present.

## Editors

### CB State

CB state uses three lanes:

- `OFF`
- `SWITCH`
- `ON`

CB names are grouped visually by voltage token and sorted high to low. Non-numeric voltage sorts last.

The CB editor supports:

- paste/list add for Base Case only;
- include/exclude search;
- drag/drop lane changes;
- delete selected;
- undo/redo;
- branch preview buttons for prior CB-changing case parts.

The branch preview is UI-only and helps inspect inherited states for later CB-changing case parts.

### Fault Level

Fault level stores standard fault fields and exports per generated case.

### Constants

Constants store parameter values by definition/parameter and export into `Comp_Stat`.

### Layer

Layer state stores `Enable`/`Disable` values and exports into `Layer_Stat`.

### Residual Flux

Residual flux values are edited in the Residual Flux card.

`Input_Data` has a separate `Residual Flux` setting in switching settings. It exports `Yes` only when switching study is selected and the setting is `Yes`.

### MM Blocks

MM element names are project-level. Limits are entered per voltage level:

- `Un`
- `Um`
- `SDPF_LG`
- `SDPF_LL`
- `SIWL_LG`
- `SIWL_LL`
- `LIWL`

MM output is sorted by voltage level high to low, then natural name.

### Input_Data

`Input_Data` is a project-level dialog. It uses tables with copy/paste support and dropdown cells.

Supported study selection:

- Frequency sweep.
- Switching.
- Fault.
- Switching and Fault together.

The dialog shows relevant settings only for selected study logic.

Sequential timing fields use:

- Frequency.
- N points over wave.
- 1st N points to check.

Export writes formulas into:

- `B40` Fault increment.
- `B41` Fault end.
- `B45` Switch increment.
- `B46` Switch stop.

Export also writes cached numeric values into the `.xlsx` XML so pandas/openpyxl readers can read values without Excel recalculation.

## Export

Styled export uses the bundled template:

```text
src/case_builder_app/assets/export_template.xlsx
```

The template's reference rows and columns are part of the export contract. Changes to that layout must be coordinated with `src/case_builder_app/services/style_template.py` and the export tests.

Visible sheets:

- `Input_Data`
- `Comp_Stat`
- `Layer_Stat`
- `Res_Flux`
- `MM_blocks`

Styled export preserves:

- key template styles;
- borders;
- conditional formatting;
- state background colors;
- voltage-group fills;
- worksheet zoom settings.

Simple export keeps required sheets but writes generated sheets as plain rows.

Export restores raw `Input_Data` validation XML after saving because `openpyxl` does not preserve the template extension directly.

## Selected Cases Export

`File -> Export Selected Cases...` opens a dialog for pasted case names.

It:

- matches pasted names against checked generated cases;
- reports matched/missing/duplicates;
- allows Simple export;
- can save/reuse named selection lists in project JSON;
- exports one workbook for all matched selected cases.

## Executable

Windows executable build uses:

```text
build_exe.bat
Case_Creator_App.spec
```

Output:

```text
dist/Case_Creator_App.exe
```
