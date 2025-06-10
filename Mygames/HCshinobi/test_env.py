import sys
import os

print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("sys.prefix:", sys.prefix)
print("sys.base_prefix:", sys.base_prefix)
print("PYTHONPATH:", os.environ.get("PYTHONPATH", "Not set"))
print("PYTHONHOME:", os.environ.get("PYTHONHOME", "Not set"))
print("sys.path:", sys.path) 