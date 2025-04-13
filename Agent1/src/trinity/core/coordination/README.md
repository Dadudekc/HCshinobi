# Agent Coordination Service

A FastAPI-based coordination service for managing agent interactions and task distribution.

## Features

- Agent registration and management
- Task creation and distribution
- State management for agent interactions
- Health monitoring and status reporting

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the service:
```bash
uvicorn main:app --reload
```

The service will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /`: Service status
- `GET /health`: Detailed health information

### Agent Management
- `POST /agents/register`: Register a new agent
  - Request body:
    ```json
    {
        "agent_id": "string",
        "capabilities": ["string"],
        "resources": ["string"]
    }
    ```

### Task Management
- `POST /tasks/create`: Create a new task
  - Request body:
    ```json
    {
        "description": "string",
        "priority": "high|medium|low",
        "dependencies": ["string"]
    }
    ```

### State Management
- `POST /state/update`: Update agent state
  - Request body:
    ```json
    {
        "agent_id": "string",
        "key": "string",
        "value": "any"
    }
    ```

## Development

### Running Tests
```bash
pytest
```

### Environment Variables
Create a `.env` file with the following variables:
```
LOG_LEVEL=INFO
PORT=8000
```

## Architecture

The service uses an in-memory storage system for simplicity, but can be extended to use a persistent database. The main components are:

- Agent Registry: Tracks registered agents and their capabilities
- Task Queue: Manages task creation and distribution
- State Store: Maintains state information for agent interactions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 