"""Dream.OS Agent System - Overnight Automation Framework."""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TaskMetadata:
    """Metadata for task tracking and execution."""
    task_id: str
    priority: int
    estimated_complexity: float
    target_files: List[str]
    dependencies: List[str]
    success_criteria: Dict[str, Union[str, float]]
    created_at: datetime
    status: str
    owner: Optional[str] = None

@dataclass
class PromptPlan:
    """Structure for planned prompts and their execution context."""
    prompt_id: str
    task_id: str
    context: Dict[str, any]
    file_targets: List[str]
    intent: str
    dependencies: List[str]
    execution_order: int
    status: str = "pending"
    
@dataclass
class ExecutionResult:
    """Results from Cursor execution of prompts."""
    prompt_id: str
    task_id: str
    status: str
    diff: Optional[str]
    execution_time: float
    retry_attempts: int
    error_message: Optional[str]
    validation_results: Dict[str, any]

__version__ = "0.1.0" 