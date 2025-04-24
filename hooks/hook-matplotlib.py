"""
PyInstaller hook for matplotlib

This hook helps PyInstaller find and include all the necessary
matplotlib modules and dependencies.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules
hiddenimports = collect_submodules('matplotlib')

# Also explicitly include these backends which might be missed
hiddenimports.extend([
    'matplotlib.backends.backend_qt',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_agg',
    'matplotlib.backends.qt_compat'
])

# Get all matplotlib data files (fonts, etc.)
datas = collect_data_files('matplotlib')
