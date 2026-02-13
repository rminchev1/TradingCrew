@echo off
REM TradingCrew Desktop Build Script for Windows

setlocal enabledelayedexpansion

echo ======================================
echo TradingCrew Desktop Builder (Windows)
echo ======================================
echo.

REM Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is not installed
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check npm
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: npm is not installed
    pause
    exit /b 1
)

for /f "delims=" %%i in ('node --version') do set NODE_VERSION=%%i
for /f "delims=" %%i in ('npm --version') do set NPM_VERSION=%%i

echo [OK] Node.js %NODE_VERSION%
echo [OK] npm %NPM_VERSION%
echo.

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

for /f "delims=" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION%
echo.

REM Navigate to electron directory
cd /d "%~dp0"

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install
    echo.
)

REM Check for icons
if not exist "assets\icon.ico" (
    echo Warning: Icon files not found in assets\
    echo The app will build but won't have custom icons.
    echo See assets\ICONS_README.md for instructions.
    echo.
)

REM Build menu
echo Build options:
echo 1) Quick test (--dir, unpacked)
echo 2) Full distributable (installer + portable)
echo.
set /p BUILD_OPTION="Choose option (1 or 2): "

if "%BUILD_OPTION%"=="1" (
    echo.
    echo Building unpacked app for testing...
    call npm run pack
) else if "%BUILD_OPTION%"=="2" (
    echo.
    echo Building full distributable...
    call npm run build:win
) else (
    echo Invalid option
    pause
    exit /b 1
)

REM Check build output
if exist "..\dist" (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo.
    echo Output directory: ..\dist
    echo.
    dir ..\dist /B
    echo.

    if "%BUILD_OPTION%"=="1" (
        echo To test the app:
        echo   ..\dist\win-unpacked\TradingCrew.exe
    ) else (
        echo To install:
        echo   Run the installer: TradingCrew Setup X.X.X.exe
        echo   Or use portable: TradingCrew X.X.X.exe
    )
) else (
    echo Build failed - dist directory not found
    pause
    exit /b 1
)

echo.
pause
