import os
import json
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger("AletheiaContentDispatcher")

# Import individual platform strategies with error handling
STRATEGIES = {}
try:
    from social.strategies.twitter_strategy import TwitterStrategy
    STRATEGIES["twitter"] = TwitterStrategy
except ImportError:
    logger.warning("Twitter strategy not available")

try:
    from social.strategies.linkedin_strategy import LinkedinStrategy
    STRATEGIES["linkedin"] = LinkedinStrategy
except ImportError:
    logger.warning("LinkedIn strategy not available")

try:
    from social.strategies.facebook_strategy import FacebookStrategy
    STRATEGIES["facebook"] = FacebookStrategy
except ImportError:
    logger.warning("Facebook strategy not available")

try:
    from social.strategies.instagram_strategy import InstagramStrategy
    STRATEGIES["instagram"] = InstagramStrategy
except ImportError:
    logger.warning("Instagram strategy not available")

try:
    from social.strategies.reddit_strategy import RedditStrategy
    STRATEGIES["reddit"] = RedditStrategy
except ImportError:
    logger.warning("Reddit strategy not available")

try:
    from social.strategies.stocktwits_strategy import StocktwitsStrategy
    STRATEGIES["stocktwits"] = StocktwitsStrategy
except ImportError:
    logger.warning("StockTwits strategy not available")

class AletheiaContentDispatcher:
    def __init__(self, memory_update: dict, template_dir: str = "chat_mate/content/templates"):
        self.memory_update = memory_update
        
        # Ensure template directory exists
        template_path = Path(template_dir)
        if not template_path.exists():
            logger.warning(f"Template directory not found: {template_dir}")
            template_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created template directory: {template_dir}")
            
        self.env = Environment(loader=FileSystemLoader(template_dir))

        # Initialize available platform strategies
        self.platforms = {}
        for platform, strategy_class in STRATEGIES.items():
            try:
                self.platforms[platform] = strategy_class(self.env)
                logger.info(f"✅ Initialized {platform} strategy")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {platform} strategy: {e}")

        if not self.platforms:
            logger.warning("⚠️ No platform strategies available")
        else:
            logger.info(f"🚀 AletheiaContentDispatcher initialized with {len(self.platforms)} platform strategies")

    def execute_full_dispatch(self):
        if not self.platforms:
            logger.error("❌ No platform strategies available for dispatch")
            return False
            
        logger.info("🚀 Dispatching content to all platforms...")
        success_count = 0
        
        # Iterate and post to each platform strategy
        for platform, strategy in self.platforms.items():
            try:
                logger.info(f"⚙️ Generating content for {platform.capitalize()}...")
                content = strategy.generate_content(self.memory_update)
                
                if not content:
                    logger.warning(f"⚠️ No content generated for {platform.capitalize()}")
                    continue
                
                logger.info(f"📤 Dispatching to {platform.capitalize()}...")
                if strategy.dispatch_content(content):
                    success_count += 1
                    logger.info(f"✅ {platform.capitalize()} post dispatched successfully")
                else:
                    logger.warning(f"⚠️ {platform.capitalize()} dispatch returned False")
                    
            except Exception as e:
                logger.error(f"❌ Failed to dispatch content to {platform.capitalize()}: {e}")

        logger.info(f"✅ Dispatch complete. {success_count}/{len(self.platforms)} platforms successful")
        return success_count > 0

# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    example_memory_update = {
        "project_milestones": ["Unified Social Authentication Rituals"],
        "newly_unlocked_protocols": ["Unified Social Logging Protocol (social_config)"],
        "quest_completions": ["Vanquished Complexity's Whisper"],
        "feedback_loops_triggered": ["Social Media Auto-Dispatcher Loop"]
    }

    dispatcher = AletheiaContentDispatcher(memory_update=example_memory_update)
    success = dispatcher.execute_full_dispatch()
    
    if not success:
        logger.error("❌ Content dispatch failed")
        exit(1)
