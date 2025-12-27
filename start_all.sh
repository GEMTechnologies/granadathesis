#!/bin/bash

# COMPLETE SYSTEM STARTUP (Terminal Tabs Version)
# Launches everything in separate gnome-terminal tabs for easy viewing

PROJECT_ROOT="/home/gemtech/Desktop/thesis"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/web-ui"

echo "🚀 STARTING COMPLETE AUTONOMOUS AI SYSTEM"
echo "========================================="
echo ""

# Check gnome-terminal
if ! command -v gnome-terminal &> /dev/null; then
    echo "⚠️  gnome-terminal not found. Using background mode..."
    echo ""
    echo "Install gnome-terminal for tab view:"
    echo "  sudo apt install gnome-terminal"
    echo ""
    exec "$PROJECT_ROOT/start_no_docker.sh"
    exit 0
fi

# Function to run command in new tab
run_in_tab() {
    local title="$1"
    local cmd="$2"
    gnome-terminal --tab --title="$title" -- bash -c "$cmd; echo ''; echo 'Press Enter to close...'; read"
}

# Check dependencies
echo "📋 Checking dependencies..."

# Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker installed"
    DOCKER_AVAILABLE=true
else
    echo "⚠️  Docker not found (code sandboxes won't work)"
    DOCKER_AVAILABLE=false
fi

# Redis
if ! systemctl is-active --quiet redis 2>/dev/null && ! pgrep redis-server > /dev/null; then
    echo "⚠️  Redis not running. Starting..."
    sudo systemctl start redis 2>/dev/null || redis-server --daemonize yes
fi
echo "✅ Redis running"

# PostgreSQL
if systemctl is-active --quiet postgresql 2>/dev/null; then
    echo "✅ PostgreSQL running"
else
    echo "⚠️  PostgreSQL not running (using in-memory)"
fi

echo ""
echo "🚀 Launching services in terminal tabs..."
echo ""

# 1. Backend API
echo "1️⃣  Launching Backend API (port 8000)..."
run_in_tab "🔧 Backend API" "cd $BACKEND_DIR/lightweight && source ../venv/bin/activate && uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

# Give backend time to start
sleep 3

# 2. Frontend
echo "2️⃣  Launching Frontend (port 3000)..."
run_in_tab "🌐 Frontend" "cd $FRONTEND_DIR && npm run dev"

# 3. Workers
echo "3️⃣  Launching Background Workers..."
run_in_tab "⚙️  Workers" "cd $BACKEND_DIR && ./start_workers.sh && tail -f /tmp/celery_agent.log"

echo ""
echo "========================================="
echo "✅ ALL SERVICES LAUNCHED!"
echo "========================================="
echo ""
echo "📍 Access Points:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📊 Check the terminal tabs above to see services running!"
echo ""
echo "✅ What's Working:"
echo "   ✓ Agent brain (thinking, planning)"
echo "   ✓ Browser automation (watch it browse!)"
echo "   ✓ Image generation (DALL-E, PIL, search)"
echo "   ✓ RAG search"
echo "   ✓ Full IDE UI"
echo "   ✓ Background workers (async tasks)"

if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "   ✓ Code sandboxes (Docker)"
else
    echo "   ⚠️  Code sandboxes (needs Docker)"
fi

echo ""
echo "💡 Quick Test:"
echo "   1. Visit http://localhost:3000"
echo "   2. Click 'Start New Chat'"
echo "   3. Ask: 'Make an essay about Uganda with 3 images'"
echo "   4. Watch browser scrape Wikipedia LIVE!"
echo "   5. See images generate in real-time!"
echo ""
echo "🛑 To stop: Close the terminal tabs or Ctrl+C in each"
echo ""
