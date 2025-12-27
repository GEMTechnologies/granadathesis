#!/bin/bash

# NO-DOCKER STARTUP
# Starts the system WITHOUT Docker (browser/images/agent work, no sandboxes)

echo "🚀 STARTING SYSTEM (No Docker Mode)"
echo "===================================="
echo ""
echo "⚠️  Note: Code execution sandboxes won't work, but everything else will!"
echo ""

# Check Redis
if ! systemctl is-active --quiet redis 2>/dev/null && ! pgrep redis-server > /dev/null; then
    echo "📦 Starting Redis..."
    sudo systemctl start redis 2>/dev/null || redis-server --daemonize yes
fi
echo "✅ Redis ready"

# Create logs dir
mkdir -p logs

# Start backend
echo ""
echo "1️⃣  Starting Backend..."
cd backend
source venv/bin/activate
nohup uvicorn lightweight.api:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
echo "$BACKEND_PID" > ../.backend.pid

# Wait for backend
echo "   Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Backend ready!"
        break
    fi
    sleep 1
done

cd ..

# Start frontend
echo ""
echo "2️⃣  Starting Frontend..."
cd web-ui
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
echo "$FRONTEND_PID" > ../.frontend.pid

# Wait for frontend
echo "   Waiting for frontend..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "   ✅ Frontend ready!"
        break
    fi
    sleep 1
done

cd ..

echo ""
echo "======================================"
echo "✅ SYSTEM RUNNING (No Docker)"
echo "======================================"
echo ""
echo "📍 Access:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo ""
echo "✅ Working:"
echo "   - Agent thinking & planning"
echo "   - Browser automation"
echo "   - Image generation"
echo "   - RAG search"
echo "   - Frontend UI"
echo ""
echo "❌ Not Working:"
echo "   - Code execution (needs Docker)"
echo "   - Python/Node sandboxes"
echo ""
echo "💡 To test Essay example:"
echo "   1. Visit http://localhost:3000"
echo "   2. Click 'Start New Chat'"
echo "   3. Ask: 'Make an essay about Uganda with 3 images'"
echo "   4. Watch browser scrape Wikipedia!"
echo "   5. See images generate!"
echo ""
echo "🛑 To stop: ./stop_all.sh"
echo ""
