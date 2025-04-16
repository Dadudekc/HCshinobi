import pytest
import os
import tempfile
from pathlib import Path
from core.coordination.path_manager import PathManager, FileType, FileNode

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test directory structure
        root = Path(tmpdir)
        
        # Create directories
        (root / "dir1").mkdir()
        (root / "dir1" / "subdir").mkdir()
        (root / "dir2").mkdir()
        
        # Create files
        (root / "file1.txt").write_text("test1")
        (root / "dir1" / "file2.txt").write_text("test2")
        (root / "dir1" / "subdir" / "file3.txt").write_text("test3")
        (root / "dir2" / "file4.py").write_text("test4")
        
        yield root

@pytest.fixture
def path_manager(temp_dir):
    return PathManager(temp_dir)

def test_init(temp_dir):
    pm = PathManager(temp_dir)
    assert pm.root == temp_dir.resolve()
    assert not pm._cache
    assert not pm._watchers

def test_get_file_type(path_manager, temp_dir):
    assert path_manager._get_file_type(temp_dir) == FileType.DIRECTORY
    assert path_manager._get_file_type(temp_dir / "file1.txt") == FileType.FILE
    assert path_manager._get_file_type(temp_dir / "nonexistent") == FileType.UNKNOWN

def test_create_node(path_manager, temp_dir):
    # Test file node
    file_node = path_manager._create_node(temp_dir / "file1.txt")
    assert file_node.type == FileType.FILE
    assert file_node.name == "file1.txt"
    assert file_node.size > 0
    assert file_node.children is None
    
    # Test directory node
    dir_node = path_manager._create_node(temp_dir / "dir1", recursive=True)
    assert dir_node.type == FileType.DIRECTORY
    assert dir_node.name == "dir1"
    assert len(dir_node.children) == 2  # file2.txt and subdir
    assert "file2.txt" in dir_node.children
    assert "subdir" in dir_node.children

def test_scan(path_manager, temp_dir):
    # Test recursive scan
    root_node = path_manager.scan()
    assert root_node.type == FileType.DIRECTORY
    assert len(root_node.children) == 4  # dir1, dir2, file1.txt
    
    # Test non-recursive scan
    root_node = path_manager.scan(recursive=False)
    assert root_node.type == FileType.DIRECTORY
    assert len(root_node.children) == 4
    
    # Test scanning subdirectory
    dir1_node = path_manager.scan(temp_dir / "dir1")
    assert dir1_node.type == FileType.DIRECTORY
    assert len(dir1_node.children) == 2
    
    # Test scanning nonexistent path
    with pytest.raises(FileNotFoundError):
        path_manager.scan(temp_dir / "nonexistent")
        
    # Test scanning path outside root
    with pytest.raises(ValueError):
        path_manager.scan(temp_dir.parent)

def test_find(path_manager, temp_dir):
    # Test finding all text files
    txt_files = path_manager.find("*.txt")
    assert len(txt_files) == 3
    
    # Test finding python files
    py_files = path_manager.find("*.py")
    assert len(py_files) == 1
    
    # Test finding in subdirectory
    subdir_files = path_manager.find("*.txt", temp_dir / "dir1")
    assert len(subdir_files) == 2
    
    # Test finding nonexistent pattern
    assert not path_manager.find("*.nonexistent")
    
    # Test finding in path outside root
    with pytest.raises(ValueError):
        path_manager.find("*.txt", temp_dir.parent)

def test_walk(path_manager, temp_dir):
    nodes = list(path_manager.walk())
    
    # Count different types of nodes
    files = [n for n in nodes if n.type == FileType.FILE]
    dirs = [n for n in nodes if n.type == FileType.DIRECTORY]
    
    assert len(files) == 4  # All files
    assert len(dirs) == 3   # Root + dir1 + dir2 + subdir

def test_path_conversion(path_manager, temp_dir):
    # Test relative path
    abs_path = temp_dir / "dir1" / "file2.txt"
    rel_path = path_manager.get_relative_path(abs_path)
    assert str(rel_path) == os.path.join("dir1", "file2.txt")
    
    # Test absolute path
    rel_path = Path("dir1/file2.txt")
    abs_path = path_manager.get_absolute_path(rel_path)
    assert abs_path == (temp_dir / "dir1" / "file2.txt").resolve()
    
    # Test path outside root
    with pytest.raises(ValueError):
        path_manager.get_relative_path(temp_dir.parent)

def test_cache_operations(path_manager, temp_dir):
    # Scan to populate cache
    path_manager.scan()
    assert path_manager._cache
    
    # Test invalidating specific path
    path_manager.invalidate_cache(temp_dir / "dir1")
    assert str(temp_dir / "dir1") not in path_manager._cache
    
    # Test invalidating all cache
    path_manager.invalidate_cache()
    assert not path_manager._cache

def test_watch_operations(path_manager, temp_dir):
    # Add watches
    path_manager.watch(temp_dir / "dir1")
    path_manager.watch(temp_dir / "dir2")
    assert len(path_manager._watchers) == 2
    
    # Remove watch
    path_manager.unwatch(temp_dir / "dir1")
    assert len(path_manager._watchers) == 1
    assert str(temp_dir / "dir2") in path_manager._watchers 