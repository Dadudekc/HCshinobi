"""
Cursor interaction utilities for the Dream.OS social media pipeline.
Handles cursor state management, chat history, and context tracking.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .common import log_event

logger = logging.getLogger('dreamos.cursor')

class CursorState:
    """Manages cursor state and context for chat interactions."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.current_file: Optional[str] = None
        self.last_command: Optional[str] = None
        
    def update_context(self, data: Dict[str, Any]) -> None:
        """Update cursor context with new data."""
        self.context.update(data)
        self._save_state()
        log_event('cursor', 'Updated context', {'data': data})
        
    def add_to_history(self, entry: Dict[str, Any]) -> None:
        """Add an entry to cursor history."""
        entry['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.history.append(entry)
        self._save_state()
        log_event('cursor', 'Added history entry', {'entry': entry})
        
    def set_current_file(self, file_path: Optional[str]) -> None:
        """Set the currently active file."""
        self.current_file = file_path
        if file_path:
            self.update_context({'current_file': file_path})
            log_event('cursor', 'Set current file', {'file': file_path})
            
    def record_command(self, command: str) -> None:
        """Record the last executed command."""
        self.last_command = command
        self.add_to_history({
            'type': 'command',
            'command': command
        })
        log_event('cursor', 'Recorded command', {'command': command})
        
    def get_file_context(self, file_path: str) -> Dict[str, Any]:
        """Get context for a specific file."""
        return {
            'path': file_path,
            'history': [
                entry for entry in self.history 
                if entry.get('file') == file_path
            ],
            'context': {
                k: v for k, v in self.context.items()
                if k.startswith(file_path)
            }
        }
        
    def clear_history(self, before: Optional[datetime] = None) -> None:
        """Clear cursor history, optionally before a specific time."""
        if before:
            self.history = [
                entry for entry in self.history
                if datetime.fromisoformat(entry['timestamp']) >= before
            ]
        else:
            self.history = []
        self._save_state()
        log_event('cursor', 'Cleared history', {'before': before})
        
    def _save_state(self) -> None:
        """Save current cursor state to disk."""
        state_file = self.workspace_root / '.cursor_state.json'
        state = {
            'context': self.context,
            'history': self.history,
            'current_file': self.current_file,
            'last_command': self.last_command,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        state_file.write_text(json.dumps(state, indent=2))
        
    def _load_state(self) -> None:
        """Load cursor state from disk."""
        state_file = self.workspace_root / '.cursor_state.json'
        if state_file.exists():
            state = json.loads(state_file.read_text())
            self.context = state.get('context', {})
            self.history = state.get('history', [])
            self.current_file = state.get('current_file')
            self.last_command = state.get('last_command')
            log_event('cursor', 'Loaded state from disk')

class ChatContext:
    """Manages chat context and history for conversations."""
    
    def __init__(self, cursor_state: CursorState):
        self.cursor_state = cursor_state
        self.messages: List[Dict[str, Any]] = []
        
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to the chat context."""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }
        self.messages.append(message)
        self.cursor_state.add_to_history({
            'type': 'chat',
            'message': message
        })
        log_event('chat', f"Added {role} message", {'content': content[:100]})
        
    def get_context(
        self,
        num_messages: Optional[int] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """Get chat context for model input."""
        messages = self.messages
        if not include_system:
            messages = [m for m in messages if m['role'] != 'system']
        if num_messages:
            messages = messages[-num_messages:]
        return messages
        
    def clear(self) -> None:
        """Clear chat context."""
        self.messages = []
        log_event('chat', 'Cleared chat context') 