from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import logging
import threading
from queue import Queue, Empty
import psutil

class ResourceManager:
    """Manages database resources and connection pooling."""
    
    def __init__(self, connection_factory: Callable[[], Any],
                 pool_size: int = 10,
                 max_wait_time: int = 30,
                 idle_timeout: int = 300,
                 memory_threshold: float = 0.9):
        """Initialize resource manager.
        
        Args:
            connection_factory: Function to create new connections
            pool_size: Maximum number of connections in pool
            max_wait_time: Maximum time to wait for connection (seconds)
            idle_timeout: Time before idle connection is closed (seconds)
            memory_threshold: Memory usage threshold (0-1) for warnings
        """
        self.connection_factory = connection_factory
        self.pool_size = pool_size
        self.max_wait_time = max_wait_time
        self.idle_timeout = idle_timeout
        self.memory_threshold = memory_threshold
        
        self.logger = logging.getLogger(__name__)
        self._pool = Queue(maxsize=pool_size)
        self._active_connections = set()
        self._lock = threading.Lock()
        self._last_used = {}
        self._cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
        self._cleanup_thread.start()
        
    def get_connection(self) -> Any:
        """Get a connection from the pool.
        
        Returns:
            Database connection
            
        Raises:
            RuntimeError: If unable to get connection
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < self.max_wait_time:
            # Check memory usage
            if self._check_memory_usage():
                self.logger.warning("High memory usage detected")
                
            # Try to get connection from pool
            try:
                connection = self._pool.get_nowait()
                if self._validate_connection(connection):
                    with self._lock:
                        self._active_connections.add(connection)
                        self._last_used[connection] = datetime.now()
                    return connection
            except Empty:
                pass
                
            # Create new connection if pool not full
            with self._lock:
                if len(self._active_connections) < self.pool_size:
                    try:
                        connection = self.connection_factory()
                        self._active_connections.add(connection)
                        self._last_used[connection] = datetime.now()
                        return connection
                    except Exception as e:
                        self.logger.error(f"Failed to create connection: {str(e)}")
                        
            # Wait before retrying
            threading.Event().wait(0.1)
            
        raise RuntimeError(f"Failed to get connection within {self.max_wait_time} seconds")
        
    def return_connection(self, connection: Any) -> None:
        """Return a connection to the pool.
        
        Args:
            connection: Database connection to return
        """
        with self._lock:
            if connection in self._active_connections:
                self._active_connections.remove(connection)
                if self._validate_connection(connection):
                    try:
                        self._pool.put_nowait(connection)
                        self._last_used[connection] = datetime.now()
                    except:
                        self._close_connection(connection)
                else:
                    self._close_connection(connection)
                    
    def _validate_connection(self, connection: Any) -> bool:
        """Check if a connection is valid.
        
        Args:
            connection: Database connection to validate
            
        Returns:
            True if connection is valid
        """
        try:
            connection.execute("SELECT 1")
            return True
        except:
            return False
            
    def _close_connection(self, connection: Any) -> None:
        """Close a database connection.
        
        Args:
            connection: Database connection to close
        """
        try:
            connection.close()
        except:
            pass
        finally:
            with self._lock:
                self._active_connections.discard(connection)
                self._last_used.pop(connection, None)
                
    def _cleanup_idle_connections(self) -> None:
        """Cleanup idle connections periodically."""
        while True:
            threading.Event().wait(60)  # Check every minute
            now = datetime.now()
            
            with self._lock:
                # Check pool connections
                while not self._pool.empty():
                    try:
                        connection = self._pool.get_nowait()
                        last_used = self._last_used.get(connection)
                        
                        if (last_used and 
                            (now - last_used).total_seconds() > self.idle_timeout):
                            self._close_connection(connection)
                        else:
                            self._pool.put_nowait(connection)
                    except Empty:
                        break
                        
                # Check active connections
                for connection in list(self._active_connections):
                    last_used = self._last_used.get(connection)
                    if (last_used and 
                        (now - last_used).total_seconds() > self.idle_timeout * 2):
                        self.logger.warning(f"Connection idle for {self.idle_timeout * 2} seconds")
                        
    def _check_memory_usage(self) -> bool:
        """Check system memory usage.
        
        Returns:
            True if memory usage exceeds threshold
        """
        try:
            memory = psutil.Process().memory_percent() / 100
            return memory > self.memory_threshold
        except:
            return False
            
    def get_stats(self) -> Dict:
        """Get resource usage statistics.
        
        Returns:
            Dict containing resource statistics
        """
        with self._lock:
            return {
                "active_connections": len(self._active_connections),
                "pooled_connections": self._pool.qsize(),
                "total_connections": len(self._active_connections) + self._pool.qsize(),
                "memory_usage": psutil.Process().memory_percent() if psutil else None,
                "pool_full": self._pool.full(),
                "pool_empty": self._pool.empty()
            }
            
    def shutdown(self) -> None:
        """Shutdown the resource manager."""
        # Close all active connections
        with self._lock:
            for connection in list(self._active_connections):
                self._close_connection(connection)
                
            # Close all pooled connections
            while not self._pool.empty():
                try:
                    connection = self._pool.get_nowait()
                    self._close_connection(connection)
                except Empty:
                    break 