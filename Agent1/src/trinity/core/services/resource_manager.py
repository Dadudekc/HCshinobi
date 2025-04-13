"""
Resource Management Implementation
This module implements the resource management system for handling system resources.
"""

import logging
import psutil
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ResourceType(Enum):
    """Types of system resources."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"

@dataclass
class ResourceUsage:
    """Resource usage statistics."""
    total: float
    used: float
    free: float
    percent: float

class ResourceManager:
    """Resource manager for handling system resources."""
    
    def __init__(self):
        """Initialize the resource manager."""
        self.logger = logging.getLogger(__name__)
        self.resources: Dict[ResourceType, ResourceUsage] = {}
        self._initialize_resources()
        
    def _initialize_resources(self) -> None:
        """Initialize resource tracking."""
        self.resources = {
            ResourceType.CPU: self._get_cpu_usage(),
            ResourceType.MEMORY: self._get_memory_usage(),
            ResourceType.DISK: self._get_disk_usage(),
            ResourceType.NETWORK: self._get_network_usage()
        }
        self.logger.info("Resource tracking initialized")
        
    def _get_cpu_usage(self) -> ResourceUsage:
        """Get CPU usage statistics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        return ResourceUsage(
            total=cpu_count,
            used=cpu_percent,
            free=100 - cpu_percent,
            percent=cpu_percent
        )
        
    def _get_memory_usage(self) -> ResourceUsage:
        """Get memory usage statistics."""
        memory = psutil.virtual_memory()
        return ResourceUsage(
            total=memory.total,
            used=memory.used,
            free=memory.available,
            percent=memory.percent
        )
        
    def _get_disk_usage(self) -> ResourceUsage:
        """Get disk usage statistics."""
        disk = psutil.disk_usage('/')
        return ResourceUsage(
            total=disk.total,
            used=disk.used,
            free=disk.free,
            percent=disk.percent
        )
        
    def _get_network_usage(self) -> ResourceUsage:
        """Get network usage statistics."""
        net_io = psutil.net_io_counters()
        return ResourceUsage(
            total=net_io.bytes_sent + net_io.bytes_recv,
            used=net_io.bytes_sent,
            free=net_io.bytes_recv,
            percent=0  # Network usage percentage not directly available
        )
        
    def update_resources(self) -> None:
        """Update all resource statistics."""
        self.resources[ResourceType.CPU] = self._get_cpu_usage()
        self.resources[ResourceType.MEMORY] = self._get_memory_usage()
        self.resources[ResourceType.DISK] = self._get_disk_usage()
        self.resources[ResourceType.NETWORK] = self._get_network_usage()
        self.logger.debug("Resource statistics updated")
        
    def get_resource_usage(self, resource_type: ResourceType) -> ResourceUsage:
        """Get usage statistics for a specific resource."""
        return self.resources.get(resource_type)
        
    def get_all_resources(self) -> Dict[ResourceType, ResourceUsage]:
        """Get usage statistics for all resources."""
        return self.resources.copy()
        
    def check_resource_availability(self, 
                                  resource_type: ResourceType,
                                  required_amount: float) -> bool:
        """Check if required amount of resource is available."""
        resource = self.get_resource_usage(resource_type)
        if not resource:
            return False
        return resource.free >= required_amount
        
    def allocate_resource(self,
                         resource_type: ResourceType,
                         amount: float) -> bool:
        """Allocate specified amount of resource."""
        if not self.check_resource_availability(resource_type, amount):
            return False
            
        resource = self.resources[resource_type]
        resource.used += amount
        resource.free -= amount
        resource.percent = (resource.used / resource.total) * 100
        self.logger.info(f"Allocated {amount} of {resource_type.value}")
        return True
        
    def release_resource(self,
                        resource_type: ResourceType,
                        amount: float) -> None:
        """Release specified amount of resource."""
        resource = self.resources[resource_type]
        resource.used -= amount
        resource.free += amount
        resource.percent = (resource.used / resource.total) * 100
        self.logger.info(f"Released {amount} of {resource_type.value}")
        
    def get_resource_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for resource usage thresholds."""
        alerts = []
        thresholds = {
            ResourceType.CPU: 80,
            ResourceType.MEMORY: 85,
            ResourceType.DISK: 90,
            ResourceType.NETWORK: 0  # Network alerts based on other metrics
        }
        
        for resource_type, threshold in thresholds.items():
            resource = self.get_resource_usage(resource_type)
            if resource and resource.percent > threshold:
                alerts.append({
                    "resource": resource_type.value,
                    "usage": resource.percent,
                    "threshold": threshold,
                    "message": f"{resource_type.value} usage above threshold"
                })
                
        return alerts 