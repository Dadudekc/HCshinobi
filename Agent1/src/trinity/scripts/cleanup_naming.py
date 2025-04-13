import os
import re
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def to_snake_case(name):
    # Remove file extension if present
    base_name = os.path.splitext(name)[0]
    # Convert camelCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', base_name)
    snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    # Add back the extension
    return snake_case + os.path.splitext(name)[1]

def cleanup_naming(directory):
    if not os.path.exists(directory):
        logging.warning(f"Directory {directory} does not exist")
        return

    logging.info(f"\nProcessing directory: {directory}")
    
    # Walk through directory
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            new_name = to_snake_case(file)
            new_path = os.path.join(root, new_name)
            
            # Skip if file is already in snake_case
            if file == new_name:
                continue
            
            try:
                # Rename file to snake_case
                if os.path.exists(new_path):
                    # If both files have the same content, remove the old one
                    with open(file_path, 'rb') as f1, open(new_path, 'rb') as f2:
                        if f1.read() == f2.read():
                            logging.info(f"Removing duplicate file {file_path}")
                            try:
                                os.remove(file_path)
                            except PermissionError:
                                logging.error(f"Could not remove {file_path} - file is in use")
                            except Exception as e:
                                logging.error(f"Error removing {file_path}: {str(e)}")
                else:
                    logging.info(f"Renaming {file_path} to {new_path}")
                    os.rename(file_path, new_path)
            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")

def main():
    directories = ['consolidated', 'Agent2', 'overnight_scripts', 'src']
    for directory in directories:
        cleanup_naming(directory)

if __name__ == '__main__':
    main() 