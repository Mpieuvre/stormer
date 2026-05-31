@echo off
cd /d "%~dp0"
echo === Build Stormer v1.0 + Installateur ===
if not exist venv\Scripts\python.exe (
    echo Creer d'abord le venv: python -m venv venv
    exit /b 1
)
call venv\Scripts\activate.bat
pip install -q pyinstaller

echo [0/2] Assets (logo)...
venv\Scripts\python.exe scripts\generate_assets.py

echo [1/2] Stormer.exe...
pyinstaller --noconfirm --clean stormer.spec
if errorlevel 1 exit /b 1

echo [2/2] Stormer_Setup.exe...
pyinstaller --noconfirm --clean installer.spec
if errorlevel 1 exit /b 1

echo.
echo OK :
echo   dist\Stormer.exe       — application seule
echo   dist\Stormer_Setup.exe — installateur ^(raccourci bureau^)
pause
