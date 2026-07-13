# Project Agent Instructions

## Scope

These instructions apply to the `Case_Creator_App` project root and its contents.

## Project Identity

- This is a PySide6 desktop app for creating PSCAD study-case Excel workbooks.
- Project definitions use `.casebuilder.json` files.
- Excel output is produced from `src/case_builder_app/assets/export_template.xlsx`.
- PSCAD itself is not launched or configured by this app.
- This project does not use Git. Do not assume Git history exists.

## Working Rules

- Work silently by default. Report only completion, blockers, required approval, or validation results.
- Inspect the relevant code and documentation before editing.
- Preserve existing behavior unless the user explicitly requests a behavior change.
- Prefer deletion and small local simplifications over new abstractions or broad rewrites.
- Do not change calculation rules, parsing, generation order, export formats, JSON schema, or UI workflows without explicit approval.
- Do not refactor or delete exclusion behavior without an explicit product decision.
- Conditional rules are preserved in JSON and used by generation, but there is currently no UI editor. Do not remove them without confirming the product requirement.
- Never overwrite unrelated user changes.
- Use `apply_patch` for manual file edits.
- Use relative paths in project documentation.

## Required Reading Before Code Changes

Read these files in order:

1. `README.md`
2. `SETUP.md`
3. `PROJECT_CONTEXT.md`
4. `docs/APP_FUNCTIONAL_SPEC.md`
5. `docs/PROJECT_JSON_GUIDE.md`
6. Relevant source files and tests for the requested change

Verify that the documentation matches the actual code before relying on it.

## Environment

- Use Anaconda or Miniconda with the dedicated environment `case-creator-app`.
- Do not install project dependencies into `base`.
- The project targets Python `3.12`.
- Prefer `environment.yml` for environment creation and updates.
- Expected project packages are `PySide6`, `openpyxl`, `pytest`, and `pyinstaller`.
- Do not auto-accept conda Terms of Service.
- If conda plugins or cache permissions block setup, use `CONDA_NO_PLUGINS=true` and report the workaround.
- If an `environment.yml` solve stalls for more than 10 minutes without progress, stop it rather than waiting indefinitely. Use the documented pip fallback only when necessary and report that fallback.

Create the environment with:

```powershell
conda env create -f environment.yml
```

Run the app with:

```powershell
conda activate case-creator-app
python -m case_builder_app
```

The Windows launchers `run_app_conda.bat` and `build_exe.bat` must run through the dedicated environment without requiring manual activation.

## Validation

For source changes:

1. Run focused tests for the touched behavior.
2. Run the full suite when practical:

   ```powershell
   python -m pytest -q
   ```

3. Run an import check for touched modules.
4. Run a compile check:

   ```powershell
   python -m compileall -q src tests
   ```

5. Validate generated workbook or JSON output when the change affects serialization or export.
6. Remove generated `__pycache__`, `.pytest_cache`, and workspace-local `.pytest-tmp*` directories after validation.

One optional export test may be skipped when the local reference fixture `F4_Energisation_FS.casebuilder.json` is absent. This fixture is not required to run the application.

Do not claim a check passed unless it was actually run. If validation cannot run, state exactly why.

## Codebase Boundaries

- `src/case_builder_app/models.py` defines the project JSON model and persistence shape.
- `src/case_builder_app/services/generator.py` defines case combination and change-application behavior.
- `src/case_builder_app/services/validation.py` defines Check validation before generation/export.
- `src/case_builder_app/services/export_service.py` owns styled and simple workbook export.
- `src/case_builder_app/services/style_template.py` depends on the layout of the bundled Excel template.
- `src/case_builder_app/ui/project_document.py` owns open, save, Check, and export orchestration.
- `tests/` contains generation, export, persistence, and UI behavior checks.

Changes to `models.py`, `generator.py`, `validation.py`, `export_service.py`, or the Excel template have a wider regression risk and require focused tests plus the full suite when practical.

## Documentation Updates

Update the relevant documentation when changing:

- setup or environment behavior;
- run, test, or build commands;
- dependencies;
- JSON schema or persistence behavior;
- generation, validation, or export behavior;
- known limitations or required fixtures.

Keep documentation concise and describe the current behavior, not obsolete implementation history.
