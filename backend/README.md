# Lingolino Backend API

FastAPI-based backend for the Lingolino agentic learning system with streaming chat capabilities.

## Architecture

```
backend/
├── api/
│   ├── routes/           # API endpoints
│   └── dependencies.py   # Dependency injection
├── services/             # Business logic layer
├── models/              # Pydantic schemas
├── core/                # Configuration
└── main.py              # Application entry point
```

## Features

- ✅ RESTful API with FastAPI
- ✅ Server-Sent Events (SSE) for streaming responses
- ✅ Rate limiting (60 requests/minute)
- ✅ CORS support for frontend integration
- ✅ Conversation session management
- ✅ Background analysis processing
- ✅ Comprehensive error handling
- ✅ API documentation (Swagger/ReDoc)

## Installation

Install dependencies using uv:

```bash
uv sync
```

## Running the Server

### Development Mode

```bash
cd /Users/lnguyen/GIT/langgraph-learning
python -m backend.main
```

Or with uvicorn directly:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check

```http
GET /health
```

### Create Conversation

```http
POST /conversations
Content-Type: application/json

{
  "child_id": "1",
  "game_id": "0"
}
```

**Response:**
```json
{
  "thread_id": "conv_abc123-def456-...",
  "child_id": "1",
  "game_id": "0",
  "created_at": "2025-10-20T10:30:00Z"
}
```

### Send Message (Streaming)

```http
POST /conversations/{thread_id}/messages
Content-Type: application/json
Accept: text/event-stream

{
  "message": "Hello! Can you tell me a story?"
}
```

**Response (SSE Stream):**
```
data: Hello
data: ! I'd
data:  love
data:  to tell
data:  you a
data:  story...
data: [DONE]
```

### Get Conversation History

```http
GET /conversations/{thread_id}
```

**Response:**
```json
{
  "thread_id": "conv_abc123",
  "child_id": "1",
  "game_id": "0",
  "messages": [
    {"role": "human", "content": "Hello!"},
    {"role": "ai", "content": "Hi there!"}
  ],
  "created_at": "2025-10-20T10:30:00Z"
}
```

### Delete Conversation

```http
DELETE /conversations/{thread_id}
```

**Response:** 204 No Content

## Interactive Documentation

Once the server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

Configuration is managed via environment variables or `.env` file:

```env
# API Settings
DEBUG=false

# CORS Settings (configure for production)
CORS_ORIGINS=["http://localhost:3000", "https://your-frontend.com"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# LLM Settings
LLM_MODEL=google_genai:gemini-2.0-flash
```

## Rate Limiting

- Default: 60 requests per minute per IP
- Burst: 10 requests
- Headers returned:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## CORS

CORS is enabled for cross-origin requests. Configure allowed origins in settings for production.

## Error Handling

All errors return consistent JSON format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE"
}
```

Common status codes:
- `200`: Success
- `201`: Created
- `204`: No Content (successful deletion)
- `400`: Bad Request
- `404`: Not Found
- `429`: Too Many Requests (rate limit)
- `500`: Internal Server Error

## Future Enhancements

### Authentication (Ready to Implement)

The architecture supports easy addition of authentication:

1. Add authentication dependency to `backend/api/dependencies.py`
2. Add `Depends(get_current_user)` to protected endpoints
3. Popular options:
   - JWT tokens
   - API keys
   - OAuth2

Example:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Verify token
    return user
```

### Persistent Storage

Current implementation uses in-memory storage. For production:

1. Replace `MemorySaver` with PostgreSQL checkpointer
2. Add database for conversation metadata
3. Consider Redis for caching

## Development

### Project Structure

```
langgraph-learning/
├── agentic-system/      # Core business logic (existing)
├── backend/             # FastAPI application (new)
├── frontend/            # Future frontend application
└── pyproject.toml
```

### Testing

Run the test client:

```bash
python examples/test_api_client.py
```

### Code Quality

The codebase follows:
- Clean code principles
- Separation of concerns
- Dependency injection
- Type hints throughout
- Comprehensive docstrings

