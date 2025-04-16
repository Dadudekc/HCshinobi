"""ChatGPT conversation scraper utility with advanced templating and logging support."""

import os
import time
import json
import logging
import requests
import threading
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, BaseLoader, Template, TemplateNotFound
from tqdm import tqdm

logger = logging.getLogger("ChatGPTScraper")
logger.setLevel(logging.INFO)

class PromptTemplate:
    """Simple wrapper around Jinja2 Template for easier usage."""
    
    def __init__(self, template_str: str):
        """Initialize template with string."""
        self.env = Environment(loader=BaseLoader())
        self.template = self.env.from_string(template_str)
    
    def render(self, **kwargs) -> str:
        """Render template with provided context."""
        return self.template.render(**kwargs)

@dataclass
class DevLogEntry:
    """Structure for MMORPG development log entries."""
    timestamp: str
    category: str
    title: str
    description: str
    changes: List[str]
    impact: Dict[str, Any]
    version: str

class TemplateManager:
    """Manages template loading and rendering with file system support."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template manager with optional template directory."""
        if template_dir and os.path.exists(template_dir):
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.info(f"Template manager initialized with directory: {template_dir}")
        else:
            self.env = Environment(loader=BaseLoader())
            logger.info("Template manager initialized with base loader")
        
        self.templates = {}
        self._template_lock = threading.Lock()
    
    def register_template(self, name: str, template_str: str) -> None:
        """Register a new template string."""
        with self._template_lock:
            try:
                self.templates[name] = self.env.from_string(template_str)
                logger.info(f"Template registered: {name}")
            except Exception as e:
                logger.error(f"Failed to register template {name}: {e}")
                raise
    
    def load_template_file(self, name: str, filename: str) -> None:
        """Load template from file in template directory."""
        try:
            template = self.env.get_template(filename)
            with self._template_lock:
                self.templates[name] = template
            logger.info(f"Template loaded from file: {filename}")
        except TemplateNotFound:
            logger.error(f"Template file not found: {filename}")
            raise
        except Exception as e:
            logger.error(f"Failed to load template {filename}: {e}")
            raise
    
    def render(self, name: str, **kwargs) -> str:
        """Render a template with provided context."""
        template = self.templates.get(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        try:
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Template rendering failed for {name}: {e}")
            raise

class ChatGPTScraper:
    """Enhanced scraper for ChatGPT conversations with advanced templating and logging."""

    DEFAULT_DEV_LOG_TEMPLATE = '''
    Create a development log entry for an MMORPG feature with the following details:
    
    Feature: {{ feature_name }}
    Category: {{ category }}
    Version: {{ version }}
    
    Please format the response as JSON with the following structure:
    {
        "timestamp": "YYYY-MM-DD HH:MM:SS",
        "category": "{{ category }}",
        "title": "Brief feature title",
        "description": "Detailed description",
        "changes": ["List of specific changes"],
        "impact": {
            "gameplay": "Impact on gameplay",
            "balance": "Impact on game balance",
            "performance": "Impact on system performance"
        },
        "version": "{{ version }}"
    }
    '''

    PATCH_NOTES_TEMPLATE = '''
    Create patch notes for MMORPG version {{ version }} focusing on {{ feature_name }}.
    Category: {{ category }}
    
    Please format the response as JSON with the following structure:
    {
        "timestamp": "YYYY-MM-DD HH:MM:SS",
        "category": "{{ category }}",
        "title": "{{ feature_name }} Update",
        "description": "Player-friendly description of changes",
        "changes": [
            "List of changes in player-friendly language",
            "Focus on gameplay impact and new features",
            "Include quality of life improvements"
        ],
        "impact": {
            "gameplay": "How this affects the player experience",
            "balance": "Changes to game balance",
            "performance": "Technical improvements players will notice"
        },
        "version": "{{ version }}"
    }
    '''

    FEATURE_ANNOUNCEMENT_TEMPLATE = '''
    Create an exciting feature announcement for {{ feature_name }} in our MMORPG.
    Category: {{ category }}
    Version: {{ version }}
    
    Please format the response as JSON with the following structure:
    {
        "timestamp": "YYYY-MM-DD HH:MM:SS",
        "category": "{{ category }}",
        "title": "Announcing: {{ feature_name }}",
        "description": "Marketing-focused description highlighting key features",
        "changes": [
            "List of exciting new features",
            "Highlight unique selling points",
            "Emphasize player benefits"
        ],
        "impact": {
            "gameplay": "Exciting new gameplay possibilities",
            "balance": "How this enhances game balance",
            "performance": "Technical achievements"
        },
        "version": "{{ version }}"
    }
    '''

    TECHNICAL_CHANGELOG_TEMPLATE = '''
    Create a technical changelog for {{ feature_name }} implementation.
    Category: {{ category }}
    Version: {{ version }}
    
    Please format the response as JSON with the following structure:
    {
        "timestamp": "YYYY-MM-DD HH:MM:SS",
        "category": "{{ category }}",
        "title": "Technical Implementation: {{ feature_name }}",
        "description": "Technical overview of implementation details",
        "changes": [
            "List of technical changes",
            "API modifications",
            "Database schema updates",
            "Performance optimizations"
        ],
        "impact": {
            "gameplay": "System-level gameplay implications",
            "balance": "Technical aspects of balance changes",
            "performance": "Detailed performance metrics and improvements"
        },
        "version": "{{ version }}"
    }
    '''

    def __init__(self, template_dir: Optional[str] = None, output_dir: Optional[str] = None):
        """Initialize the scraper with template and output directory support."""
        self.session = requests.Session()
        self.base_url = "https://chat.openai.com"
        self._setup_session()
        
        self.template_manager = TemplateManager(template_dir)
        self.output_dir = output_dir or os.path.join(os.getcwd(), "chatgpt_output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self._register_default_templates()
        self._init_data_files()
        
        self._conversation_lock = threading.Lock()
        self._export_lock = threading.Lock()
        
        logger.info("ChatGPTScraper initialized successfully")

    def _init_data_files(self):
        """Initialize data storage files."""
        self.conversation_file = os.path.join(self.output_dir, "conversations.json")
        self.dev_log_file = os.path.join(self.output_dir, "dev_logs.json")
        self.export_index_file = os.path.join(self.output_dir, "export_index.json")
        
        self.conversations = self._load_json_file(self.conversation_file, [])
        self.dev_logs = self._load_json_file(self.dev_log_file, [])
        self.export_index = self._load_json_file(self.export_index_file, {})

    @staticmethod
    def _load_json_file(filepath: str, default: Any) -> Any:
        """Load JSON file with error handling."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
        return default

    def _save_json_file(self, filepath: str, data: Any) -> None:
        """Save data to JSON file with error handling."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")

    def _register_default_templates(self):
        """Register default templates."""
        default_templates = {
            'dev_log': self.DEFAULT_DEV_LOG_TEMPLATE,
            'patch_notes': self.PATCH_NOTES_TEMPLATE,
            'feature_announcement': self.FEATURE_ANNOUNCEMENT_TEMPLATE,
            'technical_changelog': self.TECHNICAL_CHANGELOG_TEMPLATE
        }
        
        for name, template in default_templates.items():
            self.template_manager.register_template(name, template)

    def _setup_session(self):
        """Configure session headers and settings."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def register_template(self, name: str, template_str: str):
        """Register a new prompt template."""
        self.template_manager.register_template(name, template_str)

    def get_template(self, name: str) -> Optional[Template]:
        """Get a registered template by name."""
        return self.template_manager.templates.get(name)

    async def create_dev_log_entry(
        self,
        feature_name: str,
        category: str,
        version: str,
        conversation_id: Optional[str] = None,
        template_name: str = 'dev_log'
    ) -> DevLogEntry:
        """Create a development log entry using a template."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        prompt = template.render(
            feature_name=feature_name,
            category=category,
            version=version
        )

        # Send prompt to ChatGPT
        response = await self.send_message_async(conversation_id, prompt)
        
        # Parse the response
        try:
            content = response["message"]["content"]
            # Extract JSON from the response (handle potential markdown formatting)
            json_str = content.strip('`').strip()
            if 'json' in json_str:
                json_str = json_str.split('json')[1].strip()
            
            data = json.loads(json_str)
            return DevLogEntry(**data)
            
        except Exception as e:
            logger.error(f"Failed to parse dev log response: {e}")
            raise ValueError("Invalid response format from ChatGPT")

    def parse_dev_log_response(self, response: str) -> DevLogEntry:
        """Parse a ChatGPT response into a DevLogEntry."""
        try:
            # Clean up the response string
            json_str = response.strip('`').strip()
            if 'json' in json_str.lower():
                json_str = json_str.split('json')[1].strip()
            
            data = json.loads(json_str)
            return DevLogEntry(**data)
            
        except Exception as e:
            logger.error(f"Failed to parse dev log: {e}")
            raise ValueError("Invalid dev log format")

    async def send_message_async(self, conversation_id: Optional[str], message: str) -> Dict:
        """Async version of send_message for better integration."""
        return self.send_message(conversation_id, message)

    def login(self, email: str, password: str) -> bool:
        """Authenticate with ChatGPT."""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                return True
            return False
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def verify_session(self) -> bool:
        """Verify if the current session is valid."""
        try:
            response = self.session.get(f"{self.base_url}/api/auth/session")
            return response.status_code == 200
        except Exception:
            return False

    def get_conversation_history(self, offset: int = 0, limit: int = 20) -> List[Dict]:
        """Fetch conversation history with pagination."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/conversations",
                    params={"offset": offset, "limit": limit}
                )
                
                if response.status_code == 429:
                    raise Exception("Rate limit exceeded")
                    
                if response.status_code != 200:
                    raise Exception("Failed to fetch conversation history")
                    
                data = response.json()
                return data.get("items", [])
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                time.sleep(2 ** retry_count)  # Exponential backoff
        
        return []

    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Fetch messages from a specific conversation."""
        try:
            response = self.session.get(
                f"{self.base_url}/conversation/{conversation_id}"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch messages for conversation {conversation_id}")
                
            data = response.json()
            return data.get("messages", [])
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            raise

    def send_message(self, conversation_id: str, message: str) -> Dict:
        """Send a new message in a conversation."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/conversation/{conversation_id}",
                json={"message": message}
            )
            
            if response.status_code == 429:
                raise Exception("Rate limit exceeded")
                
            if response.status_code != 200:
                raise Exception("Failed to send message")
                
            return response.json()
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def process_conversations(self, max_workers: int = 3) -> None:
        """Process multiple conversations concurrently."""
        logger.info("Starting batch conversation processing")
        conversations = self.get_conversation_history()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_single_conversation, conv): conv 
                for conv in conversations
            }
            
            for future in tqdm(as_completed(futures), total=len(conversations)):
                conv = futures[future]
                try:
                    result = future.result()
                    if result:
                        self._save_conversation_result(result)
                except Exception as e:
                    logger.error(f"Failed to process conversation: {e}")

    def _process_single_conversation(self, conversation: Dict) -> Optional[Dict]:
        """Process a single conversation and generate dev log entry."""
        try:
            messages = self.get_conversation_messages(conversation['id'])
            template = self.template_manager.get_template('dev_log')
            
            context = {
                'conversation': conversation,
                'messages': messages,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            prompt = template.render(**context)
            response = self.send_message(conversation['id'], prompt)
            
            return {
                'conversation_id': conversation['id'],
                'timestamp': context['timestamp'],
                'prompt': prompt,
                'response': response
            }
        except Exception as e:
            logger.error(f"Conversation processing failed: {e}")
            return None

    def _save_conversation_result(self, result: Dict) -> None:
        """Save processed conversation result."""
        with self._conversation_lock:
            self.conversations.append(result)
            self._save_json_file(self.conversation_file, self.conversations)
            logger.info(f"Saved result for conversation {result['conversation_id']}")

    def cleanup(self):
        """Clean up resources and save final state."""
        try:
            self._save_json_file(self.conversation_file, self.conversations)
            self._save_json_file(self.dev_log_file, self.dev_logs)
            self._save_json_file(self.export_index_file, self.export_index)
            
            if hasattr(self, 'access_token'):
                delattr(self, 'access_token')
            self.session.close()
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def export_dev_log(self, entries: List[DevLogEntry], format: str = 'markdown') -> str:
        """Export dev log entries in various formats."""
        if format == 'markdown':
            return self._export_markdown(entries)
        elif format == 'json':
            return json.dumps([vars(entry) for entry in entries], indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_markdown(self, entries: List[DevLogEntry]) -> str:
        """Export dev log entries as markdown."""
        markdown = "# MMORPG Development Log\n\n"
        
        for entry in entries:
            markdown += f"## {entry.title}\n"
            markdown += f"**Date:** {entry.timestamp}  \n"
            markdown += f"**Category:** {entry.category}  \n"
            markdown += f"**Version:** {entry.version}\n\n"
            
            markdown += f"### Description\n{entry.description}\n\n"
            
            markdown += "### Changes\n"
            for change in entry.changes:
                markdown += f"- {change}\n"
            markdown += "\n"
            
            markdown += "### Impact Analysis\n"
            for area, impact in entry.impact.items():
                markdown += f"**{area.title()}:** {impact}\n"
            
            markdown += "\n---\n\n"
        
        return markdown 