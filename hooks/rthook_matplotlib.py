"""
Runtime hook for matplotlib

This is executed when the application starts to ensure matplotlib
is configured correctly.
"""

import os
import sys
import matplotlib

# For frozen applications, set environment variables to help matplotlib find its data
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Set MPLCONFIGDIR to prevent matplotlib from writing to user's home directory
    os.environ['MPLCONFIGDIR'] = os.path.join(
        sys._MEIPASS, 'matplotlib-config')

    # If there's a matplotlib-data directory in the bundle, add it to the path
    mpl_data_dir = os.path.join(sys._MEIPASS, 'matplotlib-data')
    if os.path.exists(mpl_data_dir):
        os.environ['MATPLOTLIBDATA'] = mpl_data_dir

# Set the backend to QtAgg explicitly (this is the correct backend for PyQt6)
matplotlib.use('QtAgg', force=True)
