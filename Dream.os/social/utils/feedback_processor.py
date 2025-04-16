import os
import sys
import re
import json
import uuid
from datetime import datetime, timezone

# --- Project Path Setup ---
script_dir = os.path.dirname(__file__) # social/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -------------------------

# --- Dependencies ---
try:
    from dreamforge.core.governance_memory_engine import log_event
    # Access MailboxHandler to write new tasks (adjust import path if needed)
    from social.utils.mailbox_handler import MailboxHandler 
    from social.constants import AGENT_ID # To know where to send the task
except ImportError as e:
    print(f"[FeedbackProcessor] Warning: Failed to import dependencies: {e}")
    # Dummy log_event
    def log_event(event_type, source, details):
        print(f"[Dummy Logger - FeedbackProcessor] Event: {event_type}, Source: {source}, Details: {details}")
        return False
    # Dummy MailboxHandler for basic testing
    class DummyMailboxHandler:
        def __init__(self, inbox, outbox): pass
        def send_message(self, message, recipient_agent_id=None, filename_prefix=None):
            print(f"[Dummy Mailbox] Would send message: {json.dumps(message)}")
            return True # Simulate success
    MailboxHandler = DummyMailboxHandler
    AGENT_ID = "SocialAgent_Fallback"
# --------------------

_SOURCE = "FeedbackProcessor"

# --- Configuration ---
# Simple keyword matching for MVP
SUGGESTION_KEYWORDS = ['suggest', 'recommend', 'idea', 'feature', 'request', 'improve', 'add', 'create']
BUG_KEYWORDS = ['bug', 'error', 'problem', 'issue', 'fix', 'broken', 'doesn\'t work']
# Mailbox path for the target agent (SocialMediaAgent)
# Ideally get this from config or constants
DEFAULT_AGENT_MAILBOX_BASE = os.path.join(project_root, "social", ".mailbox", AGENT_ID)
AGENT_INBOX = os.path.join(DEFAULT_AGENT_MAILBOX_BASE, "inbox")
# -------------------

# Initialize Mailbox Handler to send new tasks
# Use a dedicated instance or potentially reuse one if managed globally?
# For simplicity, create one here. Error handling needed if path doesn't exist.
try:
    # Note: MailboxHandler needs outbox too, even if only sending to inbox here.
    # This feels incorrect; should ideally have a way to *just* send.
    # Using agent's own inbox/outbox for now, assuming it can write there.
    task_sender_mailbox = MailboxHandler(AGENT_INBOX, os.path.join(DEFAULT_AGENT_MAILBOX_BASE, "outbox"))
except Exception as mb_init_e:
    log_event("FEEDBACK_PROC_ERROR", _SOURCE, {"error": "Failed to initialize MailboxHandler for sending tasks", "details": str(mb_init_e)})
    # Fallback to dummy if needed and MailboxHandler wasn't already dummied
    if MailboxHandler.__name__ != 'DummyMailboxHandler':
        task_sender_mailbox = MailboxHandler(None, None) # Use dummy instance

def _extract_potential_suggestions(text: str) -> list[tuple[str, str]]:
    """Rudimentary extraction of sentences containing keywords."""
    suggestions = []
    if not text or not isinstance(text, str):
        return suggestions
        
    # Simple sentence splitting (improve later)
    sentences = re.split(r'[.!?\n]+\s*', text)
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        found_type = None
        for keyword in SUGGESTION_KEYWORDS:
            if keyword in sentence_lower:
                found_type = 'suggestion'
                break
        if not found_type:
            for keyword in BUG_KEYWORDS:
                if keyword in sentence_lower:
                    found_type = 'bug_report'
                    break
                    
        if found_type and len(sentence.strip()) > 10: # Avoid trivial matches
            suggestions.append((found_type, sentence.strip()))
            
    return suggestions

def _create_task_message(feedback_type: str, content: str, original_context: dict) -> dict:
    """Formats an identified feedback item into a task message for the agent mailbox."""
    task_id = f"feedback_task_{uuid.uuid4()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Define task structure (adapt as needed)
    command = "process_feedback_item" # New command for agent to handle
    details = {
        "feedback_id": task_id,
        "type": feedback_type, # 'suggestion', 'bug_report'
        "original_text": content,
        "source_platform": original_context.get('platform'),
        "source_author": original_context.get('author'),
        "source_url": original_context.get('url'),
        "timestamp_received": original_context.get('timestamp'),
        "processing_notes": "Extracted automatically by FeedbackProcessor."
    }
    
    message = {
        "message_id": task_id,
        "sender": _SOURCE,
        "recipient": AGENT_ID, # Target agent
        "timestamp": timestamp,
        "type": "COMMAND", # It's a command for the agent
        "command": command,
        "details": details
    }
    return message

def process_feedback(feedback_items: list[dict]):
    """
    Parses a list of feedback items (mentions, comments), identifies potential 
    suggestions or bugs using keywords, and creates task messages in the agent's inbox.

    Args:
        feedback_items: A list of dictionaries, where each dict represents a 
                        feedback item (e.g., from scraping results). Expected keys 
                        might include 'text', 'author', 'url', 'platform', 'timestamp'.
    """
    log_event("FEEDBACK_PROC_START", _SOURCE, {"item_count": len(feedback_items)})
    tasks_created = 0
    errors = 0

    if not isinstance(feedback_items, list):
        log_event("FEEDBACK_PROC_ERROR", _SOURCE, {"error": "Invalid input: feedback_items is not a list"})
        return

    for item in feedback_items:
        if not isinstance(item, dict) or 'text' not in item:
            log_event("FEEDBACK_PROC_WARN", _SOURCE, {"warning": "Skipping invalid feedback item", "item": item})
            continue

        text_content = item.get('text')
        potential_matches = _extract_potential_suggestions(text_content)

        if potential_matches:
            log_event("FEEDBACK_PROC_MATCH", _SOURCE, {"matches_found": len(potential_matches), "source_text_snippet": text_content[:100]})
            for feedback_type, extracted_content in potential_matches:
                try:
                    task_message = _create_task_message(feedback_type, extracted_content, item)
                    # Send the task message using MailboxHandler
                    # Requires MailboxHandler to be initialized correctly and AGENT_INBOX path to be valid
                    filename_prefix = f"task_{feedback_type}"
                    if task_sender_mailbox:
                        success = task_sender_mailbox.send_message(task_message, recipient_agent_id=AGENT_ID, filename_prefix=filename_prefix)
                        if success:
                            tasks_created += 1
                            log_event("FEEDBACK_PROC_TASK_CREATED", _SOURCE, {"task_id": task_message['message_id'], "type": feedback_type})
                        else:
                            errors += 1
                            log_event("FEEDBACK_PROC_ERROR", _SOURCE, {"error": "Failed to send task message via MailboxHandler", "task_details": task_message.get('details')})
                    else:
                        errors += 1
                        log_event("FEEDBACK_PROC_ERROR", _SOURCE, {"error": "MailboxHandler not available for sending task message"}) 
                        
                except Exception as e:
                    errors += 1
                    log_event("FEEDBACK_PROC_ERROR", _SOURCE, {"error": "Failed to create or send task message", "details": str(e), "original_item": item})

    log_event("FEEDBACK_PROC_FINISH", _SOURCE, {"items_processed": len(feedback_items), "tasks_created": tasks_created, "errors": errors})

# --- Example Usage ---
if __name__ == "__main__":
    print("Testing Feedback Processor...")

    # Ensure dummy inbox exists for testing send
    if not os.path.exists(AGENT_INBOX):
        try: os.makedirs(AGENT_INBOX) 
        except: print(f"Warning: Could not create dummy inbox {AGENT_INBOX}")

    dummy_feedback = [
        {
            "platform": "twitter",
            "author": "user123",
            "url": "http://twitter.com/user123/status/1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "This is great! Maybe you could add a dark mode feature? I suggest it would be really popular."
        },
        {
            "platform": "reddit",
            "author": "redditor456",
            "url": "http://reddit.com/r/some/comments/1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "Found a problem. When I click the button, I get an error 500. This bug is quite annoying."
        },
        {
            "platform": "twitter",
            "author": "anotherUser",
            "url": "http://twitter.com/anotherUser/status/2",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "Just posting my thoughts, no suggestions here."
        },
        {
            "platform": "forum",
            "author": "helpfulPerson",
             "url": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "I have an idea for improvement. What if the dashboard automatically refreshed? Also, the login seems broken sometimes."
        },
        {
            "platform": "discord",
             "text": None # Invalid item
        }
    ]

    print(f"\nProcessing {len(dummy_feedback)} feedback items...")
    process_feedback(dummy_feedback)
    
    print("\nFeedback processing test finished.")
    print(f"Check the directory '{AGENT_INBOX}' for any generated task files (if not using dummy mailbox).")

    # Simple cleanup (optional)
    # Be careful if running tests multiple times rapidly
    # try:
    #     for f in os.listdir(AGENT_INBOX):
    #         if f.startswith("task_") and f.endswith(".json"):
    #             os.remove(os.path.join(AGENT_INBOX, f))
    #     print("Cleaned up dummy task files.")
    # except Exception as clean_e:
    #     print(f"Cleanup warning: {clean_e}") 