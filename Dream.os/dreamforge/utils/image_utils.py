import os
import sys

# Add project root to sys.path
script_dir = os.path.dirname(__file__) # social/utils
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Example imports
try:
    # from PIL import Image
    pass
except ImportError as e:
    print(f"[ImageUtils] Warning: Failed to import dependencies: {e}")


def some_image_function():
    # ... (rest of function)
    pass 