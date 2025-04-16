import unittest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
import json
import os
from datetime import datetime, timedelta, timezone
import pytest
import asyncio
import shutil
from dreamforge.core.coordination.agent_bus import Message, MessageType
from agents.reflection_agent.reflection_agent import ReflectionAgent
from dreamforge.core.governance_memory_engine import log_event
from dreamforge.core.template_engine import TemplateNotFound

# Common test configurations
TEST_CONFIG = {
    "log_dir": "test_logs",
    "runtime_dir": "test_runtime",
    "inbox_dir": "test_inbox"
}

@pytest.fixture
def agent():
    """Create a ReflectionAgent instance for testing."""
    agent = ReflectionAgent(TEST_CONFIG)
    return agent

@pytest.fixture
def test_message_factory():
    """Factory fixture for creating test messages."""
    def create_message(msg_type=MessageType.EVENT, content=None, sender="test_sender"):
        return Message(
            type=msg_type,
            content=content or {},
            sender=sender
        )
    return create_message

@pytest.fixture
async def running_agent(agent):
    """Fixture providing a started agent that's automatically cleaned up."""
    try:
        await agent.start()
        yield agent
    finally:
        await agent.stop()
        for dir_path in [TEST_CONFIG["log_dir"], TEST_CONFIG["runtime_dir"], TEST_CONFIG["inbox_dir"]]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)

class TestReflectionAgent(unittest.TestCase):
    """Unit tests for ReflectionAgent."""
    
    def setUp(self):
        self.agent = ReflectionAgent()
        self.sample_logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "event_type": "AGENT_ERROR",
                "source": "TestAgent",
                "details": {"error": "Connection failed"}
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "event_type": "TASK_COMPLETED",
                "source": "WorkerAgent",
                "details": {"task_id": "123"}
            }
        ]
        log_event("TEST_ADDED", "TestReflectionAgent", {"test_suite": "ReflectionAgent"})

    def tearDown(self):
        if hasattr(self.agent, '_memory'):
            self.agent._memory.clear()

    @patch('agents.reflection_agent.reflection_agent.log_event')
    def test_analyze_logs_with_date_range(self, mock_log_event):
        """Test log analysis with specific date range."""
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        with patch.object(self.agent, '_load_logs', return_value=self.sample_logs):
            result = self.agent.analyze_logs(start_date=start_date, end_date=end_date)
            self.assertIsInstance(result, list)
            mock_log_event.assert_called_with(
                "REFLECTION_ANALYSIS_COMPLETED",
                self.agent.agent_id,
                {
                    "analyzed_entries": len(self.sample_logs),
                    "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}"
                }
            )

    @patch('agents.reflection_agent.reflection_agent.log_event')
    def test_analyze_logs_invalid_date_range(self, mock_log_event):
        """Test log analysis with invalid date range."""
        start_date = datetime.now()
        end_date = datetime.now() - timedelta(days=7)
        result = self.agent.analyze_logs(start_date=start_date, end_date=end_date)
        self.assertEqual(result, [])
        mock_log_event.assert_called_with(
            "REFLECTION_ANALYSIS_ERROR",
            self.agent.agent_id,
            {"error": "Invalid date range: end date before start date"}
        )

    @patch('agents.reflection_agent.reflection_agent.log_event')
    def test_analyze_logs_corrupted_data(self, mock_log_event):
        """Test handling of corrupted log entries."""
        corrupted_logs = [
            {"timestamp": "invalid_date", "event_type": "TEST"},
            {"missing_timestamp": True},
            {"timestamp": datetime.now().isoformat()}  # Valid entry
        ]
        with patch.object(self.agent, '_load_logs', return_value=corrupted_logs):
            result = self.agent.analyze_logs()
            self.assertEqual(len(result), 1)
            mock_log_event.assert_any_call(
                "REFLECTION_DATA_WARNING",
                self.agent.agent_id,
                {"warning": "Corrupted log entry found", "skipped_entries": 2}
            )

@pytest.mark.asyncio
class TestReflectionAgentAsync:
    """Async tests for ReflectionAgent."""

    @pytest.mark.asyncio
    async def test_agent_bus_integration(self, running_agent, test_message_factory):
        """Test ReflectionAgent integration with AgentBus."""
        alert_msg = test_message_factory(
            content={
                "type": "governance_alert",
                "alert_id": "test_alert_1",
                "message": "Test governance alert"
            }
        )
        
        await running_agent.bus.publish(alert_msg)
        await asyncio.sleep(1)
        
        log_files = os.listdir(TEST_CONFIG["log_dir"])
        assert len(log_files) > 0
        
        with open(os.path.join(TEST_CONFIG["log_dir"], log_files[0])) as f:
            log_content = json.load(f)
            assert "test_alert_1" in str(log_content)
            assert "Test governance alert" in str(log_content)

    @pytest.mark.asyncio
    async def test_task_coordination(self, running_agent, test_message_factory):
        """Test task coordination capabilities."""
        task_msg = test_message_factory(
            content={
                "type": "task_alert",
                "task_id": "code_review_1",
                "task_type": "code_review",
                "details": {
                    "repository": "test_repo",
                    "pull_request": "123"
                }
            }
        )
        
        await running_agent.bus.publish(task_msg)
        await asyncio.sleep(1)
        
        log_files = os.listdir(TEST_CONFIG["log_dir"])
        assert len(log_files) > 0
        
        with open(os.path.join(TEST_CONFIG["log_dir"], log_files[0])) as f:
            log_content = json.load(f)
            assert "code_review_1" in str(log_content)
            assert "code_review" in str(log_content)

    @pytest.mark.asyncio
    async def test_concurrent_alert_processing(self, running_agent, test_message_factory):
        """Test handling of multiple alerts concurrently."""
        alerts = [
            test_message_factory(
                content={
                    "type": "governance_alert",
                    "alert_id": f"concurrent_alert_{i}",
                    "message": f"Test concurrent alert {i}"
                }
            ) for i in range(3)
        ]
        
        await asyncio.gather(*(running_agent.bus.publish(alert) for alert in alerts))
        await asyncio.sleep(2)
        
        log_files = os.listdir(TEST_CONFIG["log_dir"])
        assert len(log_files) > 0
        
        with open(os.path.join(TEST_CONFIG["log_dir"], log_files[0])) as f:
            log_content = json.load(f)
            log_str = str(log_content)
            for i in range(3):
                assert f"concurrent_alert_{i}" in log_str
                assert f"Test concurrent alert {i}" in log_str

    @pytest.mark.asyncio
    async def test_inbox_watching(self, running_agent):
        """Test inbox watching functionality."""
        os.makedirs(TEST_CONFIG["inbox_dir"], exist_ok=True)
        
        alert_data = {
            "type": "governance_alert",
            "alert_id": "inbox_alert_1",
            "message": "Test inbox alert"
        }
        
        alert_file_path = os.path.join(TEST_CONFIG["inbox_dir"], "test_alert.json")
        with open(alert_file_path, "w") as f:
            json.dump(alert_data, f)
        
        await asyncio.sleep(2)
        
        assert not os.path.exists(alert_file_path)
        
        log_files = os.listdir(TEST_CONFIG["log_dir"])
        assert len(log_files) > 0
        
        with open(os.path.join(TEST_CONFIG["log_dir"], log_files[0])) as f:
            log_content = json.load(f)
            assert "inbox_alert_1" in str(log_content)
            assert "Test inbox alert" in str(log_content)

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 