"""
Thea Task Engine - Orchestrator
"""

from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
from .agents.security_fixer import SecurityFixerAgent
from .agents.test_gap_scanner import TestGapScanner
from .agents.strategy_merger import StrategyMergerAgent
from . import task_engine

class TheaOrchestrator:
    def __init__(self, report_path: str):
        self.report_path = Path(report_path)
        self.workspace_root = self.report_path.parent
        self.campaigns = {
            'secure_core': {
                'name': 'Secure the Core',
                'agent': SecurityFixerAgent(),
                'frequency': timedelta(days=7),
                'last_run': None,
                'next_run': datetime.now()
            },
            'test_gaps': {
                'name': 'Close Test Gaps',
                'agent': TestGapScanner(),
                'frequency': timedelta(days=7),
                'last_run': None,
                'next_run': datetime.now()
            },
            'strategy_merge': {
                'name': 'Strategy File Deduplication',
                'agent': StrategyMergerAgent(),
                'frequency': timedelta(days=14),
                'last_run': None,
                'next_run': datetime.now()
            }
        }
        
    def initialize(self):
        """Initialize the orchestrator and parse tasks"""
        # Parse tasks from report
        task_engine.parse_tasks(str(self.report_path))
        
        # Analyze strategy files for deduplication
        strategy_agent = self.campaigns['strategy_merge']['agent']
        strategy_tasks = strategy_agent.analyze_files(self.workspace_root)
        
        # Add strategy merge tasks
        for platform_tasks in strategy_tasks.values():
            for task in platform_tasks:
                task_engine.add_task(task)
                
    def run_campaign(self, campaign_id: str):
        """Run a specific campaign"""
        if campaign_id not in self.campaigns:
            raise ValueError(f"Unknown campaign: {campaign_id}")
            
        campaign = self.campaigns[campaign_id]
        agent = campaign['agent']
        
        # Get tasks for this campaign
        tasks = task_engine.get_tasks_by_category(campaign_id)
        
        # Execute tasks
        for task in tasks:
            if agent.execute_task(task):
                task_engine.mark_task_completed(task)
                
        # Update campaign status
        campaign['last_run'] = datetime.now()
        campaign['next_run'] = datetime.now() + campaign['frequency']
        
    def get_status(self) -> Dict:
        """Get current status of all campaigns"""
        return {
            campaign_id: {
                'name': info['name'],
                'agent': info['agent'].name,
                'last_run': info['last_run'],
                'next_run': info['next_run']
            }
            for campaign_id, info in self.campaigns.items()
        } 