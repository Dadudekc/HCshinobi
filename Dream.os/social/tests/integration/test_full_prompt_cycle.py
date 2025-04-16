import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, call, ANY

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tests/integration
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) 
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Import necessary modules (assuming they exist and are importable)
try:
    from core import prompt_staging_service
    from tools import chat_cursor_bridge
    from core.memory import governance_memory_engine # For mocking log_event
    from core.memory import supervisor_memory # For mocking load_state
    _core_imports_ok = True
except ImportError as e:
    print(f"Error importing core modules for integration test: {e}")
    _core_imports_ok = False

@unittest.skipUnless(_core_imports_ok, "Core dependencies not met, skipping integration test")
class TestFullPromptCycleSimulation(unittest.TestCase):

    @patch('core.prompt_staging_service.log_event') 
    @patch('core.prompt_staging_service.load_state')
    @patch('core.prompt_staging_service._load_project_analysis')
    @patch('core.prompt_staging_service.template_engine')
    @patch('tools.chat_cursor_bridge.write_to_cursor_input')
    @patch('tools.chat_cursor_bridge.read_from_cursor_output')
    def test_simulated_prompt_cycle(self, 
                                  mock_read_bridge, 
                                  mock_write_bridge, 
                                  mock_template_engine, 
                                  mock_load_analysis, 
                                  mock_load_state, 
                                  mock_log_event):
        """Simulate the full prompt cycle from rendering to response fetching."""
        # --- Arrange --- 
        
        # 1. Mock Governance/State Data
        test_state = {"active_goals": ["Simulate cycle"], "current_focus": {"purpose": "testing cycle"}}
        mock_load_state.return_value = test_state
        test_analysis = {"summary": {"total_files": 10}}
        mock_load_analysis.return_value = test_analysis

        # 2. Mock Template Rendering
        test_template = "integration_test_prompt.j2"
        test_context = {"input_data": "some value"}
        rendered_output = "Rendered prompt with state and analysis."
        mock_template_engine.render.return_value = rendered_output
        mock_template_engine.jinja_env = True # Assume engine is available

        # 3. Mock Bridge Write
        mock_write_bridge.return_value = True # Simulate successful write

        # 4. Mock Bridge Read (Simulate response arriving)
        simulated_response = {"status": "success", "output": "LLM response data"}
        mock_read_bridge.return_value = simulated_response
        
        # --- Act --- 
        
        # Step 1 & 2: Render the prompt (implicitly loads state/analysis)
        final_rendered_prompt = prompt_staging_service.render_prompt(test_template, test_context)
        
        # Step 3: Stage the prompt (write to bridge)
        staged_ok = False
        if final_rendered_prompt:
            staged_ok = chat_cursor_bridge.write_to_cursor_input(final_rendered_prompt)
        
        # Step 4 & 5: Fetch the response (read from bridge)
        fetched_response = None
        if staged_ok: # Only try to read if staging worked
            # In a real scenario, there might be a wait here
            fetched_response = chat_cursor_bridge.read_from_cursor_output()
            
        # Step 6: Log results (Implicitly done by the services, checked in asserts)
        
        # --- Assert --- 
        
        # Verify render call
        mock_load_state.assert_called_once()
        mock_load_analysis.assert_called_once()
        expected_render_context = {
            **test_context,
            "supervisor_state": test_state,
            "project_scan": test_analysis
        }
        mock_template_engine.render.assert_called_once_with(test_template, expected_render_context)
        self.assertEqual(final_rendered_prompt, rendered_output)
        
        # Verify bridge write call
        self.assertTrue(staged_ok)
        mock_write_bridge.assert_called_once_with(rendered_output)
        
        # Verify bridge read call
        mock_read_bridge.assert_called_once()
        self.assertEqual(fetched_response, simulated_response)
        
        # Verify logging calls (using ANY for context details where needed)
        mock_log_event.assert_has_calls([
            call('PROMPT_RENDERED', ANY), # From render_prompt
            # call('PROMPT_STAGED', ANY), # Logged by prompt_staging_service.stage_prompt_for_cursor, not directly called here
            call('RESPONSE_FETCHED', ANY) # From fetch_cursor_response called by bridge
        ], any_order=True) # Order might vary slightly depending on internal logic


if __name__ == '__main__':
    # Note: Running this directly requires careful setup or mocking of dependencies
    unittest.main() 