"""
PyInstaller hook for matplotlib data files

This hook helps PyInstaller find and include all matplotlib data files
like fonts, default stylesheets, etc.
"""

import os
import matplotlib
from PyInstaller.utils.hooks import copy_metadata

# Collect matplotlib metadata
datas = copy_metadata('matplotlib')

# Add matplotlib's mpl-data directory
mpl_data_dir = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data')
dest_dir = os.path.join('matplotlib-data')

# Create a list of tuples for all files in the mpl-data directory
datas.append((mpl_data_dir, dest_dir))
