# Project Context

## Status

This is the clean active working snapshot for `Case_Creator_App`.

The project uses Git on the `main` branch. Treat this folder as the project root.

The configured remote is `git@github.com:Nikduke/Case_Creator_App.git`.

## Purpose

Case_Creator_App is a PySide6 desktop app for creating PSCAD study-case Excel workbooks. It stores project definitions as `.casebuilder.json` and exports PSCAD input workbooks from those definitions.

## Current Folder

- `src/case_builder_app/` - current application code.
- `src/case_builder_app/assets/export_template.xlsx` - bundled Excel template used by export.
- `tests/` - useful pytest coverage for generation, export, UI model behavior, rules, and dialogs.
- `examples/` - small sample/reference files for development checks.
- `docs/` - current behavior and JSON notes.
- `environment.yml` - conda environment setup.
- `build_exe.bat` and `Case_Creator_App.spec` - Windows executable build path.

Internal package name is still `case_builder_app`. This is intentional. Do not rename package unless doing a planned full rename with tests.

## Setup

Use dedicated conda env:

```powershell
conda env create -f environment.yml
conda activate case-creator-app
```

Run app:

```powershell
python -m case_builder_app
```

Run tests:

```powershell
python -m pytest -q
```

## Important Current Logic

- Project files use JSON schema version `2`.
- Base Case defines starting state.
- Case part values store sparse changes.
- CB changes are applied in case-part order from top to bottom.
- Each case part value creates branch-specific inherited state for following case parts.
- Same-as-base CB lane placement can be an explicit local override in schema v2.
- Name order is separate from logic order. It changes exported case names only.
- Exclusions remove generated case combinations.
- Export Selected Cases builds one workbook for pasted matching case names.
- Saved selected-case lists are stored in project JSON.
- `Input_Data` settings are project-level.
- `Res_Flux` and `MM_blocks` sheets are always exported.
- `MM_blocks` limits are project-level values, sorted by voltage level.
- CB and MM voltage ordering uses voltage token from element names and sorts high to low; non-numeric voltage sorts last.
- `Input_Data` export writes formulas for `B40`, `B41`, `B45`, and `B46`, then patches cached numeric values into the saved `.xlsx` so pandas-based PSCAD scripts can read values without opening Excel.
- Project validation rejects duplicate or missing case-part/value IDs, invalid saved name-order references, and invalid conditional-rule references or match modes.
- Export restores raw Excel `x14:dataValidations` XML for `Input_Data` because `openpyxl` cannot preserve that extension directly.

## Main Modules

- `models.py` - dataclasses and JSON structures.
- `services/generator.py` - case generation and layered application of changes.
- `services/export_service.py` - styled/simple Excel export orchestration.
- `services/input_data.py` - values/formulas written into `Input_Data`.
- `services/sheet_builders.py` - shared rows for styled/simple export.
- `services/style_template.py` - Excel style helpers and conditional formatting.
- `services/export_ordering.py` - shared ordering for CB/MM/elements.
- `ui/main_window.py` - main window shell.
- `ui/project_document.py` - open/save/export orchestration.
- `ui/project_selection.py` - selected case part/value state and branch preview wiring.
- `ui/changes_editor.py` - editor card composition.
- `ui/cb_state_board.py` - CB lane editor and branch preview.
- `ui/input_data_dialog.py` - project-level `Input_Data` settings.

## Configuration Requirements

- Anaconda must be installed on the new laptop.
- Use env name `case-creator-app`.
- No required `.env`, credentials, API keys, or local database.
- PSCAD itself is not configured by this app; the app exports Excel files consumed by external PSCAD automation scripts.

## Known Issues / Risks

- Tests include one skipped optional fixture check: `tests/test_services.py::test_export_service_real_energisation_project_keeps_excel_styles` expects the omitted `F4_Energisation_FS.casebuilder.json` reference project.
- Batch scripts locate `conda.exe` in common Anaconda/Miniconda install folders. Update their `:find_conda` section if Anaconda is installed elsewhere.
- The app is Windows-oriented for executable packaging.
- Conditional rules remain supported in JSON and generation but have no current UI editor.
- Some example files retain legacy engineering filenames because they are reference workbooks, not app versions.
- Internal package name is not renamed to avoid broad churn.

## Pending Work

- Build executable on the new laptop only when needed.
- If future PSCAD automation script requirements change, re-check `Input_Data` formulas and cached values.
- Keep documentation updated after meaningful code changes.

## Codex First Steps On New Laptop

1. Read `README.md`, `SETUP.md`, this file, `docs/APP_FUNCTIONAL_SPEC.md`, and `docs/PROJECT_JSON_GUIDE.md`.
2. Inspect actual code before edits.
3. Verify docs against code before trusting them.
4. Run `python -m pytest -q`.
5. Report understanding before changing files.
6. Make small targeted changes only.
