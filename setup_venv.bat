@echo off
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Installing requirements...
pip install -r requirements.txt
pip install pyinstaller
echo Setup complete! Run build_venv.bat to build executable.
pause