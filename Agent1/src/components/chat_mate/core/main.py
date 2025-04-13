"""
Thea Task Engine - Enhanced Main Entry Point
"""

import sys
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime
from core.task_engine.orchestrator import TheaOrchestrator
from core.task_engine import task_engine
from core.task_engine.preview import generate_preview

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('thea_cleanup.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def print_campaign_progress(campaign_name: str, total_tasks: int, completed_tasks: int):
    progress = (completed_tasks / total_tasks) * 100
    print(f"\n{campaign_name} Progress: [{completed_tasks}/{total_tasks}] {progress:.1f}%")
    print("=" * 50)

def parse_args():
    parser = argparse.ArgumentParser(description="Thea Task Engine - Codebase Cleanup System")
    parser.add_argument("--preview", action="store_true", help="Generate preview without execution")
    parser.add_argument("--campaign", type=str, help="Run specific campaign (e.g., secure_core)")
    parser.add_argument("--export", action="store_true", help="Export tasks to JSON")
    return parser.parse_args()

def main():
    logger = setup_logging()
    args = parse_args()
    
    # Get the path to the todo report
    report_path = Path("chat_mate/todo_report.md")
    if not report_path.exists():
        logger.error(f"Todo report not found at {report_path}")
        sys.exit(1)
        
    try:
        if args.preview:
            logger.info("Generating preview...")
            generate_preview(str(report_path))
            return
            
        # Initialize the orchestrator
        orchestrator = TheaOrchestrator(str(report_path))
        logger.info("Initializing task engine...")
        orchestrator.initialize()
        
        if args.export:
            # Export tasks to JSON
            logger.info("Exporting tasks to JSON...")
            export_file = Path("thea_tasks_export.json")
            try:
                # Access the globally stored tasks from the engine
                tasks_to_export = task_engine.tasks
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(tasks_to_export, f, indent=2)
                logger.info(f"Tasks successfully exported to {export_file}")
            except Exception as e:
                logger.error(f"Failed to export tasks: {e}")
            return
            
        if args.campaign:
            # Run specific campaign
            logger.info(f"Running campaign: {args.campaign}")
            orchestrator.run_campaign(args.campaign)
            return
            
        # Full execution
        logger.info("Starting full campaign execution...")
        
        # Get initial status
        status = orchestrator.get_status()
        logger.info("\nInitial campaign status:")
        for campaign, info in status.items():
            logger.info(f"{info['name']}: Next run at {info['next_run']}")
            
        # Execute campaigns in priority order
        campaigns = [
            ("secure_core", "Secure the Core"),
            ("test_gaps", "Close Test Gaps"),
            ("refactor_giants", "Refactor Giants"),
            ("deduplicate", "Deduplicate & Consolidate"),
            ("enhancement", "Smart Enhancement Extraction")
        ]
        
        for campaign_id, campaign_name in campaigns:
            logger.info(f"\nStarting {campaign_name} campaign...")
            start_time = datetime.now()
            
            # Get tasks for this campaign
            tasks = task_engine.get_tasks_by_category(campaign_id.split('_')[0])
            total_tasks = len(tasks)
            completed_tasks = 0
            
            if total_tasks == 0:
                logger.info(f"No tasks found for {campaign_name}")
                continue
                
            print_campaign_progress(campaign_name, total_tasks, completed_tasks)
            
            # Run the campaign
            orchestrator.run_campaign(campaign_id)
            
            # Update progress
            completed_tasks = len([t for t in tasks if t.status == "completed"])
            print_campaign_progress(campaign_name, total_tasks, completed_tasks)
            
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"Campaign completed in {duration}")
            
        # Get final status
        final_status = orchestrator.get_status()
        logger.info("\nFinal campaign status:")
        for campaign, info in final_status.items():
            logger.info(f"{info['name']}: Last run at {info['last_run']}")
            
        # Print summary
        total_tasks = len(task_engine.tasks)
        completed_tasks = len([t for t in task_engine.tasks.values() if t.status == "completed"])
        logger.info(f"\nTotal tasks processed: {completed_tasks}/{total_tasks}")
            
    except Exception as e:
        logger.error(f"Error during cleanup process: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 