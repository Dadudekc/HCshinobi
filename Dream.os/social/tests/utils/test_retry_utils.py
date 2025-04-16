import pytest
import time
from unittest.mock import Mock, patch
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from utils.retry_utils import retry_selenium_action

class TestRetryUtils:
    def test_successful_execution_no_retry(self):
        """Test successful execution without any retries needed."""
        mock_func = Mock(return_value="success")
        decorated_func = retry_selenium_action()(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_successful_execution_no_retry"})

    def test_retry_on_timeout_exception(self):
        """Test retry behavior on TimeoutException."""
        mock_func = Mock(side_effect=[
            TimeoutException("Timeout"),
            "success"
        ])
        decorated_func = retry_selenium_action(max_attempts=2)(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_retry_on_timeout_exception"})

    def test_retry_on_stale_element(self):
        """Test retry behavior on StaleElementReferenceException."""
        mock_func = Mock(side_effect=[
            StaleElementReferenceException("Stale"),
            "success"
        ])
        decorated_func = retry_selenium_action(max_attempts=2)(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_retry_on_stale_element"})

    def test_retry_on_element_intercepted(self):
        """Test retry behavior on ElementClickInterceptedException."""
        mock_func = Mock(side_effect=[
            ElementClickInterceptedException("Intercepted"),
            "success"
        ])
        decorated_func = retry_selenium_action(max_attempts=2)(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_retry_on_element_intercepted"})

    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        mock_func = Mock(side_effect=TimeoutException("Timeout"))
        decorated_func = retry_selenium_action(max_attempts=3)(mock_func)
        
        with pytest.raises(TimeoutException):
            decorated_func()
        
        assert mock_func.call_count == 3
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_max_retries_exceeded"})

    def test_custom_retry_parameters(self):
        """Test decorator with custom max_attempts and delay_seconds."""
        mock_func = Mock(side_effect=[
            TimeoutException("Timeout"),
            TimeoutException("Timeout"),
            "success"
        ])
        decorated_func = retry_selenium_action(max_attempts=4, delay_seconds=1)(mock_func)
        
        start_time = time.time()
        result = decorated_func()
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        assert mock_func.call_count == 3
        # Should have waited at least 1 + 2 seconds (exponential backoff)
        assert elapsed_time >= 3
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_custom_retry_parameters"})

    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        mock_func = Mock(side_effect=[
            TimeoutException("Timeout"),
            TimeoutException("Timeout"),
            "success"
        ])
        decorated_func = retry_selenium_action(max_attempts=3, delay_seconds=1)(mock_func)
        
        with patch('time.sleep') as mock_sleep:
            decorated_func()
            
            # First retry: 1 second, Second retry: 2 seconds
            mock_sleep.assert_any_call(1)  # First retry
            mock_sleep.assert_any_call(2)  # Second retry
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_exponential_backoff"})

    def test_preserve_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @retry_selenium_action()
        def test_func():
            """Test function docstring."""
            pass
        
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_preserve_function_metadata"})

    def test_mixed_exceptions(self):
        """Test handling of different exceptions in sequence."""
        mock_func = Mock(side_effect=[
            TimeoutException("Timeout"),
            StaleElementReferenceException("Stale"),
            ElementClickInterceptedException("Intercepted"),
            "success"
        ])
        decorated_func = retry_selenium_action(max_attempts=4)(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 4
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_mixed_exceptions"})

    def test_args_kwargs_passing(self):
        """Test proper passing of arguments to wrapped function."""
        mock_func = Mock(return_value="success")
        decorated_func = retry_selenium_action()(mock_func)
        
        result = decorated_func(1, 2, key="value")
        
        mock_func.assert_called_once_with(1, 2, key="value")
        assert result == "success"
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_args_kwargs_passing"})

    @pytest.mark.integration
    def test_integration_with_selenium(self):
        """Integration test with actual Selenium-like operations."""
        class MockWebElement:
            def __init__(self, fail_times):
                self.fail_times = fail_times
                self.calls = 0
            
            def click(self):
                self.calls += 1
                if self.calls <= self.fail_times:
                    raise StaleElementReferenceException("Stale")
                return True
        
        element = MockWebElement(fail_times=2)
        
        @retry_selenium_action(max_attempts=3)
        def click_element(elem):
            return elem.click()
        
        result = click_element(element)
        
        assert result is True
        assert element.calls == 3
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_integration_with_selenium"})

if __name__ == '__main__':
    pytest.main([__file__]) 