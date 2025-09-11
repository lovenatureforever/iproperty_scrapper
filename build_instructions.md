# Build Instructions

## Prerequisites
1. Install Python 3.8 or higher

## Quick Setup (Recommended)
Double-click `setup_venv.bat` to create virtual environment and install dependencies.
Then double-click `build_venv.bat` to build executable.

## Manual Setup
2. Install required packages:
   ```
   pip install -r requirements.txt
   pip install cx_Freeze
   ```

## Build Executable

### Option 1: cx_Freeze (if DLL issues persist, use Option 2)
```
python build_exe.py build
```
Executable will be in `build/` directory.

### Option 2: PyInstaller (Recommended for DLL issues)
```
pip install pyinstaller
python build_pyinstaller.py
```
Executable will be in `dist/iProperty_Scraper/` directory.

**Note:** Use `--onedir` instead of `--onefile` to avoid DLL ordinal errors.

## Run GUI
To run the GUI directly:
```
python gui.py
```

## Run Command Line
To run the original command line version:
```
python iproperty.py
```