# Case_Creator_App

Current clean working snapshot for the PSCAD case-creation desktop app.

This folder is intended to be opened directly as the active project root in Codex, VS Code, or another editor. The project does not use Git.

## What It Does

Case_Creator_App builds PSCAD study-case Excel workbooks from a project definition. It lets the user define case parts, values, exclusions, equipment state changes, fault levels, constants, layer states, residual flux, MM block limits, and `Input_Data` export settings.

The app exports `.xlsx` workbooks with:

- `Input_Data` from the bundled template as the first visible sheet.
- `Comp_Stat`, `Layer_Stat`, `Res_Flux`, and `MM_blocks`.
- Styled export by default.
- Simple export option for plain generated data sheets while keeping required base sheets.
- Selected-cases export through `File -> Export Selected Cases...`.

## Project Layout

- `src/case_builder_app/` - application code.
- `src/case_builder_app/assets/` - bundled Excel template and app icons.
- `tests/` - pytest suite.
- `examples/` - small reference/sample files only.
- `docs/` - current app behavior and JSON reference.
- `environment.yml` - Anaconda environment definition.
- `build_exe.bat` and `Case_Creator_App.spec` - Windows executable build files.
- `PROJECT_CONTEXT.md` - handover for future Codex sessions.
- `SETUP.md` - environment, run, test, and build commands.

## Quick Setup

```powershell
conda env create -f environment.yml
conda activate case-creator-app
python -m case_builder_app
```

Run tests:

```powershell
conda activate case-creator-app
python -m pytest -q
```

Build executable:

```powershell
build_exe.bat
```

Output executable:

```text
dist/Case_Creator_App.exe
```

## Read First

Before changing files, read:

1. `PROJECT_CONTEXT.md`
2. `SETUP.md`
3. `docs/APP_FUNCTIONAL_SPEC.md`
4. `docs/PROJECT_JSON_GUIDE.md`

## Notes

- Use a dedicated conda environment, not `base`.
- Internal Python package name remains `case_builder_app` to avoid a broad rename.
- Documentation uses relative paths only.
- `run_app_conda.bat` and `build_exe.bat` locate Anaconda/Miniconda and use the `case-creator-app` environment without manual activation.
