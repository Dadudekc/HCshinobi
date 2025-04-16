from typing import List, Dict, Set, Optional, Generator, Union
import os
import glob
import fnmatch
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"

@dataclass
class FileNode:
    path: Path
    type: FileType
    size: int
    modified: float
    children: Optional[Dict[str, 'FileNode']] = None
    
    @property
    def name(self) -> str:
        return self.path.name
        
    @property
    def is_dir(self) -> bool:
        return self.type == FileType.DIRECTORY

class PathManager:
    """Unified path management and file system traversal."""
    
    def __init__(self, root_path: Union[str, Path]):
        self.root = Path(root_path).resolve()
        self._cache: Dict[str, FileNode] = {}
        self._watchers: Set[str] = set()
        
    def _get_file_type(self, path: Path) -> FileType:
        """Determine the type of a file system entry."""
        if path.is_symlink():
            return FileType.SYMLINK
        elif path.is_dir():
            return FileType.DIRECTORY
        elif path.is_file():
            return FileType.FILE
        return FileType.UNKNOWN
        
    def _create_node(self, path: Path, recursive: bool = False) -> FileNode:
        """Create a FileNode for the given path."""
        try:
            stat = path.stat()
            node_type = self._get_file_type(path)
            
            node = FileNode(
                path=path,
                type=node_type,
                size=stat.st_size if node_type == FileType.FILE else 0,
                modified=stat.st_mtime,
                children={} if node_type == FileType.DIRECTORY else None
            )
            
            if recursive and node.is_dir:
                for child in path.iterdir():
                    child_node = self._create_node(child, recursive=True)
                    node.children[child.name] = child_node
                    
            return node
            
        except Exception as e:
            logger.error(f"Error creating node for {path}: {e}")
            raise
            
    def scan(self, path: Optional[Union[str, Path]] = None, 
            recursive: bool = True) -> FileNode:
        """Scan a directory and build its file system tree."""
        target = Path(path or self.root).resolve()
        
        if not target.exists():
            raise FileNotFoundError(f"Path does not exist: {target}")
            
        if not str(target).startswith(str(self.root)):
            raise ValueError(f"Path {target} is outside root {self.root}")
            
        node = self._create_node(target, recursive=recursive)
        self._cache[str(target)] = node
        return node
        
    def find(self, pattern: str, path: Optional[Union[str, Path]] = None) -> List[Path]:
        """Find files matching a glob pattern."""
        base_path = Path(path or self.root).resolve()
        
        if not str(base_path).startswith(str(self.root)):
            raise ValueError(f"Path {base_path} is outside root {self.root}")
            
        matches = []
        for root, _, files in os.walk(base_path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    matches.append(Path(root) / name)
        return matches
        
    def walk(self, path: Optional[Union[str, Path]] = None) -> Generator[FileNode, None, None]:
        """Walk the file system tree, yielding each node."""
        start_node = self.scan(path)
        
        def _walk(node: FileNode) -> Generator[FileNode, None, None]:
            yield node
            if node.is_dir and node.children:
                for child in node.children.values():
                    yield from _walk(child)
                    
        yield from _walk(start_node)
        
    def get_relative_path(self, path: Union[str, Path]) -> Path:
        """Get path relative to root directory."""
        full_path = Path(path).resolve()
        
        if not str(full_path).startswith(str(self.root)):
            raise ValueError(f"Path {full_path} is outside root {self.root}")
            
        return full_path.relative_to(self.root)
        
    def get_absolute_path(self, path: Union[str, Path]) -> Path:
        """Get absolute path from root-relative path."""
        return (self.root / Path(path)).resolve()
        
    def invalidate_cache(self, path: Optional[Union[str, Path]] = None) -> None:
        """Invalidate cached file system information."""
        if path:
            target = str(Path(path).resolve())
            if target in self._cache:
                del self._cache[target]
        else:
            self._cache.clear()
            
    def watch(self, path: Union[str, Path]) -> None:
        """Add a path to the watch list."""
        target = str(Path(path).resolve())
        self._watchers.add(target)
        
    def unwatch(self, path: Union[str, Path]) -> None:
        """Remove a path from the watch list."""
        target = str(Path(path).resolve())
        self._watchers.discard(target) 