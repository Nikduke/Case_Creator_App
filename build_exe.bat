@echo off
setlocal

cd /d "%~dp0"

set "ENV_NAME=case-creator-app"
set "EXE_NAME=Case_Creator_App.exe"
set "SPEC_NAME=Case_Creator_App.spec"
call :find_conda
if errorlevel 1 exit /b %errorlevel%

echo Checking conda environment:
echo   %ENV_NAME%
echo.
"%CONDA_EXE%" run -n "%ENV_NAME%" python --version >nul 2>nul
if errorlevel 1 (
  echo Could not run the conda environment "%ENV_NAME%".
  echo Create or update it with environment.yml, then run this script again.
  exit /b 1
)

echo Using Python:
echo   conda run -n %ENV_NAME% python
echo.

"%CONDA_EXE%" run -n "%ENV_NAME%" python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') and importlib.util.find_spec('openpyxl') else 1)" >nul 2>nul
if errorlevel 1 (
  echo Installing packaging dependencies...
  "%CONDA_EXE%" run -n "%ENV_NAME%" python -m pip install -e ".[packaging]"
  if errorlevel 1 exit /b %errorlevel%
  echo.
)

tasklist /FI "IMAGENAME eq %EXE_NAME%" 2>nul | find /I "%EXE_NAME%" >nul
if not errorlevel 1 (
  echo %EXE_NAME% is currently running.
  echo Close the app before building a new executable, then run this script again.
  exit /b 1
)

echo Building executable...
"%CONDA_EXE%" run -n "%ENV_NAME%" python -m PyInstaller --noconfirm .\%SPEC_NAME%
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build complete.
echo Executable:
echo   %CD%\dist\%EXE_NAME%

endlocal
exit /b 0

:find_conda
if defined CONDA_EXE if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=%USERPROFILE%\Anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=%USERPROFILE%\Miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=%LOCALAPPDATA%\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=%LOCALAPPDATA%\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=C:\ProgramData\anaconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0
set "CONDA_EXE=C:\ProgramData\miniconda3\Scripts\conda.exe"
if exist "%CONDA_EXE%" exit /b 0

echo Could not find Anaconda or Miniconda conda.exe.
echo Expected one of the common Anaconda/Miniconda install folders.
exit /b 1
