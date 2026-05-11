@echo off
cd /d "E:\utility"
echo =============================================
echo   Build: update_pptx.exe
echo =============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://www.python.org
    pause
    exit /b 1
)

echo [1/3] Installing packages...
python -m pip install python-pptx pyinstaller -q
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

echo [2/3] Building exe...
pyinstaller --onefile --windowed --name update_pptx update_pptx.py
if errorlevel 1 (
    echo [ERROR] PyInstaller failed
    pause
    exit /b 1
)

echo.
echo =============================================
echo   Done! dist\update_pptx.exe
echo =============================================
pause
