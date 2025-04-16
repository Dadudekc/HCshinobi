from pathlib import Path
from datetime import datetime
from typing import Optional

from core.agent_bus import agent_bus
from core.coordination.event import Event, EventType

async def dispatch_usage_block_update(
    agent_id: str,
    target_file: str,
    status: str,
    output_summary: Optional[str],
    errors: Optional[str],
    task_id: str
):
    """Dispatch standardized events related to usage block execution."""
    now_iso = datetime.utcnow().isoformat() + "Z"
    file_name = Path(target_file).name

    # 1. Usage Block Status Event
    await agent_bus._dispatcher.dispatch_event(Event(
        type=EventType.SYSTEM,
        source_id=agent_id,
        priority=1,
        data={
            "type": "usage_block_status",
            "file": target_file,
            "status": status,
            "output_summary": output_summary,
            "errors": errors,
            "timestamp": now_iso
        }
    ))

    # 2. Task Update Event
    await agent_bus._dispatcher.dispatch_event(Event(
        type=EventType.TASK,
        source_id=agent_id,
        priority=1,
        data={
            "type": "task_update",
            "task_id": task_id,
            "status": "complete" if status == "executed" and not errors else "error",
            "description": f"Usage block {status} in {file_name}",
            "priority": "high",
            "agent": agent_id,
            "timestamp": now_iso,
            "details": {"errors": errors} if errors else {}
        }
    ))

    # 3. Project Board Update Event
    await agent_bus._dispatcher.dispatch_event(Event(
        type=EventType.SYSTEM,
        source_id=agent_id,
        priority=1,
        data={
            "type": "project_board_update",
            "component": file_name,
            "usage_block": "present_and_validated" if status == "executed" and not errors else "validation_failed",
            "last_run": now_iso,
            "agent": agent_id
        }
    )) 