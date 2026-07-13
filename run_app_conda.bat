@echo off
setlocal

cd /d "%~dp0"

set "ENV_NAME=case-creator-app"
call :find_conda
if errorlevel 1 exit /b %errorlevel%

"%CONDA_EXE%" run -n "%ENV_NAME%" python -m case_builder_app
if errorlevel 1 exit /b %errorlevel%

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
