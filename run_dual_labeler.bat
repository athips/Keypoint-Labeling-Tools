@echo off
REM Dual Keypoint Labeler Launcher
REM This batch file launches the Dual Keypoint Labeler application

echo ========================================
echo  Dual Keypoint Labeler
echo  Starting application...
echo ========================================
echo.

REM Change to the labeling directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    echo.
    pause
    exit /b 1
)

REM Check if the script exists
if not exist "dual_keypoint_labeler.py" (
    echo ERROR: dual_keypoint_labeler.py not found
    echo Please make sure you are in the correct directory
    echo.
    pause
    exit /b 1
)

REM Install/update dependencies
echo Installing required dependencies...
python -m pip install --upgrade pip >nul 2>&1
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo WARNING: Failed to install some dependencies
        echo The application may not work correctly
        echo.
    ) else (
        echo Dependencies installed successfully.
        echo.
    )
) else (
    echo WARNING: requirements.txt not found, installing Pillow directly...
    python -m pip install Pillow>=9.0.0
)

REM Run the application
echo Launching Dual Keypoint Labeler...
echo.
python dual_keypoint_labeler.py

REM Check if there was an error
if errorlevel 1 (
    echo.
    echo ERROR: Application exited with an error
    echo.
    pause
    exit /b 1
)

echo.
echo Application closed.
pause





