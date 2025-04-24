"""
PyInstaller hook for PyYAML

This hook helps PyInstaller find and include all the necessary
YAML modules and dependencies.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules
hiddenimports = collect_submodules('yaml')

# Also explicitly include these modules which might be missed
hiddenimports.extend([
    'yaml',
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
    'yaml.cyaml',
    'yaml.tokens',
    'yaml.events',
    'yaml.nodes',
    'yaml.error'
])

# Get any data files
datas = collect_data_files('yaml')
