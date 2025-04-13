# System Health Monitoring

A comprehensive system health monitoring module for the Chat Mate application. This module provides real-time monitoring of system resources, network connectivity, and service health.

## Features

- **Asynchronous Health Checks**: Efficient parallel monitoring of multiple system components
- **Smart Caching**: Optimized metric storage with configurable history size
- **Component Monitoring**:
  - System Resources (CPU, Memory, Disk)
  - Network Connectivity and Performance
  - MongoDB Service Health
  - Redis Cache Health
- **Metric History**: Configurable storage of historical metrics with filtering capabilities
- **Alert System**: Automatic detection and logging of degraded or unhealthy components
- **Thread-Safe**: All operations are protected by locks for concurrent access

## Architecture

The module is organized into several components:

```
system_health/
├── components/
│   ├── resource_monitor.py    # System resource monitoring
│   └── network_monitor.py     # Network connectivity monitoring
├── services/
│   ├── mongodb_checker.py     # MongoDB health checker
│   └── redis_checker.py       # Redis health checker
├── utils/
│   └── status_types.py        # Health status definitions
└── monitor.py                 # Main system health monitor
```

## Usage

### Basic Usage

```python
from chat_mate.core.system_health.monitor import SystemHealthMonitor

# Create monitor instance
monitor = SystemHealthMonitor(
    driver_manager=driver_manager,
    memory_manager=memory_manager,
    thread_pool=thread_pool,
    check_interval=60,  # Check every minute
    history_size=1000   # Keep last 1000 metrics
)

# Start monitoring
monitor.start_monitoring()

# Get current health status
health = monitor.get_system_health()
print(f"System Status: {health['overall_status']}")

# Get specific component metrics
resource_usage = monitor.get_resource_usage()
network_stats = monitor.get_network_stats()
mongodb_info = monitor.get_mongodb_info()
redis_stats = monitor.get_redis_stats()

# Stop monitoring
monitor.stop_monitoring()
```

### Historical Metrics

```python
from datetime import datetime, timedelta

# Get metrics for specific component
redis_metrics = monitor.get_historical_metrics(component="redis")

# Get metrics for time range
recent_metrics = monitor.get_historical_metrics(
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)
```

## Health Status Types

- **HEALTHY**: Component is functioning normally
- **DEGRADED**: Component is functioning but with reduced performance
- **UNHEALTHY**: Component is not functioning properly

## Configuration

The monitor can be configured with several parameters:

- `check_interval`: Time between health checks (seconds)
- `history_size`: Number of historical metrics to retain
- `driver_manager`: WebDriver manager instance
- `memory_manager`: Memory manager instance
- `thread_pool`: Thread pool manager instance

## Error Handling

The monitor includes comprehensive error handling:

- Failed health checks are logged and don't stop the monitoring process
- Component errors are captured in health metrics
- Thread-safe operations prevent data corruption
- Graceful shutdown on monitoring stop

## Example

See `examples/system_health_monitor_demo.py` for a complete usage example.

## Testing

The module includes comprehensive tests:

```bash
# Run all tests
python -m pytest tests/core/system_health/

# Run specific test file
python -m pytest tests/core/system_health/test_monitor.py
```

## Contributing

When adding new features or modifying existing ones:

1. Follow the established architecture
2. Add appropriate tests
3. Update documentation
4. Ensure thread safety for concurrent operations
5. Maintain backward compatibility where possible

## Dependencies

- Python 3.7+
- `asyncio` for asynchronous operations
- `pymongo` for MongoDB health checks
- `redis` for Redis health checks 