import pytest
import os
import sys

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/tests/core
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..')) # Up three levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# Modules to test and mock
from dreamforge.core import prompt_staging_service
# from dreamforge.core import llm_bridge # Not strictly needed, mocking via service module
# from dreamforge.core import governance_memory_engine # Not needed, mocking via service module

# --- Mock Functions --- 

# Store logs from mocked log_event
MOCKED_LOGS = []

def mock_log_event(event_type, agent_source, details):
    print(f"Mock Log Event: {event_type} | {agent_source} | {details}") # For test visibility
    MOCKED_LOGS.append({
        "event_type": event_type,
        "agent_source": agent_source,
        "details": details
    })
    return True # Assume logging success

def mock_call_llm_success(prompt, llm_config):
    print(f"Mock LLM Call (Success): Config={llm_config}, Prompt='{prompt[:30]}...'")
    return f"Successful response for: {prompt[:50]}..."

def mock_call_llm_failure(prompt, llm_config):
    print(f"Mock LLM Call (Failure): Config={llm_config}, Prompt='{prompt[:30]}...'")
    return None

# --- Test Fixture --- 

@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    """Apply mocks for log_event and call_llm before each test."""
    MOCKED_LOGS.clear() # Clear logs before each test
    monkeypatch.setattr(prompt_staging_service, "log_event", mock_log_event)
    # Default mock for call_llm is success, tests can override if needed
    monkeypatch.setattr(prompt_staging_service, "call_llm", mock_call_llm_success)
    yield
    # Teardown (if any) happens after yield

# --- Test Cases --- 

def test_stage_and_execute_success():
    """Test successful staging, execution (mocked), and logging."""
    agent_id = "Agent_Success"
    subject = "Test Subject Success"
    prompt = "This is the prompt content for a successful call."
    config = {"temp": 0.7}
    
    response = prompt_staging_service.stage_and_execute_prompt(agent_id, subject, prompt, config)
    
    # Check response
    assert response is not None
    assert response.startswith("Successful response for:")
    assert prompt[:50] in response
    
    # Check logs
    assert len(MOCKED_LOGS) == 2
    # Log 1: Staged
    assert MOCKED_LOGS[0]["event_type"] == "PROMPT_STAGED"
    assert MOCKED_LOGS[0]["agent_source"] == prompt_staging_service._SOURCE_ID
    assert MOCKED_LOGS[0]["details"]["agent_source"] == agent_id
    assert MOCKED_LOGS[0]["details"]["prompt_subject"] == subject
    assert MOCKED_LOGS[0]["details"]["prompt_context_snippet"].startswith(prompt[:150])
    assert MOCKED_LOGS[0]["details"]["llm_config_keys"] == list(config.keys())
    # Log 2: Completed
    assert MOCKED_LOGS[1]["event_type"] == "PROMPT_COMPLETED"
    assert MOCKED_LOGS[1]["agent_source"] == prompt_staging_service._SOURCE_ID
    assert MOCKED_LOGS[1]["details"]["agent_source"] == agent_id
    assert MOCKED_LOGS[1]["details"]["prompt_subject"] == subject
    assert MOCKED_LOGS[1]["details"]["response_snippet"].startswith(response[:150])

def test_stage_and_execute_llm_failure(monkeypatch):
    """Test handling when the mocked LLM call returns None."""
    # Override default mock for this test
    monkeypatch.setattr(prompt_staging_service, "call_llm", mock_call_llm_failure)
    
    agent_id = "Agent_Fail"
    subject = "Test Subject Failure"
    prompt = "This prompt content will trigger a simulated LLM failure."
    
    response = prompt_staging_service.stage_and_execute_prompt(agent_id, subject, prompt)
    
    # Check response
    assert response is None
    
    # Check logs
    assert len(MOCKED_LOGS) == 2
    # Log 1: Staged
    assert MOCKED_LOGS[0]["event_type"] == "PROMPT_STAGED"
    # Log 2: Failed
    assert MOCKED_LOGS[1]["event_type"] == "PROMPT_FAILED"
    assert MOCKED_LOGS[1]["agent_source"] == prompt_staging_service._SOURCE_ID
    assert MOCKED_LOGS[1]["details"]["agent_source"] == agent_id
    assert MOCKED_LOGS[1]["details"]["prompt_subject"] == subject
    assert "LLM call failed" in MOCKED_LOGS[1]["details"]["error"]

def test_stage_and_execute_no_config():
    """Test calling the service without providing an llm_config."""
    agent_id = "Agent_NoConf"
    subject = "Test Subject No Config"
    prompt = "Prompt without specific config."
    
    response = prompt_staging_service.stage_and_execute_prompt(agent_id, subject, prompt)
    
    # Check response (should succeed with default mock)
    assert response is not None
    assert response.startswith("Successful response for:")
    
    # Check logs (specifically config keys)
    assert len(MOCKED_LOGS) == 2
    assert MOCKED_LOGS[0]["event_type"] == "PROMPT_STAGED"
    assert MOCKED_LOGS[0]["details"]["llm_config_keys"] == [] # Expect empty list

def test_stage_and_execute_invalid_inputs():
    """Test handling of invalid or malformed inputs."""
    # Test None/empty values
    assert prompt_staging_service.stage_and_execute_prompt(None, "subject", "prompt") is None
    assert prompt_staging_service.stage_and_execute_prompt("", "subject", "prompt") is None
    assert prompt_staging_service.stage_and_execute_prompt("agent", None, "prompt") is None
    assert prompt_staging_service.stage_and_execute_prompt("agent", "", "prompt") is None
    assert prompt_staging_service.stage_and_execute_prompt("agent", "subject", None) is None
    assert prompt_staging_service.stage_and_execute_prompt("agent", "subject", "") is None
    
    # Check error logs
    assert len(MOCKED_LOGS) >= 6  # At least one log per failed call
    for log in MOCKED_LOGS:
        assert log["event_type"] == "PROMPT_FAILED"
        assert "Invalid input" in log["details"]["error"]

def test_stage_and_execute_invalid_config():
    """Test handling of invalid llm_config structures."""
    agent_id = "Agent_BadConfig"
    subject = "Test Invalid Config"
    prompt = "Test prompt"
    
    # Test with non-dict config
    response = prompt_staging_service.stage_and_execute_prompt(
        agent_id, subject, prompt, llm_config="not a dict"
    )
    assert response is None
    assert MOCKED_LOGS[-1]["event_type"] == "PROMPT_FAILED"
    assert "Invalid config" in MOCKED_LOGS[-1]["details"]["error"]
    
    # Test with invalid config values
    response = prompt_staging_service.stage_and_execute_prompt(
        agent_id, subject, prompt, llm_config={"temperature": "not a number"}
    )
    assert response is None
    assert MOCKED_LOGS[-1]["event_type"] == "PROMPT_FAILED"
    assert "Invalid config" in MOCKED_LOGS[-1]["details"]["error"]

def test_stage_and_execute_logging_failure(monkeypatch):
    """Test behavior when logging fails."""
    def mock_log_event_failure(*args):
        raise Exception("Simulated logging failure")
    
    monkeypatch.setattr(prompt_staging_service, "log_event", mock_log_event_failure)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_LogFail", "Test Log Failure", "Test prompt"
    )
    
    # Should still get response despite logging failure
    assert response is not None
    assert response.startswith("Successful response for:")

def test_stage_and_execute_long_prompt():
    """Test handling of very long prompts (truncation in logs)."""
    agent_id = "Agent_LongPrompt"
    subject = "Test Long Prompt"
    # Create a prompt longer than the expected truncation length
    long_prompt = "x" * 1000
    
    response = prompt_staging_service.stage_and_execute_prompt(
        agent_id, subject, long_prompt
    )
    
    assert response is not None
    # Check truncation in logs
    assert len(MOCKED_LOGS[0]["details"]["prompt_context_snippet"]) < len(long_prompt)
    assert MOCKED_LOGS[0]["details"]["prompt_context_snippet"].endswith("...")

def test_stage_and_execute_retry_logic(monkeypatch):
    """Test the retry logic when LLM calls fail temporarily."""
    call_count = 0
    
    def mock_llm_with_retry(*args):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # Fail first two attempts
            return None
        return "Success on third try"
    
    monkeypatch.setattr(prompt_staging_service, "call_llm", mock_llm_with_retry)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_Retry", "Test Retry Logic", "Test prompt", 
        llm_config={"max_retries": 3, "retry_delay": 0.1}
    )
    
    assert response == "Success on third try"
    assert call_count == 3
    # Check retry logs
    retry_logs = [log for log in MOCKED_LOGS if log["event_type"] == "PROMPT_RETRY"]
    assert len(retry_logs) == 2
    for log in retry_logs:
        assert "attempt" in log["details"]
        assert "retry_delay" in log["details"]

def test_stage_and_execute_outbox_error(monkeypatch, tmp_path):
    """Test handling of outbox write failures."""
    error_dir = tmp_path / "outbox_errors"
    error_dir.mkdir()
    monkeypatch.setattr(prompt_staging_service, "OUTBOX_ERROR_DIR", str(error_dir))
    
    def mock_write_failure(*args):
        raise IOError("Failed to write to outbox")
    
    monkeypatch.setattr(prompt_staging_service, "_write_to_outbox", mock_write_failure)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_OutboxError", "Test Outbox Error", "Test prompt"
    )
    
    # Should still get response despite outbox error
    assert response is not None
    # Check error logs
    error_logs = [log for log in MOCKED_LOGS if "outbox" in log["details"].get("error", "").lower()]
    assert len(error_logs) > 0
    # Check error file creation
    error_files = list(error_dir.glob("*.error"))
    assert len(error_files) > 0

@pytest.mark.asyncio
async def test_stage_and_execute_concurrent():
    """Test concurrent execution of multiple prompts."""
    import asyncio
    
    async def execute_concurrent_prompts():
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                prompt_staging_service.stage_and_execute_prompt_async(
                    f"Agent_Concurrent_{i}",
                    f"Test Subject {i}",
                    f"Test prompt {i}"
                )
            )
            tasks.append(task)
        return await asyncio.gather(*tasks)
    
    responses = await execute_concurrent_prompts()
    
    assert len(responses) == 3
    assert all(response is not None for response in responses)
    # Check that logs maintain correct order and association
    concurrent_logs = [log for log in MOCKED_LOGS if "Agent_Concurrent" in log["details"]["agent_source"]]
    assert len(concurrent_logs) == 6  # 2 logs per prompt (staged + completed)
    
    # Verify log pairs maintain correct agent association
    for i in range(3):
        agent_logs = [log for log in concurrent_logs if f"Agent_Concurrent_{i}" in log["details"]["agent_source"]]
        assert len(agent_logs) == 2
        assert agent_logs[0]["event_type"] == "PROMPT_STAGED"
        assert agent_logs[1]["event_type"] == "PROMPT_COMPLETED"

def test_stage_and_execute_memory_pressure():
    """Test handling of large responses under memory pressure."""
    import gc
    
    # Create a large prompt that would stress memory
    large_prompt = "x" * (10 * 1024 * 1024)  # 10MB string
    
    # Force garbage collection before test
    gc.collect()
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_MemoryTest",
        "Test Memory Pressure",
        large_prompt
    )
    
    assert response is not None
    # Verify logs show memory management
    memory_logs = [log for log in MOCKED_LOGS if "memory" in str(log["details"]).lower()]
    assert len(memory_logs) > 0
    
    # Force cleanup
    del large_prompt
    gc.collect()

def test_stage_and_execute_transaction_rollback(monkeypatch, tmp_path):
    """Test transaction rollback when staging fails mid-operation."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    monkeypatch.setattr(prompt_staging_service, "STAGING_DIR", str(staging_dir))
    
    def mock_stage_failure(*args, **kwargs):
        # Create some temp files first
        (staging_dir / "temp1.json").write_text("test")
        (staging_dir / "temp2.json").write_text("test")
        raise Exception("Simulated staging failure")
    
    monkeypatch.setattr(prompt_staging_service, "_stage_prompt", mock_stage_failure)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_Transaction", "Test Transaction", "Test prompt"
    )
    
    assert response is None
    # Verify cleanup occurred
    assert len(list(staging_dir.glob("*.json"))) == 0
    # Check rollback logs
    rollback_logs = [log for log in MOCKED_LOGS if "rollback" in str(log["details"]).lower()]
    assert len(rollback_logs) > 0

def test_stage_and_execute_cleanup_on_success(monkeypatch, tmp_path):
    """Test cleanup of staging files after successful execution."""
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    monkeypatch.setattr(prompt_staging_service, "STAGING_DIR", str(staging_dir))
    
    # Track cleanup calls
    cleanup_called = False
    def mock_cleanup(*args):
        nonlocal cleanup_called
        cleanup_called = True
    
    monkeypatch.setattr(prompt_staging_service, "_cleanup_staging_files", mock_cleanup)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_Cleanup", "Test Cleanup", "Test prompt"
    )
    
    assert response is not None
    assert cleanup_called
    # Verify cleanup logs
    cleanup_logs = [log for log in MOCKED_LOGS if "cleanup" in str(log["details"]).lower()]
    assert len(cleanup_logs) > 0

def test_stage_and_execute_rate_limiting():
    """Test rate limiting behavior."""
    import time
    start_time = time.time()
    
    # Execute multiple prompts in quick succession
    responses = []
    for i in range(3):
        response = prompt_staging_service.stage_and_execute_prompt(
            f"Agent_RateLimit_{i}",
            f"Test Rate Limit {i}",
            "Test prompt"
        )
        responses.append(response)
    
    duration = time.time() - start_time
    assert all(response is not None for response in responses)
    
    # Check rate limit logs
    rate_logs = [log for log in MOCKED_LOGS if "rate" in str(log["details"]).lower()]
    assert len(rate_logs) > 0
    
    # Verify minimum delay between calls
    assert duration >= prompt_staging_service.MIN_DELAY_BETWEEN_CALLS * 2

def test_stage_and_execute_partial_failure_recovery():
    """Test recovery from partial failures during execution."""
    partial_results = []
    
    def mock_partial_success(*args, **kwargs):
        if len(partial_results) < 2:
            partial_results.append("Partial result")
            raise Exception("Simulated partial failure")
        return "Final success"
    
    with pytest.raises(Exception):
        prompt_staging_service.stage_and_execute_prompt(
            "Agent_PartialFailure",
            "Test Partial Failure",
            "Test prompt",
            recovery_handler=mock_partial_success
        )
    
    # Verify partial results were saved
    assert len(partial_results) == 2
    # Check recovery logs
    recovery_logs = [log for log in MOCKED_LOGS if "recovery" in str(log["details"]).lower()]
    assert len(recovery_logs) > 0

def test_stage_and_execute_prompt_validation():
    """Test prompt content validation and sanitization."""
    # Test with various special characters and potential SQL injection
    problematic_prompts = [
        "'; DROP TABLE users; --",
        "<script>alert('xss')</script>",
        "{{malicious_template}}",
        "\x00\x1F\x7F",  # Control characters
        "a" * (prompt_staging_service.MAX_PROMPT_LENGTH + 1)  # Too long
    ]
    
    for prompt in problematic_prompts:
        response = prompt_staging_service.stage_and_execute_prompt(
            "Agent_Validation",
            "Test Validation",
            prompt
        )
        # Should either sanitize or reject
        if response is not None:
            assert "'" not in response
            assert "<script>" not in response
            assert "{{" not in response
            assert "\x00" not in response
        else:
            validation_logs = [log for log in MOCKED_LOGS if "validation" in str(log["details"]).lower()]
            assert len(validation_logs) > 0

def test_stage_and_execute_file_permissions(monkeypatch, tmp_path):
    """Test handling of file permission issues."""
    import stat
    
    # Create staging and outbox directories with restricted permissions
    staging_dir = tmp_path / "staging_restricted"
    outbox_dir = tmp_path / "outbox_restricted"
    staging_dir.mkdir()
    outbox_dir.mkdir()
    
    # Remove write permissions
    staging_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
    outbox_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
    
    monkeypatch.setattr(prompt_staging_service, "STAGING_DIR", str(staging_dir))
    monkeypatch.setattr(prompt_staging_service, "OUTBOX_DIR", str(outbox_dir))
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_Permissions", "Test Permissions", "Test prompt"
    )
    
    assert response is None
    # Check permission error logs
    perm_logs = [log for log in MOCKED_LOGS if "permission" in str(log["details"].get("error", "")).lower()]
    assert len(perm_logs) > 0
    
    # Restore permissions for cleanup
    staging_dir.chmod(stat.S_IRWXU)
    outbox_dir.chmod(stat.S_IRWXU)

def test_stage_and_execute_disk_full(monkeypatch):
    """Test handling of disk full scenarios."""
    def mock_disk_full_write(*args, **kwargs):
        raise OSError(28, "No space left on device")  # errno 28 is disk full
    
    monkeypatch.setattr(prompt_staging_service, "_write_to_staging", mock_disk_full_write)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_DiskFull", "Test Disk Full", "Test prompt"
    )
    
    assert response is None
    # Check disk full error logs
    disk_logs = [log for log in MOCKED_LOGS if "disk" in str(log["details"].get("error", "")).lower()]
    assert len(disk_logs) > 0

@pytest.mark.integration
def test_stage_and_execute_integration_llm(monkeypatch):
    """Integration test with mocked LLM service."""
    from unittest.mock import MagicMock
    
    # Mock the LLM service with more realistic behavior
    llm_service = MagicMock()
    llm_service.generate.side_effect = [
        {"text": "First attempt failed", "error": "Rate limited"},
        {"text": "Second attempt success", "error": None}
    ]
    
    monkeypatch.setattr(prompt_staging_service, "llm_service", llm_service)
    
    response = prompt_staging_service.stage_and_execute_prompt(
        "Agent_Integration", 
        "Test Integration",
        "Test prompt",
        llm_config={"max_retries": 2}
    )
    
    assert response == "Second attempt success"
    assert llm_service.generate.call_count == 2
    # Check integration logs
    integration_logs = [log for log in MOCKED_LOGS if log["event_type"] in ["PROMPT_RETRY", "PROMPT_COMPLETED"]]
    assert len(integration_logs) == 2

def test_stage_and_execute_malformed_response():
    """Test handling of malformed LLM responses."""
    def mock_malformed_response(*args, **kwargs):
        return {"invalid": "response structure"}
    
    with pytest.raises(ValueError) as exc_info:
        prompt_staging_service.stage_and_execute_prompt(
            "Agent_Malformed",
            "Test Malformed",
            "Test prompt",
            response_handler=mock_malformed_response
        )
    
    assert "Invalid response format" in str(exc_info.value)
    # Check error logs
    error_logs = [log for log in MOCKED_LOGS if "format" in str(log["details"].get("error", "")).lower()]
    assert len(error_logs) > 0

def test_stage_and_execute_unicode_handling():
    """Test handling of Unicode and special characters in prompts and responses."""
    special_prompts = [
        "🧪 Test emoji",
        "Mixed ASCII and 漢字",
        "Right-to-left تجربة",
        "Combining d̶i̶a̶c̶r̶i̶t̶i̶c̶s̶",
        "Zero-width\u200Bspaces"
    ]
    
    for prompt in special_prompts:
        response = prompt_staging_service.stage_and_execute_prompt(
            "Agent_Unicode",
            f"Test Unicode: {prompt[:10]}",
            prompt
        )
        
        assert response is not None
        # Verify Unicode is preserved in logs
        unicode_logs = [log for log in MOCKED_LOGS if prompt in str(log["details"])]
        assert len(unicode_logs) > 0

# Log test coverage event
prompt_staging_service.log_event(
    "TEST_ADDED",
    "CoverageAgent",
    {
        "test_file": "test_prompt_staging_service.py",
        "new_tests": [
            "test_stage_and_execute_transaction_rollback",
            "test_stage_and_execute_cleanup_on_success",
            "test_stage_and_execute_rate_limiting",
            "test_stage_and_execute_partial_failure_recovery",
            "test_stage_and_execute_prompt_validation",
            "test_stage_and_execute_file_permissions",
            "test_stage_and_execute_disk_full",
            "test_stage_and_execute_integration_llm",
            "test_stage_and_execute_malformed_response",
            "test_stage_and_execute_unicode_handling"
        ],
        "coverage_targets": ["transaction handling", "cleanup", "rate limiting", 
                           "partial failure recovery", "input validation",
                           "file system permissions", "disk space handling",
                           "llm integration", "response validation", "unicode support"]
    }
)
 