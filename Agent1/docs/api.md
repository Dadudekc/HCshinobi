# Task Management System API Documentation

## API Overview
The Task Management System provides a RESTful API for managing tasks, monitoring execution, and retrieving reports. This document outlines the available endpoints, request/response formats, and authentication requirements.

## Authentication

### JWT Authentication
All API endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <token>
```

### API Key Authentication
Alternatively, use an API key in the X-API-Key header:
```
X-API-Key: <api_key>
```

## Endpoints

### Tasks

#### Create Task
```
POST /api/v1/tasks
```
Request body:
```json
{
  "description": "string",
  "priority": "high|medium|low",
  "dependencies": ["string"],
  "tags": ["string"],
  "assignee": "string",
  "metadata": {}
}
```
Response:
```json
{
  "id": "string",
  "status": "pending",
  "created_at": "string",
  "updated_at": "string"
}
```

#### Get Task
```
GET /api/v1/tasks/{task_id}
```
Response:
```json
{
  "id": "string",
  "description": "string",
  "status": "string",
  "priority": "string",
  "created_at": "string",
  "updated_at": "string",
  "dependencies": ["string"],
  "tags": ["string"],
  "assignee": "string",
  "metadata": {},
  "progress": 0,
  "retry_count": 0,
  "max_retries": 0
}
```

#### Update Task
```
PUT /api/v1/tasks/{task_id}
```
Request body:
```json
{
  "description": "string",
  "priority": "string",
  "status": "string",
  "tags": ["string"],
  "assignee": "string",
  "metadata": {}
}
```
Response:
```json
{
  "id": "string",
  "status": "string",
  "updated_at": "string"
}
```

#### Delete Task
```
DELETE /api/v1/tasks/{task_id}
```
Response:
```json
{
  "message": "Task deleted successfully"
}
```

#### List Tasks
```
GET /api/v1/tasks
```
Query parameters:
- status: string
- priority: string
- assignee: string
- tag: string
- page: number
- limit: number

Response:
```json
{
  "tasks": [
    {
      "id": "string",
      "description": "string",
      "status": "string",
      "priority": "string",
      "created_at": "string"
    }
  ],
  "total": 0,
  "page": 0,
  "limit": 0
}
```

### Task Execution

#### Execute Task
```
POST /api/v1/tasks/{task_id}/execute
```
Response:
```json
{
  "execution_id": "string",
  "status": "string",
  "started_at": "string"
}
```

#### Get Execution Status
```
GET /api/v1/tasks/{task_id}/executions/{execution_id}
```
Response:
```json
{
  "execution_id": "string",
  "status": "string",
  "started_at": "string",
  "completed_at": "string",
  "result": {},
  "error": {}
}
```

### Monitoring

#### Get Task Metrics
```
GET /api/v1/tasks/{task_id}/metrics
```
Query parameters:
- start_time: string
- end_time: string
- interval: string

Response:
```json
{
  "metrics": [
    {
      "timestamp": "string",
      "cpu_usage": 0,
      "memory_usage": 0,
      "execution_time": 0,
      "error_rate": 0
    }
  ]
}
```

#### Get System Metrics
```
GET /api/v1/metrics
```
Query parameters:
- start_time: string
- end_time: string
- interval: string

Response:
```json
{
  "metrics": [
    {
      "timestamp": "string",
      "active_tasks": 0,
      "completed_tasks": 0,
      "failed_tasks": 0,
      "average_execution_time": 0,
      "error_rate": 0
    }
  ]
}
```

### Reports

#### Generate Report
```
POST /api/v1/reports
```
Request body:
```json
{
  "type": "execution|performance|error|audit",
  "format": "json|csv|pdf",
  "start_time": "string",
  "end_time": "string",
  "filters": {}
}
```
Response:
```json
{
  "report_id": "string",
  "status": "string",
  "url": "string"
}
```

#### Get Report
```
GET /api/v1/reports/{report_id}
```
Response:
```json
{
  "report_id": "string",
  "type": "string",
  "format": "string",
  "generated_at": "string",
  "url": "string"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "string",
    "details": {}
  }
}
```

### 401 Unauthorized
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "string"
  }
}
```

### 403 Forbidden
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "string"
  }
}
```

### 404 Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "string"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "string",
    "retry_after": 0
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "string"
  }
}
```

## Rate Limiting
- 100 requests per minute per API key
- 1000 requests per minute per JWT token
- Rate limit headers:
  - X-RateLimit-Limit
  - X-RateLimit-Remaining
  - X-RateLimit-Reset

## Pagination
- Default page size: 20
- Maximum page size: 100
- Pagination headers:
  - X-Total-Count
  - X-Page
  - X-Limit
  - X-Has-Next
  - X-Has-Prev 