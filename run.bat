@echo off
title Stormer
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo ERREUR: Python n'est pas installe ou pas dans le PATH.
        echo Installez Python 3.10+ depuis https://python.org
        pause
        exit /b 1
    )
    echo Installation des dependances...
    venv\Scripts\pip install -r requirements.txt
)

echo Lancement de Stormer...
venv\Scripts\python.exe main.py
