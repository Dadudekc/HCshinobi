# social/constants.py

# Agent Identification
AGENT_ID = "SocialAgent"

# Configuration
CONFIG_FILE_NAME = "social_config.json"
STRATEGIES_PACKAGE = "social.strategies"
DEFAULT_USER_DATA_DIR = "chrome_user_data"
DEFAULT_MAILBOX_BASE_DIR_NAME = "mailbox"

# Operational Settings
DEFAULT_OPERATIONAL_INTERVAL_SECONDS = 60
TEST_OPERATIONAL_INTERVAL_SECONDS = 30
ERROR_BACKOFF_MULTIPLIER = 2
LOG_SNIPPET_LENGTH = 100

# Platform Interaction Defaults
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_MENTIONS = 20
DEFAULT_MAX_TRENDS = 50 # Note: Was implicitly default in TwitterStrategy loop
DEFAULT_MAX_COMMUNITY_POSTS = 20 