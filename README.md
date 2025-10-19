# Lingolino Learning - Backend API

## 🎯 Project Overview

This repository contains the Lingolino agentic learning system with a FastAPI backend for managing conversational interactions.

## 📁 Project Structure

```
langgraph-learning/
├── agentic-system/          # Core agentic system logic
│   ├── background_graph.py  # Background analysis workers
│   ├── immediate_graph.py   # Real-time response graph
│   ├── nodes.py            # Graph nodes
│   ├── states.py           # State definitions
│   └── chat.py             # CLI interface
├── backend/                 # FastAPI application
│   ├── api/                # API routes and dependencies
│   ├── services/           # Business logic layer
│   ├── models/             # Pydantic schemas
│   ├── core/               # Configuration
│   └── main.py             # Application entry point
├── examples/               # Example clients
│   ├── test_api_client.py  # Python client example
│   ├── curl_examples.py    # curl commands
│   └── web_client_example.html  # Browser-based demo
├── functional-testing/     # Functional tests
├── langgraph_tutorial/     # LangGraph tutorials
└── frontend/              # (Future) Frontend application
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment

Create a `.env` file in the root directory with your Google API credentials:

```env
GOOGLE_API_KEY=your_api_key_here
```

### 3. Start the API Server

```bash
./start_api.sh
```

Or manually:

```bash
python -m backend.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4. Test the API

#### Using the Web Client (Easiest)

Open `examples/web_client_example.html` in your browser and start chatting!

#### Using Python Client

```bash
# Install additional dependency
uv pip install sseclient-py

# Run the test client
python examples/test_api_client.py
```

#### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Create conversation
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"child_id": "1", "game_id": "0"}'

# Send message (replace THREAD_ID)
curl -X POST http://localhost:8000/conversations/THREAD_ID/messages \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Hello!"}' \
  --no-buffer
```

## 📚 API Documentation

See [backend/README.md](backend/README.md) for comprehensive API documentation.

### Key Endpoints

- `POST /conversations` - Create new conversation
- `POST /conversations/{thread_id}/messages` - Send message (SSE streaming)
- `GET /conversations/{thread_id}` - Get conversation history
- `DELETE /conversations/{thread_id}` - Delete conversation
- `GET /health` - Health check

## 🔧 Features

- ✅ RESTful API with FastAPI
- ✅ Server-Sent Events (SSE) for real-time streaming
- ✅ Rate limiting (60 req/min)
- ✅ CORS support for frontend integration
- ✅ Comprehensive error handling
- ✅ Auto-generated API documentation
- ✅ Session management
- ✅ Background analysis processing

## 🧪 Development

### Running Tests

```bash
# Functional tests
python -m pytest functional-testing/
```

### CLI Chat Interface

For testing the agentic system without the API:

```bash
python agentic-system/chat.py
```

## 🏗️ Architecture

### Backend Architecture

- **API Layer** (`backend/api/`): FastAPI routes and dependencies
- **Service Layer** (`backend/services/`): Business logic and orchestration
- **Models** (`backend/models/`): Pydantic schemas for validation
- **Core** (`backend/core/`): Configuration and utilities

### Agentic System

- **Immediate Graph**: Real-time responses to user messages
- **Background Graph**: Asynchronous analysis (educational & storytelling)
- **State Management**: LangGraph MemorySaver (in-memory)

### Streaming Strategy

Uses **Server-Sent Events (SSE)** for unidirectional streaming:
- Simpler than WebSockets
- HTTP-based, better proxy/firewall support
- Automatic reconnection
- Perfect for chat streaming use case

## 🔐 Security & Production

### Authentication (Ready to Add)

The architecture supports easy authentication integration:

```python
# Add to backend/api/dependencies.py
async def get_current_user(token: str = Depends(security)):
    # Your auth logic here
    return user

# Add to routes
@router.post("/conversations", dependencies=[Depends(get_current_user)])
```

### Rate Limiting

Configured via environment variables:
- Default: 60 requests/minute per IP
- Configurable in `backend/core/config.py`

### CORS

Configure allowed origins for production in `.env`:

```env
CORS_ORIGINS=["https://your-frontend.com"]
```

## 📦 Dependencies

Main dependencies:
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **LangChain**: LLM framework
- **LangGraph**: Graph-based workflows
- **Pydantic**: Data validation
- **SlowAPI**: Rate limiting

## 🛣️ Roadmap

- [ ] Add persistent storage (PostgreSQL)
- [ ] Implement authentication
- [ ] Add Redis for caching
- [ ] WebSocket support (if needed)
- [ ] Frontend application
- [ ] Docker containerization
- [ ] Kubernetes deployment configs
- [ ] Monitoring & logging (Prometheus, Grafana)

## 📝 License

See LICENSE file for details.

## 🤝 Contributing

This is a learning project. Contributions welcome!

---

**Made with ❤️ using FastAPI, LangChain, and LangGraph**

