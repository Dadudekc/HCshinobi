# Consolidated Project

This repository contains the consolidated and deduplicated version of the project, combining functionality from multiple directories and eliminating redundancies.

## Directory Structure

```
consolidated/
├── core/
│   ├── services/          # Core services (task management, etc.)
│   ├── task_engine/       # Task scheduling and execution
│   └── monitoring/        # System monitoring and metrics
├── overnight_scripts/
│   ├── chat_mate/        # Chat-related automation
│   └── tools/            # Utility scripts and tools
└── agents/               # Agent-specific functionality
```

## Components

### Core

The core module provides fundamental functionality:
- Task Management: Scheduling and executing tasks
- Monitoring: System health and metrics collection
- Services: Shared services used across the project

### Overnight Scripts

Automated scripts and tools:
- Chat Mate: Chat automation and processing
- Tools: Utility scripts for various tasks

### Agents

Agent-specific implementations and extensions.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Development

- Follow PEP 8 style guidelines
- Write tests for new functionality
- Update documentation as needed

## Testing

Run tests with pytest:
```bash
pytest tests/
```

## Documentation

Generate documentation with Sphinx:
```bash
cd docs
make html
``` 