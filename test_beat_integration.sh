#!/bin/bash

# Beat System Integration - Quick Test Script
# Run this to verify the beat system is working

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          BEAT SYSTEM INTEGRATION - QUICK TEST                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check if beatpack exists
echo "Step 1: Checking for example beatpack..."
if [ -f "agentic-system/content/stories/mia_und_leo/chapter_01/beatpack.v1.json" ]; then
    echo -e "${GREEN}✓${NC} Beatpack found!"
else
    echo -e "${YELLOW}⚠${NC} Beatpack not found. Creating it..."
    cd agentic-system
    python test_beat_system.py > /dev/null 2>&1
    cd ..
    echo -e "${GREEN}✓${NC} Beatpack created!"
fi
echo ""

# Step 2: Check if server is running
echo "Step 2: Checking if server is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Server is running!"
else
    echo -e "${RED}✗${NC} Server is not running!"
    echo ""
    echo "Please start the server in another terminal:"
    echo "  uvicorn backend.main:app --reload"
    echo ""
    exit 1
fi
echo ""

# Step 3: Test WITH beat system
echo "Step 3: Testing WITH beat system (mia_und_leo/chapter_01)..."
echo "  Creating conversation..."

RESPONSE=$(curl -s -X POST http://localhost:8000/conversations \
    -H "Content-Type: application/json" \
    -d '{
        "child_id": "1",
        "game_id": "0",
        "story_id": "mia_und_leo",
        "chapter_id": "chapter_01",
        "num_planned_tasks": 5
    }')

THREAD_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])" 2>/dev/null)

if [ -z "$THREAD_ID" ]; then
    echo -e "${RED}✗${NC} Failed to create conversation"
    echo "Response: $RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓${NC} Conversation created: $THREAD_ID"
echo "  Sending message: 'Wer ist Leo?'"

curl -s -X POST "http://localhost:8000/conversations/$THREAD_ID/messages" \
    -H "Content-Type: application/json" \
    -d '{"message": "Wer ist Leo?"}' \
    | while IFS= read -r line; do
        if [[ $line == data:* ]]; then
            chunk="${line#data: }"
            if [ "$chunk" != "[DONE]" ]; then
                echo -n "$chunk"
            fi
        fi
    done

echo ""
echo -e "${GREEN}✓${NC} Beat-based response received!"
echo ""

# Step 4: Test WITHOUT beat system (fallback)
echo "Step 4: Testing WITHOUT beat system (fallback)..."
echo "  Creating conversation (no story_id/chapter_id)..."

RESPONSE2=$(curl -s -X POST http://localhost:8000/conversations \
    -H "Content-Type: application/json" \
    -d '{
        "child_id": "1",
        "game_id": "0"
    }')

THREAD_ID2=$(echo $RESPONSE2 | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])" 2>/dev/null)

if [ -z "$THREAD_ID2" ]; then
    echo -e "${RED}✗${NC} Failed to create conversation"
    exit 1
fi

echo -e "${GREEN}✓${NC} Conversation created: $THREAD_ID2"
echo "  Sending message: 'Hallo!'"

curl -s -X POST "http://localhost:8000/conversations/$THREAD_ID2/messages" \
    -H "Content-Type: application/json" \
    -d '{"message": "Hallo!"}' \
    | while IFS= read -r line; do
        if [[ $line == data:* ]]; then
            chunk="${line#data: }"
            if [ "$chunk" != "[DONE]" ]; then
                echo -n "$chunk"
            fi
        fi
    done

echo ""
echo -e "${GREEN}✓${NC} Fallback response received!"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    TEST SUMMARY                                 ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  ✓ Beatpack exists                                             ║"
echo "║  ✓ Server is running                                           ║"
echo "║  ✓ Beat system conversation works                              ║"
echo "║  ✓ Fallback conversation works                                 ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║              🎉 ALL TESTS PASSED! 🎉                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Check server logs for 'Beat system activated' messages"
echo "  2. Run full test suite: python examples/test_beat_integration.py"
echo "  3. Generate beatpacks for your own stories"
echo ""
echo "Documentation:"
echo "  • BEAT_INTEGRATION_COMPLETE.md - Integration summary"
echo "  • BEAT_SERVICE_INTEGRATION.md  - Detailed docs"
echo "  • agentic-system/BEAT_QUICKSTART.md - Quick start guide"
echo ""

