@echo off
chcp 65001 >nul
title Build Stock Analyzer Desktop App
cd /d "%~dp0"

echo ============================================
echo   Stock Analyzer - Desktop Build Script
echo   Run this to package the desktop app
echo ============================================
echo.

REM Step 1: Build frontend
echo [1/3] Building frontend...
cd frontend
call pnpm install
if %errorlevel% neq 0 (
    echo [FAILED] pnpm install failed. Make sure Node.js is installed.
    pause
    exit /b 1
)

call pnpm run build
if %errorlevel% neq 0 (
    echo [FAILED] Frontend build failed.
    pause
    exit /b 1
)
echo [OK] Frontend build complete.
cd ..
echo.

REM Step 2: Install Python dependencies
echo [2/3] Installing Python dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [FAILED] pip install failed.
    pause
    exit /b 1
)

pip install pyinstaller pywebview pystray pillow
if %errorlevel% neq 0 (
    echo [FAILED] Package install failed.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed.
echo.

REM Step 3: Package with PyInstaller
echo [3/3] Packaging desktop app...
cd ..
pyinstaller --onefile --windowed --name "金融分析平台" --add-data "backend/app/static;app/static" --hidden-import uvicorn.logging --hidden-import uvicorn.loops --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols --hidden-import uvicorn.protocols.http --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets --hidden-import uvicorn.protocols.websockets.auto --hidden-import clr --clean run.py
if %errorlevel% neq 0 (
    echo [FAILED] PyInstaller packaging failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  [SUCCESS] Package complete!
echo ============================================
echo  Output: dist\金融分析平台.exe
echo.
echo  Double-click to run. No terminal needed.
echo.
pause