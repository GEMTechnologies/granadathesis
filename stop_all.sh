#!/bin/bash

# STOP ALL SERVICES
# Stops backend, frontend, and cleans up

echo "🛑 Stopping Autonomous AI System..."
echo ""

# Stop backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo "✅ Backend stopped"
    fi
    rm .backend.pid
fi

# Stop frontend
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "Stopping Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "✅ Frontend stopped"
    fi
    rm .frontend.pid
fi

# Clean up any orphaned processes
pkill -f "uvicorn.*api:app" 2>/dev/null || true
pkill -f "next.*dev" 2>/dev/null || true
pkill -f "npm.*run.*dev" 2>/dev/null || true

echo ""
echo "✅ All services stopped"
