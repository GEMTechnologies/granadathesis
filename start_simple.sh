#!/bin/bash

# SIMPLE STARTUP - No fancy tabs, just background processes
# More reliable for systems where gnome-terminal has issues

echo "🚀 SIMPLE STARTUP MODE"
echo "====================="
echo ""

# Kill any existing processes
echo "🧹 Cleaning up..."
pkill -f 'uvicorn.*api:app' 2>/dev/null
pkill -f 'next dev' 2>/dev/null
pkill -f 'celery.*worker' 2>/dev/null
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null
sleep 2

# Create logs directory
mkdir -p logs

# Check Redis
if ! pgrep redis-server > /dev/null; then
    echo "📦 Starting Redis..."
    redis-server --daemonize yes
fi
echo "✅ Redis running"

echo ""
echo "Starting services..."
echo ""

# 1. Backend
echo "1️⃣  Backend API..."
cd /home/gemtech/Desktop/thesis/backend/lightweight
source ../venv/bin/activate
nohup uvicorn api:app --host 0.0.0.0 --port 8000 --reload > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Started (PID: $BACKEND_PID)"

# Wait for backend
sleep 5
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend ready"
else
    echo "   ⚠️  Backend slow to start (check logs/backend.log)"
fi

# 2. Frontend
echo ""
echo "2️⃣  Frontend..."
cd /home/gemtech/Desktop/thesis/web-ui
nohup npm run dev 2>&1 | tee ../logs/frontend.log &
FRONTEND_PID=$!
echo "   Started (PID: $FRONTEND_PID)"

# Wait for frontend
sleep 8
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "   ✅ Frontend ready"
else
    echo "   ⚠️  Frontend slow to start (check logs/frontend.log)"
fi

# 3. Workers (optional)
echo ""
echo "3️⃣  Workers..."
cd /home/gemtech/Desktop/thesis/backend
if [ -f "start_workers.sh" ]; then
    ./start_workers.sh > ../logs/workers.log 2>&1
    echo "   ✅ Workers started"
else
    echo "   ⚠️  Workers script not found (skipping)"
fi

echo ""
echo "========================================="
echo "✅ SYSTEM RUNNING!"
echo "========================================="
echo ""
echo "📍 Access:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo ""
echo "📝 Logs (live tail):"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "🛑 To stop everything:"
echo "   pkill -f 'uvicorn.*api:app'"
echo "   pkill -f 'next dev'"
echo "   pkill -f 'celery.*worker'"
echo ""
echo "💡 Open in browser:"
echo "   http://localhost:3000"
echo ""
