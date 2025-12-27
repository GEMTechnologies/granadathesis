#!/bin/bash

# Thesis Project - Local Development Starter
# This script launches all necessary components in separate terminal tabs.

PROJECT_ROOT="/home/gemtech/Desktop/thesis"
BACKEND_DIR="$PROJECT_ROOT/backend"
LIGHTWEIGHT_DIR="$PROJECT_ROOT/backend/lightweight"
FRONTEND_DIR="$PROJECT_ROOT/web-ui"

echo "🚀 Starting Thesis Project Local Environment..."

# Check for gnome-terminal
if ! command -v gnome-terminal &> /dev/null; then
    echo "❌ gnome-terminal not found. This script requires gnome-terminal."
    exit 1
fi

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

echo "✅ All services launched in separate tabs!"
echo "   - Backend: http://localhost:8000"
echo "   - Frontend: http://localhost:3000"
