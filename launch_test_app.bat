@echo off
setlocal

cd /d "%~dp0"

set "APP_ROOT=%CD%"
set "VENV_DIR=%APP_ROOT%\.venv"
set "REQUIREMENTS_FILE=requirements.txt"
set "PYTHON_UTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ============================================
echo EasySTT Test Launcher
echo Root: %APP_ROOT%
echo ============================================

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    py -3.14 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

echo [2/4] Ensuring pip is available...
"%VENV_DIR%\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip is unavailable inside the virtual environment.
    pause
    exit /b 1
)

echo [3/4] Installing requirements from %REQUIREMENTS_FILE%...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo [4/4] Launching app...
"%VENV_DIR%\Scripts\python.exe" main.py
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo App exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
