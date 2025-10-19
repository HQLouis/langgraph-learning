"""
Simple curl-based examples for testing the API.

These examples can be run directly from the command line.
"""

# 1. Health Check
"""
curl http://localhost:8000/health
"""

# 2. Create Conversation
"""
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"child_id": "1", "game_id": "0"}'
  
# Response: {"thread_id": "conv_...", "child_id": "1", "game_id": "0", "created_at": "..."}
"""

# 3. Send Message with Streaming (replace THREAD_ID)
"""
curl -X POST http://localhost:8000/conversations/THREAD_ID/messages \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "Hello! Tell me a story"}' \
  --no-buffer
"""

# 4. Get Conversation History (replace THREAD_ID)
"""
curl http://localhost:8000/conversations/THREAD_ID
"""

# 5. Delete Conversation (replace THREAD_ID)
"""
curl -X DELETE http://localhost:8000/conversations/THREAD_ID
"""

# 6. Interactive API Documentation
"""
Open in browser: http://localhost:8000/docs
"""

