#!/bin/bash
# Quick Start - Both services at once

set -e

echo "🚀 Starting Complete Thesis System"
echo "="*60
echo ""

# 1. Start Backend
echo "📦 Starting Backend (lightweight)..."
cd /home/gemtech/Desktop/thesis/backend/lightweight

# Copy .env if needed
if [ ! -f ".env" ]; then
    cp ../.env .env
fi

# Start backend
docker compose up -d

echo "✓ Backend started"
echo ""

# 2. Start Web UI
echo "🌐 Starting Web UI..."
cd /home/gemtech/Desktop/thesis/web-ui

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate

# Check if FastAPI is installed
python3 -c "import fastapi" 2>/dev/null || {
    echo "   Installing web UI dependencies..."
    pip install -q fastapi uvicorn
}

# Start web UI in background
nohup python3 server.py > /tmp/thesis-ui.log 2>&1 &
WEB_PID=$!

echo "✓ Web UI started (PID: $WEB_PID)"
echo ""

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 5

# Check health
echo ""
echo "🏥 Health Check:"
echo "   Backend: $(curl -s http://localhost:8000/health | grep -o 'healthy' || echo 'Not ready')"
echo "   Web UI:  $(curl -s http://localhost:3000 | grep -o '<title>' | wc -l | grep -q 1 && echo 'Ready' || echo 'Not ready')"

echo ""
echo "✅ System Ready!"
echo ""
echo "📍 Access Points:"
echo "   🌐 Web UI:      http://localhost:3000"
echo "   ⚙️  API:         http://localhost:8000"
echo "   📚 API Docs:    http://localhost:8000/docs"
echo ""
echo "🛑 To stop:"
echo "   cd /home/gemtech/Desktop/thesis/backend/lightweight && docker compose down"
echo "   kill $WEB_PID"
echo ""
echo "📝 Web UI logs: tail -f /tmp/thesis-ui.log"
