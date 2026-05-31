@echo off
cd /d "%~dp0"
echo === Build Stormer v1.0 ===
if not exist venv\Scripts\python.exe (
    echo Creer d'abord le venv: python -m venv venv
    exit /b 1
)
call venv\Scripts\activate.bat
pip install -q pyinstaller
pyinstaller --noconfirm --clean stormer.spec
if errorlevel 1 (
    echo Echec du build.
    exit /b 1
)
echo.
echo OK — executable: dist\Stormer.exe
pause
