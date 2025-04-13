import os
import shutil
from pathlib import Path

def copy_files(source_dir, dest_dir):
    """Copy files from source directory to destination directory, maintaining structure."""
    if not os.path.exists(source_dir):
        print(f"Source directory not found: {source_dir}")
        return
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)
            relative_path = os.path.relpath(source_path, source_dir)
            dest_path = os.path.join(dest_dir, relative_path)
            
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            print(f"Copied {file} to {dest_path}")

def main():
    base_path = Path(".")
    chat_mate_path = base_path / "overnight_scripts" / "chat_mate"
    
    # Ensure chat_mate directory exists
    chat_mate_path.mkdir(parents=True, exist_ok=True)
    
    # Process Agent1 files
    agent1_path = base_path / "Agent2" / "Agent3" / "Agent1" / "overnight_scripts" / "chat_mate"
    if agent1_path.exists():
        print("\nProcessing Agent1 files...")
        copy_files(str(agent1_path), str(chat_mate_path))
    
    # Process Agent4 files
    agent4_path = base_path / "Agent2" / "Agent3" / "Agent4" / "overnight_scripts" / "chat_mate"
    if agent4_path.exists():
        print("\nProcessing Agent4 files...")
        copy_files(str(agent4_path), str(chat_mate_path))
    
    # Process Agent2 files
    agent2_path = base_path / "Agent2" / "overnight_scripts" / "chat_mate"
    if agent2_path.exists():
        print("\nProcessing Agent2 files...")
        copy_files(str(agent2_path), str(chat_mate_path))
    
    # Process Agent3 files
    agent3_path = base_path / "Agent2" / "Agent3" / "overnight_scripts" / "chat_mate"
    if agent3_path.exists():
        print("\nProcessing Agent3 files...")
        copy_files(str(agent3_path), str(chat_mate_path))

if __name__ == "__main__":
    main()
    print("\nFile consolidation complete!") 