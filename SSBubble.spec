# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect all submodules automatically
hidden_imports = collect_submodules('src')
hidden_imports.extend([
    # UI packages
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    
    # Data processing & visualization
    'numpy',
    'pyqtgraph',
    'matplotlib',
    'matplotlib.backends.backend_qtagg',  # Main Qt backend with AGG rendering
    'matplotlib.backends.backend_qt',     # Base Qt backend
    'matplotlib.backends.qt_compat',      # Qt compatibility layer
    'matplotlib.backends.backend_agg',    # AGG rendering backend
    'matplotlib.figure',
    'matplotlib.cm',
    'matplotlib.colors',
    'matplotlib.dates',
    'matplotlib.pyplot',
    
    # Hardware communication
    'serial',
    'minimalmodbus',
    
    # Data formats & parsing
    'yaml',
    'PyYAML',
    '_yaml',
    'yaml.loader',
    'yaml.dumper',
    'yaml.reader',
    'yaml.scanner',
    'yaml.parser',
    'yaml.composer',
    'yaml.constructor',
    'yaml.resolver',
    'yaml.emitter',
    'yaml.serializer',
    'yaml.representer',
    
    # Other common dependencies
    'pkg_resources.py2_warn',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements',
    'appdirs',
    'importlib_metadata',
    'cycler',
    'kiwisolver',
    'PIL',
    'PIL._imagingft',
    'PIL._imagingtk',
    'PIL._imaging',
    'PIL._webp'
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

# Add matplotlib data files
datas += collect_data_files('matplotlib')

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
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/rthook_matplotlib.py'],
    excludes=['tests', '__pycache__', 'PyQt6.uic.port_v2', 'PyQt6.uic.port_v3', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip'],
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