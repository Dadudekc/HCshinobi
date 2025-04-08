import logging
from typing import Optional, Dict
from pathlib import Path

from .types import TodoItem # Import the new TypedDict

class PromptBuilder:
    """Provides methods for constructing prompts based on tasks or other inputs."""

    logger = logging.getLogger(__name__) # Class-level logger

    @staticmethod
    def build_prompt_preview(todo: TodoItem, project_root: str, template: str) -> Optional[Dict]:
        """
        Creates a structured prompt dictionary from a TodoItem for preview/injection.

        Args:
            todo: The TodoItem containing task details.
            project_root: The root directory of the project.
            template: The path to the prompt template file.

        Returns:
            A dictionary representing the structured prompt, or None if an error occurs
            (e.g., file not found).
        """
        try:
            file_path_abs = Path(project_root) / todo["file_path"]
            if not file_path_abs.exists():
                PromptBuilder.logger.warning(f"File not found for prompt generation: {file_path_abs}")
                return None

            with open(file_path_abs, "r", encoding="utf-8") as f:
                file_content = f.read()

            prompt = {
                "type": "refactor_todo", # Keep type consistent with original logic
                "input": {
                    "task_id": todo["task_id"],
                    "task_name": todo["task_name"],
                    "category": todo["category"],
                    "priority": todo["priority"],
                    "complexity": todo.get("complexity", "Unknown"),
                    "file_path": todo["file_path"],
                    "line": todo["line"],
                    "context": todo.get("context", ""),
                    "file_content": file_content,
                    "dependencies": todo.get("dependencies", []),
                    "notes": todo.get("notes", "")
                },
                "target_file": todo["file_path"],
                "line": todo["line"],
                "template": template
            }

            return prompt

        except Exception as e:
            PromptBuilder.logger.error(f"Error creating prompt from task {todo.get('task_id', 'N/A')}: {e}")
            return None 