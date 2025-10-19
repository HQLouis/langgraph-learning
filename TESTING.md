# Testing Guide for Lingolino Backend API

## Quick Verification

### 1. Start the Server

```bash
./start_api.sh
```

Or:

```bash
python -m backend.main
```

Expected output:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Test Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app_name": "Lingolino API",
  "version": "0.1.0",
  "timestamp": "2025-10-20T..."
}
```

### 3. Create a Conversation

```bash
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"child_id": "1", "game_id": "0"}'
```

Expected response:
```json
{
  "thread_id": "conv_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "child_id": "1",
  "game_id": "0",
  "created_at": "2025-10-20T..."
}
```

**IMPORTANT**: Copy the `thread_id` for the next steps!

### 4. Send a Message (Streaming)

Replace `YOUR_THREAD_ID` with the thread_id from step 3:

```bash
curl -X POST http://localhost:8000/conversations/YOUR_THREAD_ID/messages \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Hello! Can you introduce yourself?"}' \
  --no-buffer
```

Expected output (streaming):
```
data: Hello
data: ! I'm
data:  Lino
data: , your
data:  friendly
data:  learning
data:  companion
data: ...
data: [DONE]
```

### 5. Get Conversation History

```bash
curl http://localhost:8000/conversations/YOUR_THREAD_ID
```

Expected response:
```json
{
  "thread_id": "conv_...",
  "child_id": "1",
  "game_id": "0",
  "messages": [
    {"role": "human", "content": "Hello! Can you introduce yourself?", "timestamp": null},
    {"role": "ai", "content": "Hello! I'm Lino...", "timestamp": null}
  ],
  "created_at": "2025-10-20T..."
}
```

### 6. Delete Conversation

```bash
curl -X DELETE http://localhost:8000/conversations/YOUR_THREAD_ID
```

Expected: HTTP 204 No Content (no response body)

## Interactive Testing

### Option 1: Web Client (Recommended)

1. Ensure the API server is running
2. Open `examples/web_client_example.html` in your browser
3. Enter Child ID and Game ID
4. Click "Start Conversation"
5. Start chatting!

### Option 2: Python Client

```bash
# Install SSE client library
uv pip install sseclient-py

# Run the test client
python examples/test_api_client.py
```

### Option 3: Swagger UI

1. Open http://localhost:8000/docs in your browser
2. Try out the endpoints interactively
3. Great for exploring the API

## Testing Error Scenarios

### 1. Non-existent Conversation

```bash
curl -X POST http://localhost:8000/conversations/invalid_thread_id/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

Expected: HTTP 404 with error message

### 2. Empty Message

```bash
curl -X POST http://localhost:8000/conversations/YOUR_THREAD_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": ""}'
```

Expected: HTTP 422 Validation Error

### 3. Rate Limiting

Run this script to test rate limiting:

```bash
for i in {1..65}; do
  curl -s http://localhost:8000/health > /dev/null
  echo "Request $i"
done
```

After ~60 requests, you should see HTTP 429 (Too Many Requests)

## Comparison: CLI vs API

### CLI (chat.py)
- Direct terminal interaction
- Single-user session
- Manual startup
- Good for: Testing agentic logic

### API (FastAPI)
- Multi-user support
- RESTful endpoints
- Production-ready
- Good for: Frontend integration, scalability

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)
```

### Import Errors

```bash
# Ensure you're in the project root
cd /Users/lnguyen/GIT/langgraph-learning

# Re-sync dependencies
uv sync
```

### Missing .env File

Create `.env` in project root:

```env
GOOGLE_API_KEY=your_api_key_here
```

## Performance Testing

### Basic Load Test

```bash
# Install Apache Bench (if not installed)
brew install httpd  # macOS

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Expected: ~60 requests should return 429 (rate limited)
```

## Next Steps

1. ✅ Verify all endpoints work
2. ✅ Test streaming with web client
3. ✅ Try rate limiting
4. 📝 Plan frontend integration
5. 🔐 Add authentication (when needed)
6. 💾 Add persistent storage (when needed)

## Questions?

- Check the main README.md
- Review backend/README.md for API details
- Explore the code in backend/ directory

