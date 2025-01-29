# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect all submodules automatically
hidden_imports = collect_submodules('src')
hidden_imports.extend([
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'numpy',
    'pyqtgraph',
    'serial',
    'minimalmodbus'
])

# Define external data files
external_files = [
    ('C:/ssbubble/valve_macro_data.json', '.'),
    ('C:/ssbubble/motor_macro_data.json', '.'),
]

# Add any existing files
datas = [
    ('config/*', 'config/'),
    ('src/controllers/*.py', 'src/controllers/'),
    ('src/models/*.py', 'src/models/'),
    ('src/ui/*.py', 'src/ui/'),
    ('src/ui/dialogs/*.py', 'src/ui/dialogs/'),
    ('src/ui/widgets/*.py', 'src/ui/widgets/'),
    ('src/utils/*.py', 'src/utils/'),
    ('src/workers/*.py', 'src/workers/'),
    ('src/__init__.py', 'src/'),
    ('chem.ico', '.'),
]

# Add external files if they exist
for src, dst in external_files:
    if os.path.exists(src):
        datas.append((src, dst))

a = Analysis(
    ['src/main.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', '__pycache__', 'PyQt6.uic.port_v2', 'PyQt6.uic.port_v3'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SSBubble',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep True for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='chem.ico'
) 