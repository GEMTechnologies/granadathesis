#!/bin/bash

echo "🛑 Stopping all services..."

# Kill all Node.js processes (frontend)
pkill -9 -f "next dev" 2>/dev/null
pkill -9 -f "node.*thesis" 2>/dev/null

# Kill all Python processes (backend & workers)
pkill -9 -f "uvicorn api:app" 2>/dev/null
pkill -9 -f "content_worker" 2>/dev/null
pkill -9 -f "objective_worker" 2>/dev/null
pkill -9 -f "search_worker" 2>/dev/null
pkill -9 -f "task_worker" 2>/dev/null

# Kill any hanging curl processes
pkill -9 curl 2>/dev/null

# Kill any process using port 8000
lsof -ti:8000 | xargs -r kill -9 2>/dev/null

echo "✅ All services stopped"
echo "⏳ Waiting for ports to be released..."
sleep 5

# Start Redis (if not running)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "📦 Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

echo "🚀 Starting all services in terminal tabs..."

PROJECT_ROOT="/home/gemtech/Desktop/thesis"
BACKEND_DIR="$PROJECT_ROOT/backend"
LIGHTWEIGHT_DIR="$PROJECT_ROOT/backend/lightweight"
FRONTEND_DIR="$PROJECT_ROOT/web-ui"

# Function to run command in new tab
run_in_tab() {
    local title="$1"
    local cmd="$2"
    gnome-terminal --tab --title="$title" -- bash -c "$cmd; echo 'Press Enter to close...'; read"
}

# 1. Start Backend API
echo "   ... Launching Backend API"
run_in_tab "Backend API" "cd $BACKEND_DIR && source venv/bin/activate && cd lightweight && uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

# 2. Start Frontend
echo "   ... Launching Frontend"
run_in_tab "Frontend" "cd $FRONTEND_DIR && npm run dev"

# 3. Start Workers
echo "   ... Launching Workers"
run_in_tab "Worker: Content" "cd $BACKEND_DIR && source venv/bin/activate && cd lightweight && python workers/content_worker.py"
run_in_tab "Worker: Objective" "cd $BACKEND_DIR && source venv/bin/activate && cd lightweight && python workers/objective_worker.py"
run_in_tab "Worker: Search" "cd $BACKEND_DIR && source venv/bin/activate && cd lightweight && python workers/search_worker.py"
run_in_tab "Worker: Task" "cd $BACKEND_DIR && source venv/bin/activate && cd lightweight && python workers/task_worker.py"

echo ""
echo "✅ All services launched in separate tabs!"
echo "   - Backend: http://localhost:8000"
echo "   - Frontend: http://localhost:3000"
echo "   - Workers: Content, Objective, Search, Task"
echo ""
echo "🛑 To stop all: pkill -9 -f 'uvicorn|next dev|worker'"
