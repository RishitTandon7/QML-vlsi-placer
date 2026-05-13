@echo off
REM QML·PLACE Local Installation Script for Windows (without Docker)
REM This script sets up the Python environment and installs dependencies

setlocal enabledelayedexpansion

echo.
echo ════════════════════════════════════════════════════════════════════════
echo  QML·PLACE Local Setup (Windows)
echo ════════════════════════════════════════════════════════════════════════
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+ from python.org
    exit /b 1
)

echo [OK] Python detected
python --version

REM Create virtual environment
echo.
echo [SETUP] Creating Python virtual environment...
if exist venv (
    echo [WARN] Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo.
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)
echo [OK] Virtual environment activated

REM Upgrade pip
echo.
echo [SETUP] Upgrading pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARN] pip upgrade had issues, continuing anyway...
)

REM Install PyTorch (CPU) from the official PyTorch wheel index
echo.
echo [SETUP] Installing PyTorch (CPU build) from pytorch.org...
pip install torch==2.2.2+cpu torchvision==0.17.2+cpu --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (
    echo [WARN] Exact torch version not found, trying latest CPU build...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    if errorlevel 1 (
        echo [ERROR] Failed to install PyTorch
        exit /b 1
    )
)
echo [OK] PyTorch installed

REM Install remaining dependencies from PyPI
echo.
echo [SETUP] Installing remaining Python dependencies...
echo [INFO] Installing: PyQt6, PennyLane, NumPy, etc.
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)
echo [OK] All dependencies installed

REM Create necessary directories
echo.
echo [SETUP] Creating directories...
if not exist "results" mkdir results
if not exist "checkpoints" mkdir checkpoints
if not exist "designs\CA234" mkdir designs\CA234

echo [OK] Directories created

REM Summary
echo.
echo ════════════════════════════════════════════════════════════════════════
echo  SETUP COMPLETE ✓
echo ════════════════════════════════════════════════════════════════════════
echo.
echo Next steps:
echo.
echo  1. Prepare design files (if not already present):
echo     - Place CA234.v, CA234.sdc, CA234.def in designs\CA234\
echo     - Or use demo mode in GUI
echo.
echo  2. Run the GUI application:
echo     python main.py
echo.
echo  3. Or run tests:
echo     pytest -v
echo.
echo ════════════════════════════════════════════════════════════════════════
echo.

endlocal
