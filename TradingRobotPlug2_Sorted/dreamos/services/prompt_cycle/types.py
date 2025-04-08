from typing import TypedDict, List, Optional

class TodoItem(TypedDict):
    """Structure representing a task item derived from a TODO."""
    task_id: str
    task_name: str
    category: str
    priority: str # e.g., 'High', 'Medium', 'Low'
    complexity: Optional[str] # e.g., 'Low', 'Medium', 'High', or None
    status: str # e.g., 'To Do', 'In Progress', 'Completed'
    file_path: str
    line: int
    context: str
    dependencies: List[str]
    notes: str
    # Optional fields from FullSyncTodoManager that might be present
    created_date: Optional[str]
    last_seen: Optional[str]
    source_todo: Optional[str]
    progress: Optional[int]
    history: Optional[List[Dict]]
    removed_date: Optional[str]
    last_modified: Optional[str] 