from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from agent_manager.agent_registry import AgentRegistry, Agent
from agent_manager.agent_profiler import AgentProfiler
from agent_manager.resource_allocator import ResourceAllocator, Resource

from task_orchestrator.task_queue import TaskQueue, Task, TaskPriority, TaskStatus
from task_orchestrator.task_assigner import TaskAssigner
from task_orchestrator.dependency_resolver import DependencyResolver

from state_manager.state_store import StateStore, StateVersion
from state_manager.state_synchronizer import StateSynchronizer
from state_manager.conflict_resolver import ConflictResolver

from messaging.message_queue import MessageQueue, Message, MessagePriority, MessageStatus
from messaging.message_router import MessageRouter
from messaging.priority_handler import PriorityHandler

from monitoring.health_monitor import HealthMonitor, HealthStatus
from monitoring.metrics_collector import MetricsCollector
from monitoring.alert_manager import AlertManager, AlertSeverity

app = FastAPI(title="Agent Coordination Service")

# Initialize components
agent_registry = AgentRegistry()
agent_profiler = AgentProfiler()
resource_allocator = ResourceAllocator()

task_queue = TaskQueue()
dependency_resolver = DependencyResolver()
task_assigner = TaskAssigner(agent_registry, agent_profiler)

state_store = StateStore()
state_synchronizer = StateSynchronizer(state_store, agent_registry)
conflict_resolver = ConflictResolver(agent_profiler)

message_queue = MessageQueue()
message_router = MessageRouter(message_queue, agent_registry)
priority_handler = PriorityHandler(message_queue, agent_profiler)

health_monitor = HealthMonitor()
metrics_collector = MetricsCollector()
alert_manager = AlertManager()

# Models
class AgentRegistration(BaseModel):
    agent_id: str
    capabilities: List[str]
    resources: List[str]

class TaskCreation(BaseModel):
    description: str
    priority: TaskPriority
    dependencies: List[str] = []

class StateUpdate(BaseModel):
    agent_id: str
    key: str
    value: Any

class MessageSend(BaseModel):
    sender_id: str
    recipient_id: str
    content: Any
    priority: MessagePriority

class HealthCheck(BaseModel):
    agent_id: str
    metrics: Dict[str, float]
    errors: List[str] = []

class OnboardingResults(BaseModel):
    step_id: str
    results: Dict[str, Any]

# Routes
@app.get("/")
async def root():
    return {"status": "ok", "service": "agent_coordination"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agents": len(agent_registry.get_all_agents()),
        "tasks": len(task_queue.get_tasks_by_status(TaskStatus.PENDING)),
        "alerts": len(alert_manager.get_active_alerts())
    }

# Agent Management
@app.post("/agents/register")
async def register_agent(registration: AgentRegistration):
    try:
        agent = agent_registry.register_agent(
            agent_id=registration.agent_id,
            capabilities=registration.capabilities,
            resources=registration.resources
        )
        agent_profiler.create_profile(registration.agent_id)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@app.get("/agents")
async def list_agents():
    return agent_registry.get_all_agents()

# Task Management
@app.post("/tasks/create")
async def create_task(task: TaskCreation):
    try:
        new_task = task_queue.create_task(
            task_id=f"task_{len(task_queue._tasks)}",
            description=task.description,
            priority=task.priority,
            dependencies=task.dependencies
        )
        dependency_resolver.add_dependencies(new_task.task_id, task.dependencies)
        return new_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/tasks")
async def list_tasks(status: Optional[TaskStatus] = None):
    if status:
        return task_queue.get_tasks_by_status(status)
    return task_queue._tasks.values()

# State Management
@app.post("/state/update")
async def update_state(update: StateUpdate):
    try:
        state_version = state_synchronizer.synchronize_state(
            agent_id=update.agent_id,
            key=update.key,
            value=update.value
        )
        return state_version
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state/{key}")
async def get_state(key: str, agent_id: Optional[str] = None):
    state = state_store.get_state(key, agent_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return state

# Messaging
@app.post("/messages/send")
async def send_message(message: MessageSend):
    try:
        sent_message = message_router.send_message(
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            content=message.content,
            priority=message.priority
        )
        return sent_message
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/messages/{agent_id}")
async def get_messages(agent_id: str):
    return message_router.get_undelivered_messages(agent_id)

# Health Monitoring
@app.post("/health/check")
async def submit_health_check(check: HealthCheck):
    try:
        health_check = health_monitor.update_health_check(
            agent_id=check.agent_id,
            metrics=check.metrics,
            errors=check.errors
        )
        
        # Record metrics
        for metric, value in check.metrics.items():
            metrics_collector.record_metric(
                name=metric,
                value=value,
                tags={"agent_id": check.agent_id}
            )
        
        # Evaluate alert rules
        alerts = alert_manager.evaluate_alert_rules(check.metrics)
        
        return {
            "health_check": health_check,
            "alerts": alerts
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health/status")
async def get_health_status():
    return {
        "summary": health_monitor.get_health_summary(),
        "alerts": alert_manager.get_alert_summary()
    }

# Add new routes for onboarding
@app.get("/agents/{agent_id}/onboarding")
async def get_onboarding_status(agent_id: str):
    if not agent_registry.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return task_queue.get_onboarding_status(agent_id)

@app.post("/agents/{agent_id}/onboarding/{step_id}")
async def submit_onboarding_results(agent_id: str, step_id: str, results: OnboardingResults):
    if not agent_registry.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        task_queue.update_onboarding_results(agent_id, step_id, results.results)
        return {"status": "success", "onboarding_status": task_queue.get_onboarding_status(agent_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Update task routes to handle onboarding
@app.get("/tasks/next/{agent_id}")
async def get_next_task(agent_id: str, priority: Optional[TaskPriority] = None):
    if not agent_registry.get_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    
    task = task_queue.get_next_task(agent_id, priority)
    if not task:
        return {"status": "no_tasks"}
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 