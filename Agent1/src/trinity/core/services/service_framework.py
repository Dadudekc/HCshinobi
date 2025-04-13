"""
Service Framework Implementation
This module implements the core service framework for managing and coordinating services.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service status values."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class ServicePriority(Enum):
    """Service priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ServiceConfig:
    """Service configuration."""
    name: str
    priority: ServicePriority
    dependencies: List[str]
    timeout: int
    retry_count: int
    health_check_interval: int

class Service:
    """Base service class."""
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.status = ServiceStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.error_count = 0
        self.last_health_check: Optional[datetime] = None
        self.metrics: Dict[str, Any] = {}

    def start(self) -> bool:
        """Start the service."""
        try:
            self.status = ServiceStatus.STARTING
            self.start_time = datetime.now()
            self._on_start()
            self.status = ServiceStatus.RUNNING
            logger.info(f"Service {self.config.name} started successfully")
            return True
        except Exception as e:
            self.status = ServiceStatus.ERROR
            logger.error(f"Failed to start service {self.config.name}: {str(e)}")
            return False

    def stop(self) -> bool:
        """Stop the service."""
        try:
            self.status = ServiceStatus.STOPPING
            self._on_stop()
            self.status = ServiceStatus.STOPPED
            logger.info(f"Service {self.config.name} stopped successfully")
            return True
        except Exception as e:
            self.status = ServiceStatus.ERROR
            logger.error(f"Failed to stop service {self.config.name}: {str(e)}")
            return False

    def health_check(self) -> bool:
        """Perform health check."""
        try:
            self.last_health_check = datetime.now()
            is_healthy = self._check_health()
            if not is_healthy:
                self.error_count += 1
                if self.error_count >= self.config.retry_count:
                    self.status = ServiceStatus.ERROR
            else:
                self.error_count = 0
            return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for service {self.config.name}: {str(e)}")
            return False

    def _on_start(self) -> None:
        """Service-specific startup logic."""
        pass

    def _on_stop(self) -> None:
        """Service-specific shutdown logic."""
        pass

    def _check_health(self) -> bool:
        """Service-specific health check logic."""
        return True

    def add_metric(self, name: str, value: Any) -> None:
        """Add a metric to the service."""
        self.metrics[name] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert service to dictionary."""
        return {
            "name": self.config.name,
            "status": self.status.value,
            "priority": self.config.priority.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "error_count": self.error_count,
            "metrics": self.metrics
        }

class ServiceManager:
    """Service manager for coordinating services."""
    def __init__(self):
        self.services: Dict[str, Service] = {}
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize the service manager."""
        logger.info("Service manager initialized")

    def register_service(self, service: Service) -> bool:
        """Register a new service."""
        if service.config.name in self.services:
            logger.error(f"Service {service.config.name} already registered")
            return False
        
        self.services[service.config.name] = service
        logger.info(f"Service {service.config.name} registered")
        return True

    def start_service(self, name: str) -> bool:
        """Start a service."""
        if name not in self.services:
            logger.error(f"Service {name} not found")
            return False
        
        service = self.services[name]
        if service.status != ServiceStatus.STOPPED:
            logger.error(f"Service {name} is not in stopped state")
            return False
        
        # Check dependencies
        for dep in service.config.dependencies:
            if dep not in self.services:
                logger.error(f"Dependency {dep} not found for service {name}")
                return False
            if self.services[dep].status != ServiceStatus.RUNNING:
                logger.error(f"Dependency {dep} is not running for service {name}")
                return False
        
        return service.start()

    def stop_service(self, name: str) -> bool:
        """Stop a service."""
        if name not in self.services:
            logger.error(f"Service {name} not found")
            return False
        
        service = self.services[name]
        if service.status != ServiceStatus.RUNNING:
            logger.error(f"Service {name} is not in running state")
            return False
        
        return service.stop()

    def get_service_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service status."""
        if name not in self.services:
            return None
        return self.services[name].to_dict()

    def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services."""
        return {name: service.to_dict() for name, service in self.services.items()}

    def perform_health_checks(self) -> Dict[str, bool]:
        """Perform health checks on all services."""
        results = {}
        for name, service in self.services.items():
            if service.status == ServiceStatus.RUNNING:
                results[name] = service.health_check()
        return results 