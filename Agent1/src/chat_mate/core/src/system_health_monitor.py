"""
This module has been refactored into the monitoring package.
Please use the new package instead:

from core.monitoring import SystemHealthMonitor, HealthStatus, HealthMetrics

The new implementation provides:
- Better separation of concerns
- Improved testability
- More maintainable code structure
- Clearer interfaces
"""

import warnings
warnings.warn(
    "SystemHealthMonitor.py is deprecated. Please use core.monitoring instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.monitoring import (
    SystemHealthMonitor as NewSystemHealthMonitor,
    HealthStatus,
    HealthMetrics,
    AlertManager,
    ServiceChecker,
    ResourceMonitor,
    MetricsStorage
)

# Re-export for backward compatibility
SystemHealthMonitor = NewSystemHealthMonitor
__all__ = [
    'SystemHealthMonitor',
    'HealthStatus',
    'HealthMetrics',
    'AlertManager',
    'ServiceChecker',
    'ResourceMonitor',
    'MetricsStorage'
] 