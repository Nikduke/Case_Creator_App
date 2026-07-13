# Setup

Use Anaconda with a project-specific environment.

## Environment

Recommended environment name:

```text
case-creator-app
```

Python version:

```text
3.12
```

Known packages:

- `PySide6`
- `openpyxl`
- `pytest`
- `pyinstaller`

Install source:

- Python from conda-forge through `environment.yml`.
- App/dev/build packages through pip editable install in `environment.yml`.

## Create Environment

```powershell
conda env create -f environment.yml
```

## Activate Environment

```powershell
conda activate case-creator-app
```

## Update Environment After Dependency Changes

```powershell
conda env update -f environment.yml --prune
```

## Run App

```powershell
conda activate case-creator-app
python -m case_builder_app
```

Alternative after editable install:

```powershell
conda activate case-creator-app
case-creator-app
```

Launcher without manual activation:

```powershell
run_app_conda.bat
```

## Test Environment

```powershell
conda activate case-creator-app
python -c "import PySide6, openpyxl; import case_builder_app; print('environment ok')"
python -m pytest -q
```

If pytest cannot access the default user temp folder, use a workspace-local temp folder:

```powershell
python -m pytest -q --basetemp .pytest-tmp
```

Expected current test result:

```text
69 passed, 1 skipped
```

The skipped test is optional and depends on a fixture not included in this clean snapshot.

The skipped test is `tests/test_services.py::test_export_service_real_energisation_project_keeps_excel_styles`. It expects `F4_Energisation_FS.casebuilder.json` in the project root. The fixture is a large/local reference project and is not required to run the app.

## Build Executable

Windows build:

```powershell
build_exe.bat
```

Build output:

```text
dist/Case_Creator_App.exe
```

If the executable is running, close it before rebuilding.

## Machine-Specific Items

The batch scripts locate `conda.exe` in common Anaconda/Miniconda locations and run the dedicated environment with:

```text
conda run -n case-creator-app ...
```

Manual activation is not required for `run_app_conda.bat` or `build_exe.bat`.

If Anaconda or Miniconda is installed outside the common locations, update the `:find_conda` section in `run_app_conda.bat` and `build_exe.bat`.

No secrets, API keys, local databases, or `.env` files are required by the current app snapshot.
