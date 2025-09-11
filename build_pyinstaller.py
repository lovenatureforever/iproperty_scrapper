import PyInstaller.__main__

PyInstaller.__main__.run([
    'gui.py',
    '--onedir',
    '--windowed',
    '--name=iProperty_Scraper',
    '--noupx',
    '--hidden-import=selenium',
    '--hidden-import=pymysql',
    '--hidden-import=tkinter'
])