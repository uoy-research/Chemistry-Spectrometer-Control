"""
Helper script to collect all matplotlib dependencies for PyInstaller.
Run this before building to generate a comprehensive list of hidden imports.
"""

import os
import importlib
import pkgutil


def find_modules(package_name):
    """Find all submodules in a package"""
    package = importlib.import_module(package_name)
    results = []

    if hasattr(package, '__path__'):
        for _, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
            results.append(name)
            if ispkg:
                results.extend(find_modules(name))

    return results


def main():
    """Print all matplotlib modules"""
    print("Collecting matplotlib modules...")

    # Collect matplotlib modules
    mpl_modules = find_modules('matplotlib')

    print(f"Found {len(mpl_modules)} modules in matplotlib")

    # Write to a file
    with open('matplotlib_modules.txt', 'w') as f:
        f.write("# Add these to your SSBubble.spec file's hidden_imports\n")
        f.write("[\n")
        for module in sorted(mpl_modules):
            f.write(f"    '{module}',\n")
        f.write("]\n")

    print(f"Module list written to matplotlib_modules.txt")


if __name__ == "__main__":
    main()
