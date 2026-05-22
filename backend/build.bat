@echo off
chcp 65001 >nul
title Build Stock Analyzer Desktop
echo ============================================
echo  Stock Analyzer - Desktop Build Script
echo ============================================
echo.

REM Step 1: Build frontend
echo [1/3] Building frontend...
cd /d "%~dp0..\frontend"
call npm install
if %errorlevel% neq 0 (
    echo [FAILED] npm install failed.
    pause
    exit /b 1
)

call npm run build-only
if %errorlevel% neq 0 (
    echo [FAILED] Frontend build failed.
    pause
    exit /b 1
)
echo [OK] Frontend build complete.
echo.

REM Step 2: Install Python dependencies
echo [2/3] Installing Python dependencies...
cd /d "%~dp0"
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [FAILED] pip install failed.
    pause
    exit /b 1
)

pip install pyinstaller
if %errorlevel% neq 0 (
    echo [FAILED] PyInstaller installation failed.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed.
echo.

REM Step 3: Package with PyInstaller
echo [3/3] Packaging desktop app...
pyinstaller build.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [FAILED] PyInstaller packaging failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  [SUCCESS] Package complete!
echo ============================================
echo  Output: %~dp0dist\StockAnalyzer\StockAnalyzer.exe
echo.
echo  Run StockAnalyzer.exe directly - no install needed.
echo.
echo  Config files (next to exe):
echo     .env   - API Key and settings
echo     data/  - Database, cache, backups (auto created)
echo.
pause
