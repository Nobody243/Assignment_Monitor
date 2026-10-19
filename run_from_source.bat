@echo off
:: Developer convenience: run the app from source. End users should use the packaged exe from Releases.
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.10+ is required. & pause & exit /b 1)
python -c "import playwright, customtkinter, winotify, lxml" >nul 2>nul || python -m pip install -r requirements.txt
start "" pythonw app.py
