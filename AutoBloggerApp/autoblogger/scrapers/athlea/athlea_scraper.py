import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import time
import json
import jinja2
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .memory import Memory, Quest, MemoryBank
from ..chatgpt import ChatGPTScraper, HybridResponseHandler

class AthleaScraper(ChatGPTScraper):
    def __init__(self, template_dir: str = "templates", memory_dir: str = "memory_bank"):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.memory_bank = MemoryBank(memory_dir)
        
        # Setup Jinja2 environment
        template_path = Path(__file__).parent / template_dir
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_path)),
            autoescape=True
        )

    def _extract_quest_info(self, chat_content: str) -> Dict:
        """Extract quest information from chat content using ChatGPT"""
        prompt = (
            "Analyze this development conversation and extract key information in JSON format:\n\n"
            "```json\n"
            "{\n"
            '  "quest_type": "feature|blocker|refactor",\n'
            '  "title": "Brief quest title",\n'
            '  "summary": "Detailed summary",\n'
            '  "resolved": true|false,\n'
            '  "xp_gained": 100,\n'
            '  "breakthroughs": ["key breakthrough 1", "key breakthrough 2"],\n'
            '  "blockers": ["blocker 1", "blocker 2"],\n'
            '  "lore_items": ["discovered item 1", "discovered item 2"]\n'
            "}\n"
            "```\n\n"
            f"Conversation:\n{chat_content}"
        )
        
        response = self.execute_prompt_cycle(prompt)
        text_part, memory_update = self.hybrid_handler.parse_hybrid_response(response)
        
        if not memory_update:
            # Fallback to basic extraction
            return {
                "title": "Development Quest",
                "type": "feature",
                "resolved": True,
                "summary": chat_content[:200] + "...",
                "xp_gained": 100
            }
            
        return memory_update

    def _create_memory(self, chat_url: str, chat_content: str) -> Memory:
        """Create a memory object from chat content"""
        quest_info = self._extract_quest_info(chat_content)
        
        return Memory(
            level=1,  # TODO: Implement level progression
            faction="Autonomy Engineers",
            quests=[
                Quest(
                    id=f"Q{datetime.now().strftime('%m%d')}",
                    title=quest_info.get("title", "Development Quest"),
                    type=quest_info.get("quest_type", "feature"),
                    resolved=quest_info.get("resolved", True),
                    summary=quest_info.get("summary", chat_content[:200] + "..."),
                    xp_gained=quest_info.get("xp_gained", 100),
                    lore_items=quest_info.get("lore_items", [])
                )
            ],
            breakthroughs=quest_info.get("breakthroughs", ["Initial implementation"]),
            blockers=quest_info.get("blockers", ["None"]),
            timestamp=datetime.now()
        )

    def generate_devlog(self, chat_url: str, template_name: str = "technical_summary") -> Tuple[Optional[str], Optional[Dict]]:
        """
        Generate a devlog using the specified template and memory system.
        
        Args:
            chat_url: URL of the chat to process
            template_name: Name of the template to use
            
        Returns:
            Tuple[str, Dict]: Generated devlog content and memory update, or (None, None) if failed
        """
        try:
            # Navigate to chat
            self.driver.get(chat_url)
            
            # Wait for chat to load
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-message-author-role]"))
            )
            
            # Extract chat content
            chat_content = self._extract_chat_content()
            
            # Create memory
            memory = self._create_memory(chat_url, chat_content)
            
            # Save memory
            self.memory_bank.save_memory(memory)
            
            # Load template
            template = self.template_env.get_template(f"{template_name}.j2")
            
            # Render devlog
            devlog = template.render(
                level=memory.level,
                faction=memory.faction,
                quest=memory.quests[0],
                breakthroughs=memory.breakthroughs,
                blockers=memory.blockers,
                timestamp=memory.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            return devlog, memory.to_json()
            
        except Exception as e:
            self.logger.error(f"Failed to generate devlog: {str(e)}")
            return None, None

    def _extract_chat_content(self) -> str:
        """Extract the full content of the chat"""
        try:
            messages = self.get_conversation_content()
            return "\n".join(msg["content"] for msg in messages)
        except Exception as e:
            self.logger.error(f"Failed to extract chat content: {str(e)}")
            return ""

    def process_chat_history(self, max_chats: int = 10) -> List[Dict[str, Any]]:
        """
        Process recent chats and generate devlogs for each.
        
        Args:
            max_chats: Maximum number of chats to process
            
        Returns:
            List of dictionaries containing chat metadata and generated devlog
        """
        try:
            # Get list of chats
            chats = self.extract_chat_list()
            if not chats:
                return []
                
            # Process up to max_chats
            results = []
            for chat in chats[:max_chats]:
                try:
                    # Generate devlog
                    devlog_content, memory_update = self.generate_devlog(chat.url)
                    if devlog_content:
                        results.append({
                            'title': chat.title,
                            'url': chat.url,
                            'created_at': chat.created_at,
                            'devlog': devlog_content,
                            'memory': memory_update
                        })
                        # Small delay between chats
                        time.sleep(2)
                except Exception as e:
                    self.logger.error(f"Failed to process chat {chat.url}: {str(e)}")
                    continue
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to process chat history: {str(e)}")
            return [] 