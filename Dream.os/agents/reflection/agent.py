import os
import json
import traceback
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# --- Updated Imports ---
from core import config
from core.llm_parser import extract_json_from_response
from core.template_engine import default_template_engine as template_engine
from core.prompt_staging_service import stage_and_execute_prompt
from core.coordination.agent_bus import AgentBus
from core.memory.governance_memory_engine import log_event

# --- Configure Logging ---
logger = logging.getLogger(__name__)

# Add dummy log_event if needed for import error handling
try: log_event
except NameError:
    def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")

# --- Configuration ---
LOG_PATH = config.get("governance_log_path", "memory/governance_logs.json")
AGENT_ID_DEFAULT = "ReflectionAgent"

class ReflectionAgent:
    """Agent responsible for analyzing system logs and generating insights via AgentBus dispatch."""
    AGENT_NAME = AGENT_ID_DEFAULT
    CAPABILITIES = ["log_analysis", "insight_generation", "improvement_suggestion"]

    def __init__(self, agent_id: str = AGENT_ID_DEFAULT, agent_bus: AgentBus = None):
        if agent_bus is None:
            raise ValueError("AgentBus instance is required for ReflectionAgent initialization.")

        self.agent_id = agent_id
        self.agent_bus = agent_bus
        self.logs = []

        # Register with Agent Bus (Synchronous)
        try:
            registration_success = self.agent_bus.register_agent(self)
            if registration_success:
                 log_event("AGENT_REGISTERED", self.agent_id, {"message": "Successfully registered with AgentBus."})
                 logger.info(f"Agent {self.agent_id} registered successfully.")
            else:
                 log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to register with AgentBus (register_agent returned False)."})
                 logger.error("Agent registration failed.")
        except Exception as reg_e:
             log_event("AGENT_ERROR", self.agent_id, {"error": f"Exception during AgentBus registration: {reg_e}", "traceback": traceback.format_exc()})
             logger.exception("Exception during AgentBus registration.")

    def _load_logs(self, days=2):
        """Loads governance logs from the past N days."""
        if not os.path.exists(LOG_PATH):
            logger.warning(f"Log file not found at: {LOG_PATH}")
            return []

        try:
            with open(LOG_PATH, "r") as f:
                all_logs = json.load(f)
            cutoff = datetime.now() - timedelta(days=days)
            recent_logs = [
                entry for entry in all_logs
                if "timestamp" in entry and datetime.fromisoformat(entry["timestamp"]) > cutoff
            ]
            logger.debug(f"Loaded {len(recent_logs)} recent log entries.")
            return recent_logs
        except Exception as e:
            logger.error(f"Failed to load logs from {LOG_PATH}: {e}", exc_info=True)
            return []

    def analyze_logs(self) -> list:
        """Filters and prepares relevant events from recent logs."""
        logger.info("Analyzing logs...")
        self.logs = self._load_logs()
        if not self.logs:
             logger.warning("No logs loaded, cannot analyze.")
             return []
        structured_events = [
            {
                "timestamp": log.get("timestamp"),
                "event_type": log.get("event_type"),
                "source": log.get("source"),
                "details": log.get("details", {})
            }
            for log in self.logs
            if log.get("event_type") not in ["DEBUG", "TRACE"]
        ]
        logger.info(f"Found {len(structured_events)} relevant events for analysis.")
        return structured_events

    def generate_insights(self) -> dict:
        """Uses LLM or templates to extract patterns or lessons from logs."""
        logger.info("Generating insights from loaded logs...")
        if not self.logs:
            logger.warning("generate_insights called but self.logs is empty. Run analyze_logs first.")
            return {"insights": [], "summary": "No logs available.", "error": "Logs not loaded"}
        
        prompt_context = {
            "events": self.logs[-50:]  # Use only the last 50 events for efficiency
        }
        template_path = "agents/prompts/reflection/generate_insights.j2"
        try:
            prompt = template_engine.render(template_path, prompt_context)
            if not prompt: raise ValueError(f"Failed to render template: {template_path}")
            response = stage_and_execute_prompt(prompt, agent_id=self.agent_id, purpose="generate_insights")
            if not response: raise ValueError("No response from LLM for generate_insights")
            insights = extract_json_from_response(response)
            logger.info(f"Insights generated: {insights.get('summary', 'Summary N/A')}")
            return insights or {"insights": [], "summary": "No insights extracted."}
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}", exc_info=True)
            return {"error": str(e), "traceback": traceback.format_exc()}

    def suggest_improvements(self, insights: dict) -> list:
        """Returns actionable suggestions derived from generated insights."""
        logger.info("Generating improvement suggestions from insights...")
        if insights is None or "insights" not in insights or not insights["insights"]:
            logger.info("No valid insights provided to generate suggestions.")
            return []
        suggestions = [
            {
                "suggestion": insight.get("recommendation", "No suggestion found."),
                "context": insight.get("context", {})
            }
            for insight in insights["insights"]
        ]
        logger.info(f"Generated {len(suggestions)} suggestions.")
        return suggestions

    def run_reflection_cycle(self, calling_agent_id: str = "Unknown") -> Dict[str, Any]:
        """Performs a full reflection cycle: analyze logs, generate insights, suggest improvements.
        
        Called via AgentBus.dispatch(). Returns a dictionary containing results.
        Optionally dispatches results to another agent.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "run_reflection_cycle", "caller": calling_agent_id})
        logger.info(f"Received run_reflection_cycle request from {calling_agent_id}.")
        
        results = {
            "events_analyzed": 0,
            "insights": {},
            "suggestions": [],
            "status": "FAILED",
            "error": None
        }
        
        try:
            events = self.analyze_logs()
            results["events_analyzed"] = len(events)
            
            insights = self.generate_insights()
            results["insights"] = insights
            
            if insights.get("error"):
                raise Exception(f"Insight generation failed: {insights.get('error')}")
                
            suggestions = self.suggest_improvements(insights)
            results["suggestions"] = suggestions
            
            results["status"] = "COMPLETED"
            log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "run_reflection_cycle", "events_analyzed": len(events), "insights_generated": insights.get("summary", "N/A"), "suggestions_count": len(suggestions)})
            logger.info("Reflection cycle completed successfully.")

        except Exception as cycle_e:
            error_msg = f"Error during reflection cycle: {str(cycle_e)}"
            results["error"] = error_msg
            results["status"] = "FAILED"
            log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "run_reflection_cycle", "error": error_msg, "traceback": traceback.format_exc()})
            logger.exception("Error during reflection cycle.")
            
        return results
