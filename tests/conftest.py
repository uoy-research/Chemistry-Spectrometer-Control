import sys
import os
print("Loading conftest.py")
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"Project root: {project_root}")
sys.path.insert(0, project_root)
