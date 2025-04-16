import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dreamforge.core.feedback.consumer import FeedbackConsumerService
from dreamforge.core.memory.memory_manager import MemoryManager

@pytest.fixture
def memory_manager():
    return Mock(spec=MemoryManager)

@pytest.fixture
def feedback_consumer(memory_manager):
    return FeedbackConsumerService(memory_manager=memory_manager)

@pytest.mark.asyncio
async def test_feedback_consumer_initialization(feedback_consumer, memory_manager):
    """Test FeedbackConsumer initializes correctly"""
    assert feedback_consumer is not None
    assert feedback_consumer.memory_manager == memory_manager
    assert hasattr(feedback_consumer, 'process_feedback')
    assert hasattr(feedback_consumer, 'start_consumer')

@pytest.mark.asyncio
async def test_process_feedback(feedback_consumer):
    """Test feedback processing functionality"""
    test_feedback = {
        "type": "prompt_refinement",
        "content": "Test feedback",
        "metrics": {"accuracy": 0.95}
    }
    
    with patch.object(feedback_consumer, '_store_feedback') as mock_store:
        await feedback_consumer.process_feedback(test_feedback)
        mock_store.assert_called_once_with(test_feedback)

@pytest.mark.asyncio
async def test_invalid_feedback_handling(feedback_consumer):
    """Test handling of invalid feedback"""
    invalid_feedback = {"type": "invalid"}
    
    with pytest.raises(ValueError):
        await feedback_consumer.process_feedback(invalid_feedback)

@pytest.mark.asyncio
async def test_metrics_logging(feedback_consumer):
    """Test metrics are properly logged"""
    test_feedback = {
        "type": "prompt_refinement",
        "metrics": {
            "accuracy": 0.95,
            "latency": 100
        }
    }
    
    with patch('prometheus_client.Gauge') as mock_gauge:
        await feedback_consumer.process_feedback(test_feedback)
        assert mock_gauge.labels.call_count == 2  # One for each metric

@pytest.mark.asyncio
async def test_memory_storage(feedback_consumer, memory_manager):
    """Test feedback storage in memory manager"""
    test_feedback = {
        "type": "prompt_refinement",
        "content": "Test feedback"
    }
    
    await feedback_consumer.process_feedback(test_feedback)
    memory_manager.store_feedback.assert_called_once_with(test_feedback)

@pytest.mark.asyncio
async def test_consumer_daemon_mode(feedback_consumer):
    """Test consumer running in daemon mode"""
    mock_queue = asyncio.Queue()
    await mock_queue.put({"type": "prompt_refinement", "content": "test"})
    
    with patch.object(feedback_consumer, 'process_feedback') as mock_process:
        # Start consumer
        consumer_task = asyncio.create_task(
            feedback_consumer.start_consumer(mock_queue)
        )
        await asyncio.sleep(0.1)  # Give consumer time to process
        
        # Verify processing
        mock_process.assert_called_once()
        
        # Cleanup
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_refined_prompt_generation(feedback_consumer):
    """Test generation of refined prompts based on feedback"""
    feedback_history = [
        {"type": "prompt_refinement", "content": "Improve clarity"},
        {"type": "prompt_refinement", "content": "Add more context"}
    ]
    
    with patch.object(feedback_consumer.memory_manager, 'get_feedback_history') as mock_history:
        mock_history.return_value = feedback_history
        refined_prompt = await feedback_consumer._generate_refined_prompt("original prompt")
        assert refined_prompt != "original prompt"
        assert isinstance(refined_prompt, str)

@pytest.mark.asyncio
async def test_error_recovery(feedback_consumer):
    """Test error recovery and retry mechanism"""
    test_feedback = {"type": "prompt_refinement", "content": "test"}
    
    # Simulate temporary failure then success
    mock_store = AsyncMock(side_effect=[Exception("Temporary failure"), None])
    with patch.object(feedback_consumer, '_store_feedback', mock_store):
        await feedback_consumer.process_feedback(test_feedback)
        assert mock_store.call_count == 2  # One failure + one retry 