@echo off
call venv\Scripts\activate.bat
echo Building executable with PyInstaller...
pyinstaller gui.py --onedir --windowed --name=iProperty_Scraper --hidden-import=selenium --hidden-import=pymysql --hidden-import=tkinter --noupx
echo Build complete! Check dist folder for executable.
pause