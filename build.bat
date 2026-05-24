@echo off
echo ========================================
echo   Cookie Dash - Building EXE...
echo ========================================
echo.

REM Install dependencies if needed
pip install -r requirements.txt

echo.
echo Building executable with PyInstaller...
echo.

pyinstaller --onefile --windowed --name "CookieDash" --icon=NUL main.py

echo.
echo ========================================
echo   Build complete!
echo   EXE location: dist\CookieDash.exe
echo ========================================
pause
