# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['performance_monitor_service.py'],
    pathex=[],
    binaries=[],
    hiddenimports=[
        'win32service',
        'win32serviceutil', 
        'win32event',
        'servicemanager',
        'flask',
        'flask_cors',
        'psutil',
        'GPUtil',
        'threading',
        'json',
        'time',
        'logging',
        'pathlib',
        'ctypes',
        'traceback',
        'win32api',
        'win32con',
        'win32process',
        'win32file',
        'winreg'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PerformanceMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # show console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,  # UAC request
    icon=None,
    version='version_info.txt',
)