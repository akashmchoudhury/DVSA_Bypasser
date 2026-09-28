@echo off
setlocal

cd /d "%~dp0"

if exist "..\Instructions\instructions.md" (
  echo Checked instruction file: ..\Instructions\instructions.md
) else (
  echo Instruction file was not found at ..\Instructions\instructions.md
)

set "PYTHON_CMD=python"

where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python was not found. Install Python 3.11 or newer, then run this launcher again.
    pause
    exit /b 1
  )
  set "PYTHON_CMD=py -3"
)

cd /d "%~dp0Core Engine"
%PYTHON_CMD% -m dvsa_appointment_setter.ui_server
if errorlevel 1 (
  echo The UI server stopped with an error.
  pause
  exit /b 1
)
