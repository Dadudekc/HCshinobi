import pytest
import asyncio
import time
from core.utils.metrics import (
    MetricPoint, MetricCollector, TimingStats, Timer
)

@pytest.fixture
def metric_collector():
    collector = MetricCollector()
    collector._metrics.clear()  # Reset singleton state
    collector._collectors.clear()
    return collector

@pytest.mark.asyncio
async def test_record_and_get_metrics(metric_collector):
    # Record some metrics
    await metric_collector.record_metric("test_metric", 1.0)
    await metric_collector.record_metric("test_metric", 2.0)
    await metric_collector.record_metric("test_metric", 3.0)
    
    # Get all metrics
    metrics = await metric_collector.get_metrics("test_metric")
    assert len(metrics) == 3
    assert all(isinstance(m, MetricPoint) for m in metrics)
    assert [m.value for m in metrics] == [1.0, 2.0, 3.0]
    
    # Test time range filtering
    now = time.time()
    await metric_collector.record_metric("time_metric", 1.0)
    time.sleep(0.1)
    middle_time = time.time()
    time.sleep(0.1)
    await metric_collector.record_metric("time_metric", 2.0)
    
    # Get metrics in time range
    metrics = await metric_collector.get_metrics(
        "time_metric",
        start_time=middle_time
    )
    assert len(metrics) == 1
    assert metrics[0].value == 2.0

@pytest.mark.asyncio
async def test_metric_collectors(metric_collector):
    # Register collectors
    metric_collector.register_collector("cpu", lambda: 42.0)
    metric_collector.register_collector("memory", lambda: 1024)
    
    # Start collection
    await metric_collector.start_collection()
    metric_collector.set_collection_interval(0.1)  # Speed up for testing
    
    # Wait for some collections
    await asyncio.sleep(0.3)
    
    # Stop collection
    await metric_collector.stop_collection()
    
    # Verify metrics were collected
    cpu_metrics = await metric_collector.get_metrics("cpu")
    memory_metrics = await metric_collector.get_metrics("memory")
    
    assert len(cpu_metrics) > 0
    assert len(memory_metrics) > 0
    assert all(m.value == 42.0 for m in cpu_metrics)
    assert all(m.value == 1024.0 for m in memory_metrics)

@pytest.mark.asyncio
async def test_collector_error_handling(metric_collector):
    def failing_collector():
        raise ValueError("Test error")
    
    # Register failing collector
    metric_collector.register_collector("failing", failing_collector)
    
    # Start collection
    await metric_collector.start_collection()
    metric_collector.set_collection_interval(0.1)
    
    # Wait for some attempts
    await asyncio.sleep(0.3)
    
    # Stop collection
    await metric_collector.stop_collection()
    
    # Verify no metrics were recorded
    metrics = await metric_collector.get_metrics("failing")
    assert len(metrics) == 0

def test_timing_stats():
    stats = TimingStats()
    
    # Test initial state
    assert stats.count == 0
    assert stats.total_time == 0.0
    assert stats.min_time is None
    assert stats.max_time is None
    assert stats.average_time is None
    
    # Update with some values
    stats.update(1.0)
    stats.update(2.0)
    stats.update(3.0)
    
    assert stats.count == 3
    assert stats.total_time == 6.0
    assert stats.min_time == 1.0
    assert stats.max_time == 3.0
    assert stats.average_time == 2.0

@pytest.mark.asyncio
async def test_timer():
    # Use timer as context manager
    async with Timer("test_operation") as timer:
        await asyncio.sleep(0.1)
    
    # Verify timing stats
    assert timer.stats.count == 1
    assert 0.05 < timer.stats.total_time < 0.15  # Allow for some timing variance
    
    # Verify metric was recorded
    collector = MetricCollector()
    metrics = await collector.get_metrics("timer_test_operation")
    assert len(metrics) == 1
    assert 0.05 < metrics[0].value < 0.15
    
    # Test with labels
    labels = {"operation": "test", "component": "timer"}
    async with Timer("labeled_operation", labels):
        await asyncio.sleep(0.1)
    
    metrics = await collector.get_metrics("timer_labeled_operation")
    assert len(metrics) == 1
    assert metrics[0].labels == labels 