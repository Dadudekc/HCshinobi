"""
Mailbox handling for inter-service communication in the Dream.OS social media pipeline.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from utils.logging_utils import log_event
from utils.common import retry_on_exception
# from core import config # Removed import

# Revert to using os.getenv or direct defaults
MAILBOX_DIR = os.getenv("MAILBOX_BASE_DIR", "data/mailboxes") # Default path
MAX_RETRIES = 3 # Default retries
RETRY_DELAY = 0.5 # Default delay

class MailboxHandler:
    """Handles inter-service communication through file-based mailboxes."""
    
    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        # Use provided base_dir or the configured default
        self.base_dir = Path(base_dir or MAILBOX_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def create_mailbox(self, service_name: str) -> None:
        """Create a mailbox directory for a service."""
        mailbox_dir = self.base_dir / service_name
        mailbox_dir.mkdir(parents=True, exist_ok=True)
        log_event('mailbox', f"Created mailbox for {service_name}")
        
    def send_message(
        self,
        sender: str,
        recipient: str,
        message: Dict[str, Any],
        priority: int = 0
    ) -> None:
        """Send a message to a service's mailbox."""
        recipient_dir = self.base_dir / recipient
        if not recipient_dir.exists():
            raise ValueError(f"Mailbox not found for {recipient}")
            
        message_data = {
            'sender': sender,
            'recipient': recipient,
            'timestamp': datetime.now().isoformat(),
            'priority': priority,
            'content': message
        }
        
        message_file = recipient_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sender}.json"
        message_file.write_text(json.dumps(message_data, indent=2))
        log_event('mailbox', f"Sent message from {sender} to {recipient}")
        
    def get_messages(
        self,
        service_name: str,
        max_messages: Optional[int] = None,
        min_priority: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages from a service's mailbox."""
        mailbox_dir = self.base_dir / service_name
        if not mailbox_dir.exists():
            raise ValueError(f"Mailbox not found for {service_name}")
            
        messages = []
        for message_file in sorted(mailbox_dir.glob('*.json')):
            message_data = json.loads(message_file.read_text())
            if message_data['priority'] >= min_priority:
                messages.append(message_data)
                message_file.unlink()
                
        if max_messages:
            messages = messages[:max_messages]
            
        log_event('mailbox', f"Retrieved {len(messages)} messages for {service_name}")
        return messages
        
    def clear_mailbox(self, service_name: str) -> None:
        """Clear all messages from a service's mailbox."""
        mailbox_dir = self.base_dir / service_name
        if mailbox_dir.exists():
            for message_file in mailbox_dir.glob('*.json'):
                message_file.unlink()
        log_event('mailbox', f"Cleared mailbox for {service_name}")
        
    def delete_mailbox(self, service_name: str) -> None:
        """Delete a service's mailbox directory."""
        mailbox_dir = self.base_dir / service_name
        if mailbox_dir.exists():
            for message_file in mailbox_dir.glob('*.json'):
                message_file.unlink()
            mailbox_dir.rmdir()
        log_event('mailbox', f"Deleted mailbox for {service_name}")
        
    @retry_on_exception(max_attempts=MAX_RETRIES, delay=RETRY_DELAY)
    def broadcast_message(
        self,
        sender: str,
        message: Dict[str, Any],
        priority: int = 0,
        exclude: Optional[List[str]] = None
    ) -> None:
        """Broadcast a message to all mailboxes except excluded ones."""
        exclude = exclude or []
        for mailbox_dir in self.base_dir.iterdir():
            if mailbox_dir.is_dir() and mailbox_dir.name not in exclude:
                self.send_message(sender, mailbox_dir.name, message, priority)
        log_event('mailbox', f"Broadcast message from {sender} to all services") 