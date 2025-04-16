import unittest
from unittest.mock import patch, MagicMock
import json
import os
from dreamforge.core.governance_memory_engine import GovernanceMemoryEngine, log_event

class TestGovernanceMemoryEngine(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.engine = GovernanceMemoryEngine()
        self.test_event = {
            "event_type": "TEST_EVENT",
            "agent_id": "test_agent",
            "data": {"test_key": "test_value"}
        }
        log_event("TEST_ADDED", "TestGovernanceMemoryEngine", {"test_suite": "GovernanceMemoryEngine"})

    def tearDown(self):
        """Clean up test artifacts."""
        if hasattr(self.engine, '_memory_store'):
            self.engine._memory_store.clear()

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_store_event_success(self, mock_log_event):
        """Test successful event storage."""
        result = self.engine.store_event(
            self.test_event["event_type"],
            self.test_event["agent_id"],
            self.test_event["data"]
        )
        self.assertTrue(result)
        mock_log_event.assert_called_with(
            "EVENT_STORED",
            "governance_engine",
            {"event_type": "TEST_EVENT", "agent_id": "test_agent"}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_store_event_success"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_store_event_validation(self, mock_log_event):
        """Test event validation during storage."""
        invalid_cases = [
            (None, "test_agent", {}, "Invalid event type"),
            ("TEST_EVENT", None, {}, "Invalid agent ID"),
            ("TEST_EVENT", "test_agent", None, "Invalid event data")
        ]
        
        for event_type, agent_id, data, expected_error in invalid_cases:
            result = self.engine.store_event(event_type, agent_id, data)
            self.assertFalse(result)
            mock_log_event.assert_called_with(
                "EVENT_VALIDATION_FAILED",
                "governance_engine",
                {"error": expected_error}
            )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_store_event_validation"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_query_events_by_type(self, mock_log_event):
        """Test querying events by type."""
        # Store multiple events
        self.engine.store_event("TYPE_A", "agent1", {"data": "a"})
        self.engine.store_event("TYPE_B", "agent1", {"data": "b"})
        self.engine.store_event("TYPE_A", "agent2", {"data": "c"})
        
        results = self.engine.query_events(event_type="TYPE_A")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(event["event_type"] == "TYPE_A" for event in results))
        mock_log_event.assert_called_with(
            "EVENTS_QUERIED",
            "governance_engine",
            {"query_type": "event_type", "count": 2}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_query_events_by_type"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_query_events_by_agent(self, mock_log_event):
        """Test querying events by agent ID."""
        # Store multiple events
        self.engine.store_event("TYPE_A", "agent1", {"data": "a"})
        self.engine.store_event("TYPE_B", "agent1", {"data": "b"})
        self.engine.store_event("TYPE_A", "agent2", {"data": "c"})
        
        results = self.engine.query_events(agent_id="agent1")
        self.assertEqual(len(results), 2)
        self.assertTrue(all(event["agent_id"] == "agent1" for event in results))
        mock_log_event.assert_called_with(
            "EVENTS_QUERIED",
            "governance_engine",
            {"query_type": "agent_id", "count": 2}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_query_events_by_agent"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_query_events_with_time_range(self, mock_log_event):
        """Test querying events within a time range."""
        current_time = 1000  # Mock timestamp
        
        with patch('time.time', return_value=current_time):
            self.engine.store_event("TEST_EVENT", "agent1", {"data": "a"})
        
        with patch('time.time', return_value=current_time + 100):
            self.engine.store_event("TEST_EVENT", "agent1", {"data": "b"})
        
        results = self.engine.query_events(
            start_time=current_time - 50,
            end_time=current_time + 50
        )
        self.assertEqual(len(results), 1)
        mock_log_event.assert_called_with(
            "EVENTS_QUERIED",
            "governance_engine",
            {"query_type": "time_range", "count": 1}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_query_events_with_time_range"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_event_persistence(self, mock_log_event):
        """Test event persistence and recovery."""
        test_events = [
            ("TYPE_A", "agent1", {"data": "a"}),
            ("TYPE_B", "agent1", {"data": "b"})
        ]
        
        # Store events
        for event_type, agent_id, data in test_events:
            self.engine.store_event(event_type, agent_id, data)
        
        # Test persistence
        with patch('builtins.open', mock_open()) as mock_file:
            self.engine.persist_events()
            mock_file.assert_called()
            mock_log_event.assert_called_with(
                "EVENTS_PERSISTED",
                "governance_engine",
                {"count": 2}
            )
        
        # Test recovery
        with patch('builtins.open', mock_open(read_data=json.dumps(test_events))):
            recovered = self.engine.recover_events()
            self.assertTrue(recovered)
            mock_log_event.assert_called_with(
                "EVENTS_RECOVERED",
                "governance_engine",
                {"count": 2}
            )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_event_persistence"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_event_aggregation(self, mock_log_event):
        """Test event aggregation functionality."""
        # Store test events
        for i in range(5):
            self.engine.store_event(
                "METRIC_EVENT",
                "agent1",
                {"value": i}
            )
        
        aggregation = self.engine.aggregate_events(
            event_type="METRIC_EVENT",
            aggregation_key="value",
            operation="sum"
        )
        
        self.assertEqual(aggregation["sum"], 10)
        mock_log_event.assert_called_with(
            "EVENTS_AGGREGATED",
            "governance_engine",
            {
                "event_type": "METRIC_EVENT",
                "operation": "sum",
                "result": 10
            }
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_event_aggregation"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_event_cleanup(self, mock_log_event):
        """Test event cleanup functionality."""
        current_time = 1000  # Mock timestamp
        
        # Store old and new events
        with patch('time.time', return_value=current_time - 1000):
            self.engine.store_event("OLD_EVENT", "agent1", {"data": "old"})
        
        with patch('time.time', return_value=current_time):
            self.engine.store_event("NEW_EVENT", "agent1", {"data": "new"})
        
        cleaned = self.engine.cleanup_events(max_age=500)
        self.assertTrue(cleaned)
        
        # Verify only new event remains
        events = self.engine.query_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "NEW_EVENT")
        
        mock_log_event.assert_called_with(
            "EVENTS_CLEANED",
            "governance_engine",
            {"removed_count": 1}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_event_cleanup"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_concurrent_event_storage(self, mock_log_event):
        """Test concurrent event storage with thread safety."""
        from threading import Thread
        from queue import Queue
        
        results_queue = Queue()
        def store_events():
            try:
                for i in range(10):
                    result = self.engine.store_event(
                        f"CONCURRENT_EVENT_{i}",
                        "concurrent_agent",
                        {"thread_data": i}
                    )
                    results_queue.put(result)
            except Exception as e:
                results_queue.put(e)
        
        threads = [Thread(target=store_events) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        self.assertEqual(len(results), 30)  # 3 threads * 10 events each
        self.assertTrue(all(results))  # All stores successful
        
        stored_events = self.engine.query_events(agent_id="concurrent_agent")
        self.assertEqual(len(stored_events), 30)
        mock_log_event.assert_any_call(
            "CONCURRENT_EVENTS_STORED",
            "governance_engine",
            {"thread_count": 3, "events_per_thread": 10}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_concurrent_event_storage"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_query_with_complex_filters(self, mock_log_event):
        """Test querying events with complex filtering conditions."""
        # Store events with various attributes
        test_events = [
            ("TYPE_A", "agent1", {"priority": "high", "status": "active"}),
            ("TYPE_A", "agent1", {"priority": "low", "status": "inactive"}),
            ("TYPE_B", "agent2", {"priority": "high", "status": "active"}),
            ("TYPE_B", "agent2", {"priority": "medium", "status": "pending"})
        ]
        
        for event_type, agent_id, data in test_events:
            self.engine.store_event(event_type, agent_id, data)
        
        # Test complex filtering
        filters = {
            "priority": ["high", "medium"],
            "status": "active"
        }
        
        results = self.engine.query_events(
            event_type="TYPE_B",
            filters=filters
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["data"]["priority"], "high")
        self.assertEqual(results[0]["data"]["status"], "active")
        
        mock_log_event.assert_called_with(
            "EVENTS_COMPLEX_QUERY",
            "governance_engine",
            {"filters": filters, "matched_count": 1}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_query_with_complex_filters"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_event_persistence_error_handling(self, mock_log_event):
        """Test error handling during event persistence operations."""
        test_events = [
            ("TYPE_A", "agent1", {"data": "a"}),
            ("TYPE_B", "agent1", {"data": "b"})
        ]
        
        for event_type, agent_id, data in test_events:
            self.engine.store_event(event_type, agent_id, data)
        
        # Test persistence with file write error
        with patch('builtins.open', side_effect=IOError("Mock IO Error")):
            result = self.engine.persist_events()
            self.assertFalse(result)
            mock_log_event.assert_called_with(
                "EVENT_PERSISTENCE_ERROR",
                "governance_engine",
                {"error": "Mock IO Error"}
            )
        
        # Test recovery with corrupted data
        with patch('builtins.open', mock_open(read_data="corrupted json data")):
            result = self.engine.recover_events()
            self.assertFalse(result)
            mock_log_event.assert_called_with(
                "EVENT_RECOVERY_ERROR",
                "governance_engine",
                {"error": "JSON decode error"}
            )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_event_persistence_error_handling"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_event_aggregation_advanced(self, mock_log_event):
        """Test advanced event aggregation features."""
        # Store test events with complex data
        test_events = [
            ("METRIC", "agent1", {"cpu": 80, "memory": 1024, "status": "warning"}),
            ("METRIC", "agent1", {"cpu": 90, "memory": 2048, "status": "critical"}),
            ("METRIC", "agent2", {"cpu": 30, "memory": 512, "status": "normal"}),
            ("METRIC", "agent2", {"cpu": 40, "memory": 768, "status": "normal"})
        ]
        
        for event_type, agent_id, data in test_events:
            self.engine.store_event(event_type, agent_id, data)
        
        # Test multiple aggregations
        aggregations = self.engine.aggregate_events(
            event_type="METRIC",
            agent_id="agent1",
            aggregations=[
                {"key": "cpu", "op": "avg"},
                {"key": "memory", "op": "max"},
                {"key": "status", "op": "count_distinct"}
            ]
        )
        
        self.assertEqual(aggregations["cpu_avg"], 85)
        self.assertEqual(aggregations["memory_max"], 2048)
        self.assertEqual(aggregations["status_distinct"], 2)
        
        mock_log_event.assert_called_with(
            "EVENTS_ADVANCED_AGGREGATION",
            "governance_engine",
            {"aggregations": aggregations}
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_event_aggregation_advanced"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_memory_management(self, mock_log_event):
        """Test memory management and optimization features."""
        # Fill memory store with events
        for i in range(1000):
            self.engine.store_event(
                "MEMORY_TEST",
                f"agent{i % 10}",
                {"data": "x" * 1000}  # 1KB of data per event
            )
        
        # Test memory optimization
        initial_size = self.engine.get_memory_size()
        optimized = self.engine.optimize_memory(max_size_mb=1)
        final_size = self.engine.get_memory_size()
        
        self.assertTrue(optimized)
        self.assertLess(final_size, initial_size)
        
        mock_log_event.assert_called_with(
            "MEMORY_OPTIMIZED",
            "governance_engine",
            {
                "initial_size_mb": initial_size / (1024 * 1024),
                "final_size_mb": final_size / (1024 * 1024)
            }
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_memory_management"})

    @patch('dreamforge.core.governance_memory_engine.log_event')
    def test_event_batching(self, mock_log_event):
        """Test batch event operations."""
        # Prepare batch of events
        batch_events = [
            {
                "event_type": f"BATCH_EVENT_{i}",
                "agent_id": f"batch_agent_{i % 3}",
                "data": {"batch_id": i}
            }
            for i in range(50)
        ]
        
        # Test batch storage
        result = self.engine.store_events_batch(batch_events)
        self.assertTrue(result["success"])
        self.assertEqual(result["stored_count"], 50)
        
        # Test batch query
        batch_results = self.engine.query_events_batch([
            {"agent_id": "batch_agent_0"},
            {"agent_id": "batch_agent_1"},
            {"event_type": "BATCH_EVENT_1"}
        ])
        
        self.assertEqual(len(batch_results), 3)
        self.assertTrue(all(len(result) > 0 for result in batch_results))
        
        mock_log_event.assert_called_with(
            "BATCH_OPERATIONS_COMPLETED",
            "governance_engine",
            {
                "stored_count": 50,
                "query_count": 3
            }
        )
        log_event("TEST_PASSED", "TestGovernanceMemoryEngine", {"test": "test_event_batching"})

if __name__ == "__main__":
    unittest.main() 