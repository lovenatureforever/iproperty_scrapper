import cx_Freeze
import sys
import os

# Dependencies
build_exe_options = {
    "packages": ["tkinter", "selenium", "pymysql", "json", "re", "time", "threading"],
    "excludes": ["unittest"],
    "include_files": [],
    "zip_include_packages": "*",
    "zip_exclude_packages": []
}

# GUI applications require a different base on Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"

cx_Freeze.setup(
    name="iProperty Scraper",
    version="1.0",
    description="iProperty.com.my Property Scraper",
    options={"build_exe": build_exe_options},
    executables=[cx_Freeze.Executable("gui.py", base=base, target_name="iProperty_Scraper.exe")]
)