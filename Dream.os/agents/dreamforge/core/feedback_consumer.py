import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from prometheus_client import Counter, Histogram
from .agent_protocols import FeedbackEventMessage
from .chat_memory_manager import ChatMemoryManager

logger = logging.getLogger(__name__)

# Prometheus metrics
FEEDBACK_COUNTER = Counter('feedback_events_total', 'Total feedback events processed', ['status'])
RETRY_COUNTER = Counter('feedback_retries_total', 'Total retry attempts', ['priority'])
PROCESSING_TIME = Histogram('feedback_processing_seconds', 'Time spent processing feedback')

class FeedbackProcessingError(Exception):
    """Raised when feedback processing fails."""
    pass

class FeedbackConsumerService:
    def __init__(self, chat_memory_manager: ChatMemoryManager):
        self.memory_manager = chat_memory_manager
        self.feedback_queue = asyncio.Queue()
        self.running = False
        logger.info("FeedbackConsumerService initialized")

    async def start(self):
        """Start the feedback processing loop."""
        self.running = True
        logger.info("Starting feedback processing loop")
        while self.running:
            try:
                feedback_data = await self.feedback_queue.get()
                await self.consume_feedback(feedback_data)
                self.feedback_queue.task_done()
            except Exception as e:
                logger.error(f"Error in feedback processing loop: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on errors

    async def stop(self):
        """Stop the feedback processing loop."""
        self.running = False
        logger.info("Stopping feedback processing loop")

    def _extract_metadata(self, feedback_data: Dict) -> Dict:
        """Extract and validate metadata from feedback event."""
        try:
            event = FeedbackEventMessage.from_dict(feedback_data)
            metadata = {
                "task_id": event.task_id,
                "agent_id": event.agent_id,
                "status": event.status,
                "retry_count": feedback_data.get("retry_count", 0),
                "errors": [e.to_dict() for e in event.errors],
                "timestamp": event.timestamp,
                "metrics": event.metrics.to_dict()
            }
            FEEDBACK_COUNTER.labels(status=event.status).inc()
            return metadata
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise FeedbackProcessingError(f"Invalid feedback format: {str(e)}")

    async def _determine_retry_strategy(self, metadata: Dict) -> Dict:
        """Determine if and how to retry based on metadata."""
        status = metadata.get("status")
        retry_count = metadata.get("retry_count", 0)
        error_codes = [e.get("code") for e in metadata.get("errors", [])]

        strategy = {"action": "no_retry", "priority": "none"}

        if status == "failed":
            if retry_count < self.TRIGGER_CONDITIONS["test_failure"]["retry_count"]:
                if "TEST_FAILURE" in error_codes:
                    strategy = {"action": "retry", "priority": "high"}
                elif "EMPTY_RESPONSE" in error_codes:
                    strategy = {"action": "retry", "priority": "medium"}

        elif status == "partial":
            if retry_count < self.TRIGGER_CONDITIONS["partial"]["retry_count"]:
                strategy = {"action": "retry", "priority": "low"}

        if strategy["action"] == "retry":
            RETRY_COUNTER.labels(priority=strategy["priority"]).inc()

        return strategy

    async def _generate_refined_prompt(self, feedback_data: Dict) -> Optional[str]:
        """Generate refined prompt based on feedback if needed."""
        if not feedback_data.get("requires_prompt_update"):
            return None

        try:
            # TODO: Implement prompt refinement logic
            return "Refined prompt based on feedback"
        except Exception as e:
            logger.error(f"Prompt refinement failed: {e}")
            return None

    async def consume_feedback(self, feedback_data: Dict):
        """Process feedback event and determine next actions."""
        with PROCESSING_TIME.time():
            try:
                metadata = self._extract_metadata(feedback_data)
                refined_prompt = await self._generate_refined_prompt(feedback_data)
                
                # Store feedback in memory manager
                await self.memory_manager.store_feedback(metadata, refined_prompt)
                
                # Determine retry strategy
                retry_strategy = await self._determine_retry_strategy(metadata)
                
                logger.info(f"Feedback processed. Strategy: {retry_strategy}")
                return retry_strategy
                
            except Exception as e:
                logger.error(f"Feedback consumption error: {e}")
                raise FeedbackProcessingError(str(e))

    TRIGGER_CONDITIONS = {
        "test_failure": {"priority": "high", "retry_count": 3},
        "empty_output": {"priority": "medium", "retry_count": 2},
        "partial": {"priority": "low", "retry_count": 1},
        "sentiment_threshold": {"priority": "low", "retry_count": 1}
    }

class FeedbackConsumer:
    """Consumes feedback events and potentially triggers prompt refinement."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.feedback_store = {}  # In-memory store for simplicity
        logger.info("FeedbackConsumer initialized.")
        # TODO: Initialize connection to a persistent feedback store (e.g., database, file)

    async def process_feedback(self, feedback_data: Dict[str, Any]):
        """
        Processes incoming feedback data.

        Args:
            feedback_data (Dict[str, Any]): Dictionary containing feedback details,
                                             e.g., {'task_id': ..., 'prompt_used': ..., 'outcome': 'failure', 'error': ..., 'rating': ...}
        """
        task_id = feedback_data.get('task_id')
        prompt_used = feedback_data.get('prompt_used')
        outcome = feedback_data.get('outcome')

        if not task_id or not prompt_used or not outcome:
            logger.warning(f"Received incomplete feedback data: {feedback_data}")
            return

        logger.info(f"Processing feedback for task {task_id} (Outcome: {outcome}). Storing...")
        # Store feedback (simple in-memory example)
        self.feedback_store[task_id] = feedback_data

        if outcome == 'failure':
            logger.info(f"Task {task_id} failed. Evaluating for prompt refinement.")
            await self.evaluate_and_refine_prompt(feedback_data)
        else:
            logger.debug(f"Task {task_id} succeeded or outcome ({outcome}) does not trigger refinement.")

    async def evaluate_and_refine_prompt(self, failed_feedback: Dict[str, Any]):
        """
        Evaluates feedback from a failed task and triggers prompt refinement if needed.
        Stub implementation.
        """
        prompt_to_evaluate = failed_feedback.get('prompt_used')
        error_details = failed_feedback.get('error')
        task_id = failed_feedback.get('task_id')

        logger.info(f"Evaluating prompt for task {task_id} based on failure: {error_details}")

        # TODO: Implement prompt refinement logic
        # This could involve:
        # 1. Analyzing the error and prompt content.
        # 2. Checking historical feedback for this prompt template.
        # 3. Calling an LLM to suggest modifications to the prompt.
        # 4. Storing the refined prompt suggestion.
        # 5. Potentially triggering a task to test the new prompt.

        logger.warning("Prompt refinement logic is not implemented. No refinement performed.")

        # Simulate outcome (no refinement generated)
        refinement_result = {
            "task_id": task_id,
            "original_prompt": prompt_to_evaluate,
            "refinement_performed": False,
            "reason": "Refinement logic not implemented."
        }
        # In a real implementation, this might dispatch an event or update a prompt database
        logger.debug(f"Refinement evaluation result: {refinement_result}")

    async def get_feedback_summary(self) -> Dict[str, Any]:
        """Returns a summary of stored feedback (stub)."""
        logger.info("Generating feedback summary (stub implementation).")
        summary = {
            "total_feedback_items": len(self.feedback_store),
            "failure_count": sum(1 for fb in self.feedback_store.values() if fb.get('outcome') == 'failure'),
            # TODO: Add more detailed summary statistics
        }
        logger.warning("Feedback summary is basic; detailed stats not implemented.")
        return summary

# Placeholder for potential event listener integration
async def handle_feedback_event(event: Any, feedback_consumer: FeedbackConsumer):
    if event.type == "feedback_received": # Assuming an event type
        logger.debug(f"Feedback event received: {event.data}")
        await feedback_consumer.process_feedback(event.data)
    else:
        logger.debug(f"Ignoring non-feedback event type: {event.type}") 