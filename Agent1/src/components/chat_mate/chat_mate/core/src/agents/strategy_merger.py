"""
Strategy Merger Agent - Handles deduplication and merging of social media strategy files
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Any
from difflib import unified_diff
from .base_agent import BaseAgent

class StrategyMergerAgent(BaseAgent):
    def __init__(self):
        super().__init__("strategy_merger")
        self.strategy_patterns = {
            'facebook': r'facebook_strategy\.py$',
            'instagram': r'instagram_strategy\.py$',
            'twitter': r'twitter_strategy\.py$',
            'tiktok': r'tiktok_strategy\.py$'
        }
        self.duplicate_files: Dict[str, List[Path]] = {}
        
    def analyze_files(self, workspace_root: Path) -> Dict[str, List[Dict]]:
        """Analyze strategy files and identify duplicates"""
        tasks = []
        
        # Find strategy files in chat_mate/social/strategies
        strategies_dir = workspace_root / 'chat_mate' / 'social' / 'strategies'
        if not strategies_dir.exists():
            print(f"Warning: Strategies directory not found at {strategies_dir}")
            return {}
            
        # Analyze each strategy file
        for platform, pattern in self.strategy_patterns.items():
            strategy_file = None
            for file in strategies_dir.glob('*.py'):
                if re.search(pattern, str(file)):
                    strategy_file = file
                    break
                    
            if strategy_file:
                tasks.append(self._create_refactor_task(platform, strategy_file))
                
        return {'strategy_merge': tasks}
        
    def _create_refactor_task(self, platform: str, file_path: Path) -> Dict:
        """Create a task to refactor a strategy file"""
        return {
            'type': 'refactor',
            'platform': platform,
            'target_file': str(file_path),
            'priority': 80,  # High priority for refactoring
            'description': f'Refactor {platform} strategy file to reduce complexity and improve maintainability',
            'category': 'strategy_merge',
            'target_files': [str(file_path)],
            'status': 'pending',
            'metrics': {
                'file_size': file_path.stat().st_size,
                'line_count': sum(1 for _ in open(file_path, 'r', encoding='utf-8'))
            }
        }
        
    def execute_task(self, task: Dict[str, Any]) -> bool:
        """Execute a refactoring task"""
        try:
            target_file = Path(task['target_file'])
            
            # Read file content
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.readlines()
                
            print(f"\nAnalyzing {task['platform']} strategy file:")
            print(f"File: {target_file}")
            print(f"Size: {task['metrics']['file_size']} bytes")
            print(f"Lines: {task['metrics']['line_count']}")
            
            # TODO: Implement actual refactoring logic
            # For now, just analyze the file structure
            class_count = sum(1 for line in content if re.match(r'^\s*class\s+', line))
            method_count = sum(1 for line in content if re.match(r'^\s*def\s+', line))
            todo_count = sum(1 for line in content if 'TODO' in line)
            
            print(f"Structure:")
            print(f"  - Classes: {class_count}")
            print(f"  - Methods: {method_count}")
            print(f"  - TODOs: {todo_count}")
            
            # Mark task as completed if analysis was successful
            return True
            
        except Exception as e:
            print(f"Error analyzing strategy file: {str(e)}")
            return False 