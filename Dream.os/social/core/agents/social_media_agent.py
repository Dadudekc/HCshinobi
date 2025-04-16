import logging
import os
import json
import time
import random
import threading
import queue
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Updated import paths
from utils.browser_utils import get_undetected_driver
from coordination.agent_bus import AgentBus, Message # Import AgentBus and Message
from utils.content.post_context_generator import generate_context_from_governance # Updated path
# Assume setup_logging is used elsewhere or handled globally
# from utils.logging_utils import setup_logging
# from utils.cursor_utils import export_prompt_for_cursor, CURSOR_QUEUE_DIR # cursor_utils may need review/relocation
# from tools.cursor_dispatcher import dispatch_prompt_to_cursor # cursor_dispatcher was removed/empty - need alternative
from utils.feedback_processor import process_feedback # Updated path
# from strategies import FacebookStrategy, TwitterStrategy, LinkedInStrategy, RedditStrategy # Import from core.strategies now
from core.strategies import FacebookStrategy, TwitterStrategy, LinkedInStrategy # RedditStrategy maybe not implemented
# from strategy_exceptions import StrategyError, LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError
from core.exceptions.strategy_exceptions import StrategyError, LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError # Updated path

# Define constants or import from core.constants
# AGENT_ID = "SocialMediaAgent_007"
# DEFAULT_MAILBOX_BASE_DIR_NAME = "run/mailboxes"
# CURSOR_QUEUE_DIR = "run/cursor_queue" # Example, review actual path
from core.constants import AGENT_ID_SOCIAL_MEDIA as AGENT_ID # Assuming constant exists
from core.constants import DEFAULT_USER_DATA_DIR, CURSOR_QUEUE_DIR, CONFIG_FILE # Example

logger = logging.getLogger(__name__)

# Message type constants
MSG_TYPE_POST_CONTENT = "POST_CONTENT"
MSG_TYPE_GET_ANALYTICS = "GET_ANALYTICS"
MSG_TYPE_ERROR = "ERROR"
MSG_TYPE_STATUS = "STATUS"
MSG_TYPE_POST_SUCCESS = "POST_SUCCESS"
MSG_TYPE_POST_FAILURE = "POST_FAILURE"
MSG_TYPE_ANALYTICS_RESULT = "ANALYTICS_RESULT"
MSG_TYPE_ANALYTICS_FAILURE = "ANALYTICS_FAILURE"

class SocialMediaAgent:
    # Define default settings structure
    DEFAULT_CONFIG = {
        "common_settings": {
            "timeout_seconds": 30,
            "max_mentions": 20,
            "max_community_posts": 20,
            "log_snippet_length": 100,
        },
        "twitter": {
            "username": None,
            "password": None,
            "verification_email": None, # Or phone
            # Add other twitter-specific defaults here
        },
        "reddit": {
            "username": None,
            "password": None,
            "client_id": None, # Example API key default
            "client_secret": None,
             # Add other reddit-specific defaults here
       },
        "linkedin": {
            "username": None,
            "password": None,
             # Add other linkedin-specific defaults here
       },
       "facebook": {
            "username": None,
            "password": None,
             # Add other facebook-specific defaults here
       },
       "instagram": {
            "username": None,
            "password": None,
             # Add other instagram-specific defaults here
       },
        # Add sections for other platforms as needed
    }

    def __init__(self, agent_bus: AgentBus, config_path=CONFIG_FILE, user_data_dir=DEFAULT_USER_DATA_DIR):
        """Initializes the agent, loads config, registers with AgentBus."""
        self.agent_id = AGENT_ID
        self.bus = agent_bus # Store AgentBus instance
        self.config = self._load_config(config_path)
        self.user_data_dir = user_data_dir
        self.driver = None
        self.strategies = {}
        
        # Define command handlers mapping (based on message payload['action'])
        self.COMMAND_HANDLERS = {
            # Map action strings to handler methods
            MSG_TYPE_POST_CONTENT: self._handle_post_command, 
            MSG_TYPE_GET_ANALYTICS: self._handle_get_analytics_command, # Example generic analytics handler
            'login': self._handle_login_command, # Keep specific actions if needed
            'check_login_status': self._handle_check_login_status_command,
            'scrape_mentions': self._handle_scrape_mentions_command,
            'scrape_trends': self._handle_scrape_trends_command,
            'scrape_community': self._handle_scrape_community_command,
            'agent_status': self._handle_agent_status_command,
            'request_cursor_action': self._handle_request_cursor_action_command,
            'process_feedback_item': self._handle_process_feedback_item_command,
        }

        # Register agent and message handler with AgentBus
        self.bus.register_agent(self.agent_id, capabilities=["social_media_posting", "social_media_scraping"])
        # Register a single handler for messages directed to this agent
        self.bus.register_handler(self.agent_id, self.handle_bus_message)
        
        log_event("AGENT_INIT", self.agent_id, {"status": "initialized", "registered_handlers": list(self.COMMAND_HANDLERS.keys())})

    def _load_config(self, config_path):
        """Loads configuration with defaults, JSON file, and environment variable overrides."""
        # 1. Start with deep copy of defaults
        # Use deepcopy to avoid modifying the class attribute
        import copy 
        final_config = copy.deepcopy(self.DEFAULT_CONFIG)
        log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "Defaults loaded"})

        # 2. Load base config from JSON file
        base_config = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                base_config = json.load(f)
            log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "JSON file loaded", "path": config_path})
        except FileNotFoundError:
            log_event("AGENT_WARNING", self.agent_id, {"warning": "Config file not found, using defaults + env vars", "path": config_path})
            # Proceed without base config, defaults + env vars will be used
        except json.JSONDecodeError as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": f"Invalid JSON in config file: {e}. Using defaults + env vars.", "path": config_path})
            # Treat as if file not found
        except Exception as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": f"Failed to load config file: {e}. Using defaults + env vars.", "path": config_path, "details": str(e)})
            # Treat as if file not found

        # 3. Merge base_config into final_config (deep merge needed for nested dicts)
        def deep_merge_dicts(source, destination):
            """Recursively merge source dict into destination dict."""
            for key, value in source.items():
                if isinstance(value, dict):
                    # get node or create one
                    node = destination.setdefault(key, {})
                    deep_merge_dicts(value, node)
                else:
                    destination[key] = value
            return destination

        if base_config:
            final_config = deep_merge_dicts(base_config, final_config)
            log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "JSON config merged"})
            
        # 4. Apply Environment Variable Overrides
        overridden_keys = []
        # Iterate through the structure of the merged config
        for section_key, section_value in final_config.items():
            if isinstance(section_value, dict):
                for setting_key in section_value:
                    # Construct env var name (e.g., COMMON_SETTINGS_TIMEOUT_SECONDS, TWITTER_USERNAME)
                    env_var_name = f"{section_key.upper()}_{setting_key.upper()}"
                    env_var_value = os.environ.get(env_var_name)
                    
                    if env_var_value is not None:
                        original_value = final_config[section_key][setting_key]
                        # Attempt type conversion based on default value type if possible
                        default_type = type(self.DEFAULT_CONFIG.get(section_key, {}).get(setting_key))
                        try:
                            if default_type is bool:
                                converted_value = env_var_value.lower() in ('true', '1', 'yes')
                            elif default_type is int:
                                converted_value = int(env_var_value)
                            elif default_type is float:
                                converted_value = float(env_var_value)
                            else: # Assume string or NoneType
                                converted_value = env_var_value
                        except ValueError:
                            log_event("AGENT_WARNING", self.agent_id, {"warning": f"Failed to convert env var {env_var_name} ('{env_var_value}') to type {default_type}. Using raw string.", "key": f"{section_key}.{setting_key}"})
                            converted_value = env_var_value # Fallback to string
                            
                        final_config[section_key][setting_key] = converted_value
                        if converted_value != original_value:
                             # Avoid logging the actual secret value, just the key
                             overridden_keys.append(f"{section_key}.{setting_key}")
                             
        if overridden_keys:
             log_event("AGENT_CONFIG_OVERRIDE", self.agent_id, {"overridden_keys": overridden_keys})
             
        # 5. Validation (Optional - Example)
        # Check if critical keys are missing for platforms that seem enabled (e.g., have a username)
        required_platform_keys = {
             'twitter': ['username', 'password'],
             'reddit': ['username', 'password'], # Add client_id/secret if using API later
             'linkedin': ['username', 'password'],
             'facebook': ['username', 'password'],
             'instagram': ['username', 'password']
        }
        missing_critical_keys = []
        for platform, keys in required_platform_keys.items():
            platform_config = final_config.get(platform, {})
            # Check requirements only if platform seems intended for use (e.g., has a username set)
            if platform_config.get('username'): 
                 for key in keys:
                      if not platform_config.get(key):
                           missing_critical_keys.append(f"{platform}.{key}")
                           
        if missing_critical_keys:
             log_event("AGENT_CRITICAL", self.agent_id, {"error": "Missing critical configuration values after load/override", "missing_keys": missing_critical_keys})
             # Depending on severity, either raise an error or allow to proceed with limited function
             raise ValueError(f"Missing critical configuration: {missing_critical_keys}")
             
        log_event("AGENT_CONFIG_LOAD", self.agent_id, {"step": "Final config ready"})
        return final_config

    def _initialize_driver(self):
        # Ensure driver is initialized only once
        if self.driver is None:
            # print("[SocialMediaAgent] Initializing browser driver...")
            log_event("AGENT_STEP", self.agent_id, {"step": "initialize_driver"})
            try:
                self.driver = get_undetected_driver(user_data_dir=self.user_data_dir)
                if self.driver is None:
                     raise RuntimeError("get_undetected_driver returned None.")
                # print("[SocialMediaAgent] Browser driver initialized successfully.")
            except Exception as e:
                 # print(f"[SocialMediaAgent] CRITICAL: Failed to initialize browser driver: {e}")
                 log_event("AGENT_ERROR", self.agent_id, {"error": "Driver initialization failed", "details": str(e)})
                 self.driver = None # Ensure driver is None on failure
                 raise # Re-raise the exception to potentially halt execution if driver is critical
        return self.driver

    def _get_or_load_strategy(self, platform_name: str):
        """Gets the strategy instance for the platform, loading it if necessary."""
        if platform_name in self.strategies:
            # print(f"[SocialMediaAgent] Using existing strategy instance for: {platform_name}")
            return self.strategies[platform_name]

        # print(f"[SocialMediaAgent] Attempting to load strategy for: {platform_name}...")
        strategy_module_name = f"{platform_name}_strategy"
        strategy_class_name = f"{platform_name.capitalize()}Strategy"
        full_module_path = f"{STRATEGIES_PACKAGE}.{strategy_module_name}"

        try:
            # Dynamically import the strategy module
            strategy_module = importlib.import_module(full_module_path)
            strategy_class = getattr(strategy_module, strategy_class_name)

            # Initialize driver if needed (only the first time a strategy requiring it is loaded)
            # Note: Strategies needing the driver should handle potential None driver if init fails
            driver_instance = None
            # Check if the strategy likely needs a driver (can be refined)
            # A simple check could be if it inherits from a base class that uses it,
            # or inspecting __init__ signature, but this is complex.
            # For now, we initialize it defensively if ANY strategy is loaded.
            # A better approach might be needed if some strategies are API-only.
            try:
                driver_instance = self._initialize_driver()
            except RuntimeError as driver_e:
                # print(f"[SocialMediaAgent] Warning: Driver initialization failed during strategy load for {platform_name}: {driver_e}. Strategy might not function.")
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Driver init failed during strategy load", "platform": platform_name, "details": str(driver_e)})
                # Allow strategy loading to continue if driver is optional for it

            # Instantiate the strategy
            strategy_instance = strategy_class(self.config, driver_instance)
            self.strategies[platform_name] = strategy_instance # Store the instance
            # print(f"[SocialMediaAgent] Successfully loaded and initialized strategy for: {platform_name}")
            log_event("STRATEGY_LOADED", self.agent_id, {"platform": platform_name})
            return strategy_instance

        except ModuleNotFoundError:
            # print(f"[SocialMediaAgent] Error: Strategy module '{full_module_path}' not found.")
            log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy module not found", "platform": platform_name, "module": full_module_path})
        except AttributeError:
            # print(f"[SocialMediaAgent] Error: Strategy class '{strategy_class_name}' not found in '{full_module_path}'.")
            log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy class not found", "platform": platform_name, "class": strategy_class_name})
        except Exception as e:
            # print(f"[SocialMediaAgent] Error loading strategy for {platform_name}: {e}\n{traceback.format_exc()}")
            log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy loading failed", "platform": platform_name, "details": str(e)})
            
        return None # Return None on failure

    # +++ NEW HELPER METHOD +++
    def _execute_strategy_action(self, platform_name: str, action_name: str, required_method_name: str | None = None, default_return_on_error: any = False, action_args: tuple = (), action_kwargs: dict = {}):
        """
        Helper to execute a method on a loaded strategy with common error handling.
        Now catches specific StrategyError subclasses.
        """
        method_to_call = required_method_name or action_name
        log_event(f"AGENT_ACTION_START", self.agent_id, {"action": action_name, "platform": platform_name, "method": method_to_call, "args": action_args, "kwargs": action_kwargs})

        strategy = self._get_or_load_strategy(platform_name)
        if not strategy:
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": "Strategy loading failed"})
            return default_return_on_error

        if not hasattr(strategy, method_to_call):
            log_event("AGENT_WARNING", self.agent_id, {"warning": f"Strategy does not support method '{method_to_call}'", "platform": platform_name, "action": action_name})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": "Method not supported by strategy"})
            return default_return_on_error

        try:
            strategy_method = getattr(strategy, method_to_call)
            result = strategy_method(*action_args, **action_kwargs)
            log_event(f"AGENT_ACTION_SUCCESS", self.agent_id, {"action": action_name, "platform": platform_name, "result_type": type(result).__name__})
            return result
        # Catch specific strategy errors first
        except AuthenticationError as auth_e:
            error_details = f"Authentication failed for {action_name}"
            log_event("AGENT_ERROR", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(auth_e).__name__, "details": str(auth_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(auth_e)})
            # Potentially trigger specific fallback? Mark credentials as invalid?
            return default_return_on_error
        except LoginError as login_e:
            error_details = f"Login failed for {action_name}"
            log_event("AGENT_ERROR", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(login_e).__name__, "details": str(login_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(login_e)})
            # Potentially retry login later?
            return default_return_on_error
        except PostError as post_e:
            error_details = f"Posting failed for {action_name}"
            log_event("AGENT_ERROR", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(post_e).__name__, "details": str(post_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(post_e)})
            # Potentially analyze error for content issues vs. platform issues
            return default_return_on_error
        except ScrapeError as scrape_e:
            error_details = f"Scraping failed for {action_name}"
            log_event("AGENT_ERROR", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(scrape_e).__name__, "details": str(scrape_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(scrape_e)})
            # Potentially adjust scraping frequency or selectors?
            return default_return_on_error
        except RateLimitError as rate_e:
            error_details = f"Rate limit likely hit for {action_name}"
            log_event("AGENT_WARNING", self.agent_id, {"warning": error_details, "action": action_name, "platform": platform_name, "exception_type": type(rate_e).__name__, "details": str(rate_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(rate_e)})
            # Implement backoff logic here or signal to caller
            return default_return_on_error
        except ContentError as content_e:
            error_details = f"Content error during {action_name}"
            log_event("AGENT_WARNING", self.agent_id, {"warning": error_details, "action": action_name, "platform": platform_name, "exception_type": type(content_e).__name__, "details": str(content_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(content_e)})
            # Avoid retrying this content?
            return default_return_on_error
        except StrategyError as strat_e: # Catch any other specific StrategyError
            error_details = f"Strategy error during {action_name}"
            log_event("AGENT_ERROR", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(strat_e).__name__, "details": str(strat_e)})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(strat_e)})
            return default_return_on_error
        except Exception as e: # Catch any other unexpected error
            error_details = f"Unexpected error executing strategy method '{method_to_call}'"
            log_event("AGENT_CRITICAL", self.agent_id, {"error": error_details, "action": action_name, "platform": platform_name, "exception_type": type(e).__name__, "details": str(e), "traceback": traceback.format_exc()})
            log_event("AGENT_ACTION_ERROR", self.agent_id, {"action": action_name, "platform": platform_name, "error": error_details, "exception": str(e)})
            return default_return_on_error
    # +++ END HELPER METHOD +++

    def login(self, platform_name: str):
        """Logs into the specified platform using its strategy."""
        # --- REFACTORED ---
        return self._execute_strategy_action(
            platform_name=platform_name,
            action_name='login',
            default_return_on_error=False
        )
        # --- END REFACTOR ---

    def _generate_post_content(self, platform_name: str) -> tuple[str | None, dict | None]:
        """Generates post text using governance context and templates."""
        # print(f"[{self.agent_id}] Generating post content for {platform_name} from governance context...")
        context = generate_context_from_governance()
        if not context or not isinstance(context, dict):
            # print(f"[{self.agent_id}] Warning: Received invalid context from governance: {context}")
            log_event("AGENT_WARNING", self.agent_id, {"warning": "Invalid context received", "context": context})
            return None, None # Return None for text and context

        template_name = "social/generic_event.j2"
        event_type = context.get("event_type", "GENERIC_EVENT").lower()
        
        # --- Template Mapping Logic --- 
        if event_type == "proposal_status_updated":
             template_name = "social/proposal_update.j2"
        # Add more template mappings here based on event_type...
        elif event_type == "some_other_event":
             # template_name = "social/some_other_template.j2"
             pass
        # --- End Template Mapping Logic --- 

        # print(f"[{self.agent_id}] Using template: {template_name}")
        # Ensure event_type key exists for template, even if generic
        if 'event_type' not in context: context['event_type'] = event_type.upper() 
            
        rendered_text = render_template(template_name, context)
        
        if rendered_text:
            # print(f"[{self.agent_id}] Rendered Text: {rendered_text[:LOG_SNIPPET_LENGTH]}...") # Log snippet
            return rendered_text, context # Return rendered text and the context used
        else:
             # print(f"[{self.agent_id}] Error: Failed to render template {template_name}. Generating fallback text.")
             log_event("AGENT_WARNING", self.agent_id, {"warning": "Template rendering failed", "template": template_name, "context": context})
             # Fallback text generation logic
             fallback_text = "[Fallback] A general update occurred."
             if context.get("governance_update"):
                 title = context.get("title", "Governance Update")
                 summary = context.get("proposal_summary") or context.get("reflection_snippet") or context.get("general_update", "N/A")
                 status = context.get("status_update")
                 fallback_text = f"[Fallback] {title}: {summary}" + (f" (Status: {status})" if status else "")
             
             # print(f"[{self.agent_id}] Fallback Text: {fallback_text[:LOG_SNIPPET_LENGTH]}...")
             return fallback_text, context # Return fallback text and the context used

    def post(self, platform_name: str, text: str | None = None, image_path: str | None = None, use_governance_context: bool = False, **kwargs):
        """Posts content to the specified social media platform."""
        # --- REFACTORED (PARTIALLY) ---
        final_text = text
        context_used = None # For logging

        if use_governance_context:
            generated_text, context_used = self._generate_post_content(platform_name)
            if generated_text is not None:
                final_text = generated_text
            else:
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Post content generation failed. Using provided text if available.", "platform": platform_name})
                if not final_text:
                    log_event("AGENT_ERROR", self.agent_id, {"error": "Post aborted - no content available (generation failed and no text provided)", "platform": platform_name})
                    return False

        if not final_text and not image_path: # Allow image-only posts
            log_event("AGENT_WARNING", self.agent_id, {"warning": "Attempting to post with no text or image.", "platform": platform_name})
            # Proceed, strategy might handle image-only posts
            # return False # Old logic

        post_kwargs = {'text': final_text, 'image_path': image_path, **kwargs}
        result = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='post',
            action_kwargs=post_kwargs,
            default_return_on_error=False
        )

        # Additional logging specific to post outcome
        log_event("PLATFORM_POST", self.agent_id, {
            "platform": platform_name,
            "success": result,
            "text_length": len(final_text) if final_text else 0,
            "image_provided": bool(image_path),
            "governance_context_used": use_governance_context,
            "context_details": context_used, # Log context if generated
            "strategy_kwargs": kwargs # Log any extra args passed
        })
        return result
        # --- END REFACTOR ---

    def check_login_status(self, platform_name: str):
        """Checks login status for the specified platform."""
        # --- REFACTORED ---
        # Returns status (True/False) or None on error checking
        return self._execute_strategy_action(
            platform_name=platform_name,
            action_name='check_login_status',
            default_return_on_error=None # Indicate failure to check status
        )
        # --- END REFACTOR ---

    def scrape_mentions(self, platform_name: str, max_mentions: int = DEFAULT_MAX_MENTIONS):
        """Scrapes mentions using the specified platform's strategy."""
        # --- REFACTORED ---
        # Returns list of mentions or [] on error/unsupported
        results_list = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='scrape_mentions',
            action_kwargs={'max_mentions': max_mentions},
            default_return_on_error=[]
        )
        # --- END REFACTOR ---
        # ---> ADDED: Process feedback from mentions
        if results_list:
            try:
                log_event("AGENT_INFO", self.agent_id, {"message": "Processing feedback from scraped mentions...", "count": len(results_list)})
                process_feedback(results_list) # Call feedback processor
            except Exception as feedback_e:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Error processing feedback from mentions", "details": str(feedback_e), "traceback": traceback.format_exc()})
        # <--- END ADDED
        return results_list

    def scrape_trends(self, platform_name: str, **kwargs):
        """Scrapes trends using the specified platform's strategy."""
        # --- REFACTORED ---
        # Returns list of trends or [] on error/unsupported
        return self._execute_strategy_action(
            platform_name=platform_name,
            action_name='scrape_trends',
            action_kwargs=kwargs, # Pass through kwargs like region
            default_return_on_error=[]
        )
        # --- END REFACTOR ---

    def scrape_community(self, platform_name: str, **kwargs):
        """Scrapes community posts using the specified platform's strategy."""
        # --- REFACTORED ---
        # Returns list of posts or [] on error/unsupported
        results_list = self._execute_strategy_action(
            platform_name=platform_name,
            action_name='scrape_community',
            action_kwargs=kwargs, # Pass through kwargs like community_id, max_posts
            default_return_on_error=[]
        )
        # --- END REFACTOR ---
        # ---> ADDED: Process feedback from community posts
        if results_list:
            try:
                log_event("AGENT_INFO", self.agent_id, {"message": "Processing feedback from scraped community posts...", "count": len(results_list)})
                # Assuming community posts have a 'text' field like mentions
                process_feedback(results_list)
            except Exception as feedback_e:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Error processing feedback from community posts", "details": str(feedback_e), "traceback": traceback.format_exc()})
        # <--- END ADDED
        return results_list

    def _send_bus_response(self, original_message: Message, status: str, results: any = None, error_details: str | None = None):
        """Sends a response message back to the original sender via the AgentBus."""
        response_payload = {}
        if results is not None:
            response_payload["results"] = results
        if error_details is not None:
            response_payload["error"] = error_details

        # Construct response message type (e.g., POST_CONTENT_RESPONSE)
        response_type = f"{original_message.payload.get('action', original_message.type)}_RESPONSE"
        
        logger.debug(f"Sending response: Type={response_type}, Status={status}, To={original_message.sender}")
        self.bus.send_message(
            sender=self.agent_id,
            recipient=original_message.sender,
            message_type=response_type,
            payload=response_payload,
            status=status,
            request_id=original_message.id # Link response to request
        )

    # --- Bus Message Handling --- 
    def handle_bus_message(self, message: Message):
        """Processes incoming messages from the AgentBus."""
        logger.info(f"[{self.agent_id}] Received message: Type={message.type}, Sender={message.sender}")
        
        # Determine action based on message type or payload content
        action = message.payload.get("action", message.type) # Prefer payload action, fallback to type
        details = message.payload # Pass the whole payload as details
        platform = details.get("platform") # Platform might be in payload
        
        handler = self.COMMAND_HANDLERS.get(action)
        
        if handler:
            # Execute the command handler
            try:
                # Handlers now need to accept the Message object or just payload
                # Let's adapt handlers to potentially use message.id etc.
                # Refactoring handlers to accept (message: Message) might be cleaner
                # For now, passing payload (details) and platform
                # Original handlers returned: success_flag, result, error
                # We need to send a response message via the bus.
                
                # Simplified call for now, handlers need internal adaptation
                # Let's assume handlers are adapted to call _send_bus_response internally
                handler(message=message) # Pass the whole message object to handlers

            except Exception as e:
                error_msg = f"Unhandled exception in handler for action '{action}': {e}"
                logger.error(error_msg, exc_info=True)
                # Send error response back via bus
                self._send_bus_response(original_message=message, status=MSG_TYPE_ERROR, error_details=error_msg)
        else:
            error_msg = f"No handler found for action: {action}"
            logger.warning(error_msg)
            self._send_bus_response(original_message=message, status=MSG_TYPE_ERROR, error_details=error_msg)

    # --- Adapting Command Handlers --- 
    # Each _handle_... command needs to be adapted:
    # 1. Accept `message: Message` as argument.
    # 2. Extract details from `message.payload`.
    # 3. Instead of returning (success, result, error), call `self._send_bus_response`.

    # Example Adaptation for _handle_post_command (Already done)
    def _handle_post_command(self, message: Message):
        details = message.payload
        platform = details.get("platform")
        if not platform:
            self._send_bus_response(message, MSG_TYPE_POST_FAILURE, error_details="Missing 'platform' in payload")
            return
        
        text = details.get("text")
        image_path = details.get("image_path")
        use_governance = details.get("use_governance_context", False)
        kwargs = details.get("kwargs", {})
        
        try:
            post_result = self.post(platform, text=text, image_path=image_path, use_governance_context=use_governance, **kwargs)
            if post_result: # Assuming post returns True on success
                # Post ID might be part of the result, include it if available
                # Assuming self.post is adapted to return result details dict or True/False
                result_data = {"status": "posted", "details": post_result if isinstance(post_result, dict) else {}}
                self._send_bus_response(message, MSG_TYPE_POST_SUCCESS, results=result_data)
            else:
                self._send_bus_response(message, MSG_TYPE_POST_FAILURE, error_details="Post method returned failure")
        except Exception as e:
            logger.error(f"Error during post command for platform {platform}: {e}", exc_info=True)
            self._send_bus_response(message, MSG_TYPE_POST_FAILURE, error_details=f"Exception during post: {str(e)}")

    def _handle_get_analytics_command(self, message: Message):
        """Generic handler for different analytics/scraping types based on payload."""
        details = message.payload
        platform = details.get("platform")
        analytics_type = details.get("analytics_type") # e.g., "mentions", "trends", "community"
        if not platform or not analytics_type:
            self._send_bus_response(message, MSG_TYPE_ANALYTICS_FAILURE, error_details="Missing 'platform' or 'analytics_type' in payload")
            return

        results = None
        error_msg = None
        success = False
        kwargs = details.get("kwargs", {})
        
        try:
            if analytics_type == "mentions":
                max_mentions = kwargs.get('max_mentions', self.config.get('common_settings', {}).get('max_mentions', 20))
                results_list = self.scrape_mentions(platform, max_mentions=max_mentions)
                success = isinstance(results_list, list)
                if success:
                     results = {"mention_count": len(results_list), "mentions": results_list}
                     # Optional: Process feedback here if needed
                     # process_feedback(results_list)
            elif analytics_type == "trends":
                results_list = self.scrape_trends(platform, **kwargs)
                success = isinstance(results_list, list)
                if success:
                     results = {"trend_count": len(results_list), "trends": results_list}
            elif analytics_type == "community":
                community_id = kwargs.get('community_id')
                max_posts = kwargs.get('max_posts', self.config.get('common_settings', {}).get('max_community_posts', 20))
                if not community_id:
                    error_msg = "Missing 'community_id' in kwargs for scrape_community"
                else:
                    results_list = self.scrape_community(platform, community_id=community_id, max_posts=max_posts)
                    success = isinstance(results_list, list)
                    if success:
                        results = {"post_count": len(results_list), "posts": results_list}
                        # Optional: Process feedback here if needed
                        # process_feedback(results_list)
            else:
                error_msg = f"Unsupported analytics_type: {analytics_type}"
                success = False
            
            if success:
                self._send_bus_response(message, MSG_TYPE_ANALYTICS_RESULT, results=results)
            else:
                 self._send_bus_response(message, MSG_TYPE_ANALYTICS_FAILURE, error_details=error_msg or "Analytics/Scrape method returned failure")
        except Exception as e:
            logger.error(f"Error during {analytics_type} command for platform {platform}: {e}", exc_info=True)
            self._send_bus_response(message, MSG_TYPE_ANALYTICS_FAILURE, error_details=f"Exception during {analytics_type}: {str(e)}")

    def _handle_login_command(self, message: Message):
        details = message.payload
        platform = details.get("platform")
        if not platform:
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details="Missing 'platform' in payload")
            return
        try:
            success = self.login(platform)
            self._send_bus_response(message, "SUCCESS" if success else "FAILED", results={"login_attempted": True, "success": success})
        except Exception as e:
            logger.error(f"Error during login command for platform {platform}: {e}", exc_info=True)
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details=f"Exception during login: {str(e)}")

    def _handle_check_login_status_command(self, message: Message):
        details = message.payload
        platform = details.get("platform")
        if not platform:
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details="Missing 'platform' in payload")
            return
        try:
            status = self.check_login_status(platform)
            success = status is not None # Consider successful if check runs
            self._send_bus_response(message, "SUCCESS" if success else "FAILED", results={"logged_in": status})
        except Exception as e:
            logger.error(f"Error during check_login_status for platform {platform}: {e}", exc_info=True)
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details=f"Exception during check_login_status: {str(e)}")

    # Remove specific scrape handlers as they are covered by _handle_get_analytics_command
    # def _handle_scrape_mentions_command(self, message: Message): ...
    # def _handle_scrape_trends_command(self, message: Message): ...
    # def _handle_scrape_community_command(self, message: Message): ...

    def _handle_agent_status_command(self, message: Message):
        try:
            loaded_strategies = list(self.strategies.keys())
            results = {
                "agent_id": self.agent_id,
                "loaded_strategies": loaded_strategies,
                # Add more status later
            }
            self._send_bus_response(message, "SUCCESS", results=results)
        except Exception as e:
            logger.error(f"Error during agent_status command: {e}", exc_info=True)
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details=f"Exception during agent_status: {str(e)}")

    def _handle_request_cursor_action_command(self, message: Message):
        details = message.payload
        log_context = {"command": "request_cursor_action", "message_id": message.id}
        # ... (Keep payload construction logic from original handler) ...
        objective = details.get("objective")
        instruction = details.get("prompt_instruction")
        if not objective or not instruction:
            error_msg = "Missing required fields ('objective', 'prompt_instruction') in request_cursor_action details."
            log_event("AGENT_COMMAND_ERROR", self.agent_id, {**log_context, "error": error_msg})
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details=error_msg)
            return
            
        try:
            # Construct payload dictionary (same as before)
            payload_to_export = { 
                # ... (construct the full payload dict) ... 
            }
            # Export using utility
            exported_filepath = export_prompt_for_cursor(payload_to_export) # Assuming this util exists
            if exported_filepath:
                 log_event("AGENT_COMMAND_SUCCESS", self.agent_id, {**log_context, "result": "Prompt exported", "path": exported_filepath})
                 self._send_bus_response(message, "SUCCESS", results={"exported_path": exported_filepath})
            else:
                 error_msg = "Failed to export prompt payload via cursor_utils."
                 log_event("AGENT_COMMAND_ERROR", self.agent_id, {**log_context, "error": error_msg})
                 self._send_bus_response(message, MSG_TYPE_ERROR, error_details=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error constructing or exporting Cursor prompt: {e}"
            log_event("AGENT_COMMAND_ERROR", self.agent_id, {**log_context, "error": error_msg, "traceback": traceback.format_exc()})
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details=error_msg)

    def _handle_process_feedback_item_command(self, message: Message):
        details = message.payload
        feedback_id = details.get("feedback_id", "UNKNOWN_FEEDBACK")
        # ... (Keep logging and placeholder processing logic from original handler) ...
        # For now, just acknowledge receipt via bus
        try:
             # Placeholder processing
            log_event("AGENT_FEEDBACK_ITEM_PROCESSED", self.agent_id, {
                "feedback_id": feedback_id,
                "status": "logged", 
                "action_taken": "placeholder_log_only"
            })
            self._send_bus_response(message, "SUCCESS", results={"processed_feedback_id": feedback_id})
        except Exception as e:
            logger.error(f"Error processing feedback item {feedback_id}: {e}", exc_info=True)
            self._send_bus_response(message, MSG_TYPE_ERROR, error_details=f"Exception processing feedback: {str(e)}")

    # --- REMOVE Mailbox processing logic --- 
    # def process_incoming_message(self, message: dict):
    # ...
    # def run_operational_loop(...)
    # ...

    # --- Keep Shutdown Logic --- 
    def shutdown(self):
        """Cleans up resources like strategies and the browser driver."""
        log_event("AGENT_SHUTDOWN", self.agent_id, {"status": "starting"}) # Replaced print
        # Shutdown strategies first
        for platform, strategy in self.strategies.items():
            if hasattr(strategy, 'quit') and callable(getattr(strategy, 'quit')):
                try:
                    log_event("AGENT_SHUTDOWN", self.agent_id, {"message": f"Quitting strategy for {platform}..."}) # Replaced print
                    strategy.quit()
                except Exception as e:
                     # print(f"[{self.agent_id}] Error quitting strategy {platform}: {e}") # Replaced by log_event below
                     log_event("AGENT_ERROR", self.agent_id, {"error": "Strategy shutdown failed", "platform": platform, "details": str(e)})

        # Quit the browser driver if it was initialized
        if self.driver:
            try:
                log_event("AGENT_SHUTDOWN", self.agent_id, {"message": "Quitting browser driver..."}) # Replaced print
                self.driver.quit()
                self.driver = None
                log_event("AGENT_SHUTDOWN", self.agent_id, {"message": "Browser driver quit successfully."}) # Replaced print
            except Exception as e:
                # print(f"[{self.agent_id}] Error quitting driver: {e}") # Replaced by log_event below
                log_event("AGENT_ERROR", self.agent_id, {"error": "Driver shutdown failed", "details": str(e)})
        
        # log_event("AGENT_STOP", self.agent_id, {}) # Already logged here? Changed from AGENT_STOP to AGENT_SHUTDOWN
        log_event("AGENT_SHUTDOWN", self.agent_id, {"status": "complete"}) # Replaced print
        # print(f"[{self.agent_id}] Shutdown complete.") # Replaced by log_event above

# --- Main execution block ---
if __name__ == "__main__":
    # Configure logging for direct execution (if MailboxHandler didn't already)
    # ... (logging setup can be refined)
    
    log_event("AGENT_MAIN", AGENT_ID, {"status": "starting"}) # Replaced print
    agent = None 
    try:
        # Use default paths for config and mailbox
        agent = SocialMediaAgent()
        
        # Start the main loop 
        log_event("AGENT_MAIN", AGENT_ID, {"status": "starting_loop"}) # Replaced print
        agent.run_operational_loop(interval_seconds=TEST_OPERATIONAL_INTERVAL_SECONDS) # Use test interval

    except KeyboardInterrupt:
        log_event("AGENT_MAIN", AGENT_ID, {"status": "keyboard_interrupt"}) # Replaced print
    except Exception as e:
        # print(f"\nCRITICAL ERROR in main execution block: {e}") # Replaced by log_event below
        # print(traceback.format_exc()) # Included in log_event below
        log_event("AGENT_CRITICAL", AGENT_ID, {"error": "Unhandled exception in main block", "details": str(e), "traceback": traceback.format_exc()})
        # Ensure shutdown is attempted even if agent init fails partially
        if agent and hasattr(agent, 'shutdown'):
             log_event("AGENT_MAIN", AGENT_ID, {"status": "attempting_shutdown_after_error"}) # Replaced print
             agent.shutdown()
        else:
             # Log critical failure if agent couldn't even be created
             log_event("AGENT_CRITICAL", AGENT_ID, {"error": "Unhandled exception in main before/during agent init", "details": str(e)}) 
    finally:
        # Loop handles shutdown on KeyboardInterrupt, but ensure it happens for other exits
        # if agent and agent.is_running: # Need a flag if loop doesn't call shutdown
        #    agent.shutdown()
        log_event("AGENT_MAIN", AGENT_ID, {"status": "finished"}) # Replaced print