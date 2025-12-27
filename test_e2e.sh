#!/bin/bash

# Quick End-to-End Test
# Tests the complete flow from landing page to agent execution

echo "🧪 QUICK E2E TEST"
echo "================"
echo ""

# 1. Check backend is running
echo "1. Checking backend..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend not running! Start with: ./start_all.sh"
    exit 1
fi

# 2. Check frontend is running
echo "2. Checking frontend..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ Frontend is running"
else
    echo "   ❌ Frontend not running! Start with: ./start_all.sh"
    exit 1
fi

# 3. Test workspace creation
echo "3. Testing workspace creation..."
WORKSPACE=$(curl -s -X POST http://localhost:8000/api/workspace/create-with-sandbox \
    -H "Content-Type: application/json" \
    -d '{"topic":"Test","template":"python"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['workspace_id'])" 2>/dev/null)

if [ -n "$WORKSPACE" ]; then
    echo "   ✅ Workspace created: $WORKSPACE"
else
    echo "   ❌ Workspace creation failed"
    exit 1
fi

# 4. Test agent execution
echo "4. Testing agent..."
RESULT=$(curl -s -X POST http://localhost:8000/api/agent/solve-sync \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"Create a function that adds two numbers\",\"workspace_id\":\"$WORKSPACE\"}" | head -c 100)

if [ -n "$RESULT" ]; then
    echo "   ✅ Agent responded"
    echo "   Response: ${RESULT}..."
else
    echo "   ❌ Agent failed"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ QUICK TEST PASSED!"
echo "========================================="
echo ""
echo "🎉 System is working end-to-end!"
echo ""
echo "Try it:"
echo "  1. Open http://localhost:3000"
echo "  2. Click 'Start New Chat'"
echo "  3. Ask agent to build something"
echo "  4. Watch it work in real-time!"
echo ""
