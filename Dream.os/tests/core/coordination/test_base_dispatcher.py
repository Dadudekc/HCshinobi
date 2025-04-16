"""Tests for the base dispatcher functionality."""

import pytest
from typing import Dict, Any
from core.coordination.dispatchers.base_dispatcher import BaseDispatcher

class MockDispatcher(BaseDispatcher):
    """Mock dispatcher for testing."""
    
    def __init__(self):
        super().__init__()
        self.executed_tasks = []
        
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Record task and return success."""
        self.executed_tasks.append(task)
        return {"success": True, "data": task}

def test_base_dispatcher_initialization():
    """Test dispatcher initialization."""
    dispatcher = MockDispatcher()
    assert not dispatcher.is_running
    assert dispatcher.current_task is None
    assert dispatcher.task_queue.empty()
    
def test_add_task():
    """Test adding tasks to the queue."""
    dispatcher = MockDispatcher()
    task = {"id": "test-1", "type": "test", "payload": {}}
    
    dispatcher.add_task(task)
    assert not dispatcher.task_queue.empty()
    assert dispatcher.task_queue.qsize() == 1
    
def test_run_dispatcher_loop():
    """Test the dispatcher loop processes tasks."""
    dispatcher = MockDispatcher()
    tasks = [
        {"id": "test-1", "type": "test", "payload": {"value": 1}},
        {"id": "test-2", "type": "test", "payload": {"value": 2}}
    ]
    
    # Add tasks to queue
    for task in tasks:
        dispatcher.add_task(task)
        
    # Start loop and let it process one iteration
    dispatcher.run_dispatcher_loop()
    
    # Verify tasks were executed
    assert len(dispatcher.executed_tasks) > 0
    assert dispatcher.executed_tasks[0]["id"] == "test-1"
    
def test_stop_dispatcher():
    """Test stopping the dispatcher loop."""
    dispatcher = MockDispatcher()
    dispatcher.run_dispatcher_loop()  # Start loop
    assert dispatcher.is_running
    
    dispatcher.stop()  # Stop loop
    assert not dispatcher.is_running
    
def test_get_status():
    """Test getting dispatcher status."""
    dispatcher = MockDispatcher()
    task = {"id": "test-1", "type": "test", "payload": {}}
    
    # Check initial status
    status = dispatcher.get_status()
    assert not status["is_running"]
    assert status["queue_size"] == 0
    assert status["current_task"] is None
    
    # Add task and check status
    dispatcher.add_task(task)
    status = dispatcher.get_status()
    assert status["queue_size"] == 1
    
    # Start processing and check status
    dispatcher.run_dispatcher_loop()
    status = dispatcher.get_status()
    assert status["is_running"] 