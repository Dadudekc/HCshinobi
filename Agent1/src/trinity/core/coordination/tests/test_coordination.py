import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from agent_manager.agent_registry import AgentRegistry
from task_orchestrator.task_queue import TaskPriority, TaskStatus
from messaging.message_queue import MessagePriority
from monitoring.health_monitor import HealthStatus

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agent_coordination"}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "agents" in data
    assert "tasks" in data
    assert "alerts" in data

def test_agent_registration():
    # Register an agent
    response = client.post("/agents/register", json={
        "agent_id": "test_agent",
        "capabilities": ["testing", "development"],
        "resources": ["cpu", "memory"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "test_agent"
    assert "testing" in data["capabilities"]
    assert "cpu" in data["resources"]

    # Try to register the same agent again
    response = client.post("/agents/register", json={
        "agent_id": "test_agent",
        "capabilities": ["testing"],
        "resources": ["cpu"]
    })
    assert response.status_code == 400

    # Get the agent
    response = client.get("/agents/test_agent")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "test_agent"

def test_task_management():
    # Create a task
    response = client.post("/tasks/create", json={
        "description": "Test task",
        "priority": "high",
        "dependencies": []
    })
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]

    # Get the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Test task"
    assert data["priority"] == "high"

    # List all tasks
    response = client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0

def test_state_management():
    # Update state
    response = client.post("/state/update", json={
        "agent_id": "test_agent",
        "key": "test_key",
        "value": {"test": "value"}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "test_key"
    assert data["value"] == {"test": "value"}

    # Get state
    response = client.get("/state/test_key")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == {"test": "value"}

def test_messaging():
    # Send a message
    response = client.post("/messages/send", json={
        "sender_id": "test_agent",
        "recipient_id": "other_agent",
        "content": "Test message",
        "priority": "high"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Test message"
    assert data["priority"] == "high"

    # Get messages
    response = client.get("/messages/other_agent")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) > 0

def test_health_monitoring():
    # Submit health check
    response = client.post("/health/check", json={
        "agent_id": "test_agent",
        "metrics": {
            "cpu_usage": 50.0,
            "memory_usage": 60.0
        },
        "errors": []
    })
    assert response.status_code == 200
    data = response.json()
    assert "health_check" in data
    assert "alerts" in data

    # Get health status
    response = client.get("/health/status")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "alerts" in data

def test_integration():
    # Register multiple agents
    agents = ["agent1", "agent2", "agent3"]
    for agent_id in agents:
        client.post("/agents/register", json={
            "agent_id": agent_id,
            "capabilities": ["testing"],
            "resources": ["cpu"]
        })

    # Create tasks with dependencies
    task1 = client.post("/tasks/create", json={
        "description": "Task 1",
        "priority": "high",
        "dependencies": []
    }).json()

    task2 = client.post("/tasks/create", json={
        "description": "Task 2",
        "priority": "medium",
        "dependencies": [task1["task_id"]]
    }).json()

    # Update state from different agents
    for agent_id in agents:
        client.post("/state/update", json={
            "agent_id": agent_id,
            "key": "shared_state",
            "value": {"agent": agent_id}
        })

    # Send messages between agents
    for i in range(len(agents)):
        sender = agents[i]
        recipient = agents[(i + 1) % len(agents)]
        client.post("/messages/send", json={
            "sender_id": sender,
            "recipient_id": recipient,
            "content": f"Message from {sender}",
            "priority": "medium"
        })

    # Submit health checks
    for agent_id in agents:
        client.post("/health/check", json={
            "agent_id": agent_id,
            "metrics": {
                "cpu_usage": 30.0,
                "memory_usage": 40.0
            }
        })

    # Verify system state
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["agents"] == len(agents)
    assert data["tasks"] >= 2  # At least our two created tasks

def test_onboarding():
    # Register a new agent
    response = client.post("/agents/register", json={
        "agent_id": "new_agent",
        "capabilities": ["reading", "development"],
        "resources": ["cpu", "memory"]
    })
    assert response.status_code == 200
    agent_id = response.json()["agent_id"]

    # Get initial onboarding status
    response = client.get(f"/agents/{agent_id}/onboarding")
    assert response.status_code == 200
    status = response.json()
    assert status["completed_steps"] == 0
    assert status["next_step"] == "read_guidelines"

    # Get next task (should be onboarding)
    response = client.get(f"/tasks/next/{agent_id}")
    assert response.status_code == 200
    task = response.json()
    assert task["is_onboarding"] == True
    assert task["onboarding_step"] == "read_guidelines"

    # Submit onboarding results for first step
    response = client.post(f"/agents/{agent_id}/onboarding/read_guidelines", json={
        "step_id": "read_guidelines",
        "results": {
            "quiz_score": 0.9,
            "time_spent": 400
        }
    })
    assert response.status_code == 200
    status = response.json()["onboarding_status"]
    assert "read_guidelines" in status["completed_steps"]
    assert status["next_step"] == "setup_environment"

    # Get next task (should be next onboarding step)
    response = client.get(f"/tasks/next/{agent_id}")
    assert response.status_code == 200
    task = response.json()
    assert task["is_onboarding"] == True
    assert task["onboarding_step"] == "setup_environment"

    # Complete all onboarding steps
    onboarding_results = {
        "setup_environment": {
            "tools_installed": True,
            "environment_variables_set": True
        },
        "initial_contribution": {
            "code_quality_score": 0.95,
            "tests_passed": True,
            "review_approved": True
        },
        "collaboration_test": {
            "messages_exchanged": 6,
            "code_review_comments": 4,
            "merge_requests_created": 1
        }
    }

    for step_id, results in onboarding_results.items():
        response = client.post(f"/agents/{agent_id}/onboarding/{step_id}", json={
            "step_id": step_id,
            "results": results
        })
        assert response.status_code == 200

    # Verify onboarding completion
    response = client.get(f"/agents/{agent_id}/onboarding")
    assert response.status_code == 200
    status = response.json()
    assert status["completed_steps"] == 4  # All steps completed
    assert status["next_step"] is None

    # Get next task (should be regular task now)
    response = client.get(f"/tasks/next/{agent_id}")
    assert response.status_code == 200
    task = response.json()
    if task != {"status": "no_tasks"}:  # If there are regular tasks
        assert task["is_onboarding"] == False
        assert task["onboarding_step"] is None 