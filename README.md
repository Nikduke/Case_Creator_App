# Case_Creator_App

Current clean working snapshot for the PSCAD case-creation desktop app.

This folder is intended to be opened directly as the active project root in Codex, VS Code, or another editor. The project is tracked in Git.

GitHub repository:

```text
git@github.com:Nikduke/Case_Creator_App.git
```

## What It Does

Case_Creator_App builds PSCAD study-case Excel workbooks from a project definition. It lets the user define case parts, values, exclusions, equipment state changes, fault levels, constants, layer states, residual flux, MM block limits, and `Input_Data` export settings.

The app exports `.xlsx` workbooks with:

- `Input_Data` from the bundled template as the first visible sheet.
- `Comp_Stat`, `Layer_Stat`, `Res_Flux`, and `MM_blocks`.
- Styled export by default.
- Simple export option for plain generated data sheets while keeping required base sheets.
- Selected-cases export through `File -> Export Selected Cases...`.

The desktop UI follows the active Windows/Qt color palette. Main editor tables and the Exclusions, `Input_Data`, and `MM_blocks` dialogs keep table surfaces and headers readable in light and dark themes. This affects the UI only; Excel export colors come from the export template and export services.

## Project Layout

- `src/case_builder_app/` - application code.
- `src/case_builder_app/assets/` - bundled Excel template and app icons.
- `src/case_builder_app/ui/theme.py` - palette-aware UI colors and shared table styles.
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

If the default Windows pytest temp folder is inaccessible, use a workspace-local temp directory:

```powershell
python -m pytest -q --basetemp .pytest-tmp
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

1. `README.md`
2. `SETUP.md`
3. `PROJECT_CONTEXT.md`
4. `docs/APP_FUNCTIONAL_SPEC.md`
5. `docs/PROJECT_JSON_GUIDE.md`

## Notes

- Use a dedicated conda environment, not `base`.
- Internal Python package name remains `case_builder_app` to avoid a broad rename.
- Documentation uses relative paths only.
- `run_app_conda.bat` and `build_exe.bat` locate Anaconda/Miniconda and use the `case-creator-app` environment without manual activation.
