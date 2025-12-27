#!/bin/bash
# Quick script to restart backend and pick up new routes

echo "🔄 Restarting backend container to load new routes..."

# Check if using docker-compose
if command -v docker-compose &> /dev/null; then
    docker-compose restart backend
    echo "✅ Backend restarted with docker-compose"
elif command -v docker &> /dev/null; then
    # Find backend container
    BACKEND_CONTAINER=$(docker ps --filter "name=backend" --format "{{.Names}}" | head -1)
    if [ -n "$BACKEND_CONTAINER" ]; then
        docker restart "$BACKEND_CONTAINER"
        echo "✅ Backend container '$BACKEND_CONTAINER' restarted"
    else
        echo "⚠️  No backend container found. Make sure Docker is running."
    fi
else
    echo "⚠️  Docker not found. If running directly, restart manually."
fi

echo ""
echo "📝 To verify new routes are loaded:"
echo "   curl http://localhost:8000/api/code/health"
echo "   curl http://localhost:8000/api/agent/health"
echo "   curl http://localhost:8000/api/markdown/health"














