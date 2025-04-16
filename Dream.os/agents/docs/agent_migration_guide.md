# Agent Migration Guide

This guide outlines the process for migrating existing agents to use the new `BaseAgent` class and standardized message patterns.

## Overview

The new agent architecture provides:
- Standardized message handling
- Task prioritization
- Task cancellation
- Performance logging
- Error handling
- Graceful shutdown

## Migration Steps

### 1. Update Imports

```python
from dreamforge.core.coordination.base_agent import BaseAgent
from dreamforge.core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message, update_task_status
)
```

### 2. Inherit from BaseAgent

```python
class YourAgent(BaseAgent):
    def __init__(self):
        super().__init__("YourAgentID")
        # Register command handlers
        self.register_command_handler("your_command", self._handle_your_command)
```

### 3. Implement Command Handlers

```python
async def _handle_your_command(self, task: TaskMessage) -> Dict[str, Any]:
    """Handle your command type."""
    try:
        # Process the task
        result = await self._your_processing_logic(task.input_data)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 4. Override Lifecycle Hooks (Optional)

```python
async def _on_start(self):
    """Initialize agent-specific resources."""
    # Your startup logic here
    pass

async def _on_stop(self):
    """Clean up agent-specific resources."""
    # Your cleanup logic here
    pass
```

### 5. Update Main Entry Point

```python
if __name__ == "__main__":
    agent = YourAgent()
    
    try:
        asyncio.run(agent.start())
        
        # Keep running until interrupted
        while True:
            asyncio.sleep(1)
            
    except KeyboardInterrupt:
        asyncio.run(agent.stop())
    except Exception as e:
        log_event("AGENT_FATAL", agent.agent_id, {
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        sys.exit(1)
```

## Message Patterns

### Task Message Format

```python
task = create_task_message(
    task_type="your_command",
    agent_id="YourAgentID",
    input_data={
        "key": "value",
        # Your task-specific data
    },
    priority=TaskPriority.NORMAL  # Or CRITICAL, HIGH, LOW
)
```

### Task Status Updates

The BaseAgent automatically handles status updates. Your command handlers just need to return appropriate results:

```python
# Success case
return {
    "status": "success",
    "result": your_result
}

# Error case
return {
    "status": "error",
    "error": "Error message"
}
```

## Migration Checklist

For each agent:

- [ ] Update imports
- [ ] Inherit from BaseAgent
- [ ] Convert command handlers to use TaskMessage
- [ ] Register command handlers in __init__
- [ ] Update main entry point
- [ ] Add tests using BaseAgent test patterns
- [ ] Verify error handling
- [ ] Test task cancellation
- [ ] Test priority ordering
- [ ] Update documentation

## Example: Converting Legacy Agent

### Before:

```python
class LegacyAgent:
    def __init__(self):
        self.running = False
        
    async def process_task(self, task_data):
        # Direct task processing
        result = await self._do_work(task_data)
        return result
        
    async def start(self):
        self.running = True
        while self.running:
            # Poll for tasks
            tasks = await self.get_tasks()
            for task in tasks:
                await self.process_task(task)
```

### After:

```python
class ModernAgent(BaseAgent):
    def __init__(self):
        super().__init__("ModernAgent")
        self.register_command_handler("process_task", self._handle_task)
        
    async def _handle_task(self, task: TaskMessage) -> Dict[str, Any]:
        try:
            result = await self._do_work(task.input_data)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

## Testing

See `test_base_agent.py` for examples of testing patterns, including:
- Command handling
- Task cancellation
- Priority ordering
- Error scenarios
- Lifecycle events

## Common Issues

1. **Task Type Mismatch**: Ensure task types match registered handlers exactly
2. **Missing Command Handlers**: Register all supported commands in __init__
3. **Incorrect Result Format**: Always return dict with "status" key
4. **Blocking Operations**: Use async/await for all I/O operations
5. **Resource Cleanup**: Use _on_stop for proper cleanup

## Support

For migration assistance, contact the Dream.OS Core Team. 