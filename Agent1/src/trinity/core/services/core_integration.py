"""
Core Integration Implementation
This module implements the integration layer connecting all core components.
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime
from .core_engine import CoreEngine
from .task_manager import TaskManager, TaskPriority
from .resource_manager import ResourceManager, ResourceType
from .monitoring_system import MonitoringSystem, AlertLevel
from .security_framework import SecurityFramework, AccessLevel

class CoreIntegration:
    """Integration layer connecting all core components."""
    
    def __init__(self, secret_key: str):
        """Initialize the core integration layer."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.security = SecurityFramework(secret_key)
        self.core_engine = CoreEngine()
        self.task_manager = TaskManager()
        self.resource_manager = ResourceManager()
        self.monitoring = MonitoringSystem()
        
        # Register monitoring metrics
        self._setup_monitoring()
        self.logger.info("Core integration initialized")
        
    def _setup_monitoring(self) -> None:
        """Setup monitoring metrics and alerts."""
        # Register resource metrics
        self.monitoring.add_metric("cpu_usage", 0)
        self.monitoring.add_metric("memory_usage", 0)
        self.monitoring.add_metric("disk_usage", 0)
        self.monitoring.add_metric("network_usage", 0)
        
        # Register task metrics
        self.monitoring.add_metric("task_queue_size", 0)
        self.monitoring.add_metric("active_tasks", 0)
        self.monitoring.add_metric("completed_tasks", 0)
        
        # Register security metrics
        self.monitoring.add_metric("failed_auth_attempts", 0)
        self.monitoring.add_metric("access_denials", 0)
        
    def submit_task(self,
                   task_data: Dict[str, Any],
                   priority: TaskPriority,
                   token: str) -> bool:
        """Submit a task with security validation."""
        # Verify access
        if not self.security.verify_access(token, AccessLevel.WRITE):
            self.monitoring.add_metric("access_denials", 1)
            return False
            
        # Check resource availability
        if not self._check_resources(task_data.get("resource_requirements", {})):
            return False
            
        # Submit task
        task_id = self.task_manager.add_task(task_data, priority)
        self.core_engine.submit_task(task_id, priority)
        
        # Update metrics
        self.monitoring.add_metric("task_queue_size", 
                                 self.task_manager.get_queue_size())
        return True
        
    def _check_resources(self, requirements: Dict[str, float]) -> bool:
        """Check if required resources are available."""
        for resource_type, amount in requirements.items():
            if not self.resource_manager.check_resource_availability(
                ResourceType(resource_type), amount
            ):
                return False
        return True
        
    def allocate_resources(self,
                         requirements: Dict[str, float],
                         token: str) -> bool:
        """Allocate resources with security validation."""
        if not self.security.verify_access(token, AccessLevel.WRITE):
            self.monitoring.add_metric("access_denials", 1)
            return False
            
        for resource_type, amount in requirements.items():
            if not self.resource_manager.allocate_resource(
                ResourceType(resource_type), amount
            ):
                return False
                
        self._update_resource_metrics()
        return True
        
    def _update_resource_metrics(self) -> None:
        """Update resource usage metrics."""
        resources = self.resource_manager.get_all_resources()
        for resource_type, usage in resources.items():
            self.monitoring.add_metric(
                f"{resource_type.value}_usage",
                usage.percent
            )
            
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and setup monitoring."""
        token = self.security.authenticate(username, password)
        if not token:
            self.monitoring.add_metric("failed_auth_attempts", 1)
            return None
            
        self.monitoring.add_metric("active_users", 1)
        return token
        
    def get_system_status(self, token: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive system status."""
        if not self.security.verify_access(token, AccessLevel.READ):
            return None
            
        return {
            "resources": self.resource_manager.get_all_resources(),
            "tasks": {
                "queue_size": self.task_manager.get_queue_size(),
                "active": self.core_engine.get_active_tasks(),
                "completed": self.core_engine.get_completed_tasks()
            },
            "monitoring": self.monitoring.get_dashboard_data(),
            "security": {
                "active_users": len(self.security.users),
                "recent_events": self.security.get_events()
            }
        }
        
    def shutdown(self, token: str) -> bool:
        """Safely shutdown the system."""
        if not self.security.verify_access(token, AccessLevel.ADMIN):
            return False
            
        # Stop task processing
        self.core_engine.stop()
        
        # Release all resources
        for resource_type in ResourceType:
            usage = self.resource_manager.get_resource_usage(resource_type)
            if usage:
                self.resource_manager.release_resource(
                    resource_type, usage.used
                )
                
        # Log shutdown event
        self.monitoring.create_alert(
            AlertLevel.INFO,
            "System shutdown initiated",
            "core_integration",
            {"timestamp": datetime.now().isoformat()}
        )
        
        return True 