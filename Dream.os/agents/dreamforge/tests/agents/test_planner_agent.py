"""Tests for PlannerAgent."""
import pytest
from dreamforge.agents.planner_agent import PlannerAgent, AGENT_ID
from dreamforge.tests.agents.test_utils import (
    SAMPLE_PLAN,
    validate_plan,
    validate_plan_refinement
)
from dreamforge.tests.core.utils.llm_test_utils import (
    LLMTestResponse,
    patch_llm_chain
)

@pytest.fixture
def planner_agent():
    """Create a planner agent instance."""
    return PlannerAgent()

# --- plan_from_goal Tests ---

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_success(llm_chain, planner_agent):
    """Test successful plan generation from a goal."""
    llm_chain.setup_response(LLMTestResponse.with_json(SAMPLE_PLAN))
    goal = "Test Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    validate_plan(plan, SAMPLE_PLAN)
    llm_chain.verify_call(
        "agents/prompts/planner/generate_plan.j2",
        {"goal": goal},
        AGENT_ID,
        "generate_plan"
    )

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_render_fails(llm_chain, planner_agent):
    """Test plan_from_goal when template rendering fails."""
    llm_chain.setup_response(
        LLMTestResponse.with_error(),
        render_result=None
    )
    goal = "Render Fail Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    assert plan == []
    llm_chain.verify_not_called()

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_llm_fails(llm_chain, planner_agent):
    """Test plan_from_goal when LLM call fails."""
    llm_chain.setup_response(
        LLMTestResponse.with_error(),
        should_fail=True
    )
    goal = "LLM Fail Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    assert plan == []
    llm_chain.execute.assert_called_once()

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_parsing_fails_no_json(llm_chain, planner_agent):
    """Test plan_from_goal when LLM response has no JSON."""
    llm_chain.setup_response(LLMTestResponse.with_error("no_content"))
    goal = "No JSON Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    assert plan == []

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_parsing_fails_bad_json(llm_chain, planner_agent):
    """Test plan_from_goal when LLM response has invalid JSON."""
    llm_chain.setup_response(LLMTestResponse.with_error("invalid_json"))
    goal = "Bad JSON Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    assert plan == []

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_parsing_fails_wrong_type(llm_chain, planner_agent):
    """Test plan_from_goal when LLM response JSON is not a list."""
    llm_chain.setup_response(LLMTestResponse.with_json({"not_a": "list"}))
    goal = "Wrong Type Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    assert plan == []

@patch_llm_chain("agents.planner_agent")
def test_plan_from_goal_parsing_fails_bad_item(llm_chain, planner_agent):
    """Test plan_from_goal when a plan item is invalid."""
    invalid_plan = [
        {"task_id": "T1", "description": "Valid"},
        {"task_id": "T2"}  # Missing description
    ]
    llm_chain.setup_response(LLMTestResponse.with_json(invalid_plan))
    goal = "Bad Item Goal"
    
    plan = planner_agent.plan_from_goal(goal)
    
    assert len(plan) == 1  # Should return only the valid items
    assert plan[0]['task_id'] == 'T1'

# --- refine_plan Tests ---

@patch_llm_chain("agents.planner_agent")
def test_refine_plan_success(llm_chain, planner_agent):
    """Test successful plan refinement."""
    original_plan = [SAMPLE_PLAN[0]]  # Use first task from sample plan
    refined_plan = [
        {
            'task_id': 'TASK-001',
            'description': 'Define project scope precisely',  # Changed
            'status': 'Pending',
            'dependencies': [],
            'estimated_time': '3h'  # Changed
        },
        {
            'task_id': 'TASK-002',  # Added
            'description': 'Create roadmap',
            'status': 'Pending',
            'dependencies': ['TASK-001'],
            'estimated_time': '4h'
        }
    ]
    llm_chain.setup_response(LLMTestResponse.with_json(refined_plan))
    instructions = "Make scope definition more precise, estimate 3h. Add task for roadmap creation dependent on scope."
    
    result = planner_agent.refine_plan(original_plan, instructions)
    
    expected_changes = {
        'TASK-001': {
            'description': 'Define project scope precisely',
            'estimated_time': '3h'
        },
        'TASK-002': {
            'description': 'Create roadmap',
            'dependencies': ['TASK-001'],
            'estimated_time': '4h'
        }
    }
    validate_plan_refinement(result, original_plan, expected_changes)
    llm_chain.verify_call(
        "agents/prompts/planner/refine_plan.j2",
        {"plan": original_plan, "instructions": instructions},
        AGENT_ID,
        "refine_plan"
    )

@patch_llm_chain("agents.planner_agent")
def test_refine_plan_render_fails(llm_chain, planner_agent):
    """Test refine_plan when template rendering fails."""
    llm_chain.setup_response(
        LLMTestResponse.with_error(),
        render_result=None
    )
    original_plan = [SAMPLE_PLAN[0]]
    instructions = "Test instructions"
    
    result = planner_agent.refine_plan(original_plan, instructions)
    
    assert result == original_plan
    llm_chain.verify_not_called()

@patch_llm_chain("agents.planner_agent")
def test_refine_plan_llm_fails(llm_chain, planner_agent):
    """Test refine_plan when LLM call fails."""
    llm_chain.setup_response(
        LLMTestResponse.with_error(),
        should_fail=True
    )
    original_plan = [SAMPLE_PLAN[0]]
    instructions = "Test instructions"
    
    result = planner_agent.refine_plan(original_plan, instructions)
    
    assert result == original_plan
    llm_chain.execute.assert_called_once()

@patch_llm_chain("agents.planner_agent")
def test_refine_plan_parsing_fails(llm_chain, planner_agent):
    """Test refine_plan when response parsing fails."""
    llm_chain.setup_response(LLMTestResponse.with_error("malformed"))
    original_plan = [SAMPLE_PLAN[0]]
    instructions = "Test instructions"
    
    result = planner_agent.refine_plan(original_plan, instructions)
    
    assert result == original_plan 