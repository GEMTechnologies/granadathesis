#!/bin/bash
# Quick script to start both frontend and backend servers

echo "🚀 Starting Thesis Platform Services..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Kill any existing processes on ports 3000 and 8000
echo "🧹 Cleaning up existing processes..."
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null
echo "✓ Ports cleared"
echo ""

# Start Backend
echo "📦 Starting Backend Server..."
cd /home/gemtech/Desktop/thesis/backend
source venv/bin/activate

# Install aioredis if missing
python -c "import aioredis" 2>/dev/null || {
    echo "   Installing missing dependency: aioredis"
    pip install -q aioredis
}

# Start backend in background
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ Backend starting (PID: $BACKEND_PID)"
echo ""

# Start Frontend
echo "🌐 Starting Frontend Server..."
cd /home/gemtech/Desktop/thesis/web-ui
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✓ Frontend starting (PID: $FRONTEND_PID)"
echo ""

# Wait for services to start
echo "⏳ Waiting for services to start (10 seconds)..."
sleep 10

# Check status
echo ""
echo "🏥 Checking Service Status..."
echo ""

# Check Backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC} - http://localhost:8000"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "   (health check passed)"
else
    echo -e "${RED}✗ Backend is NOT responding${NC}"
    echo "   Check logs: tail -f /tmp/backend.log"
fi

# Check Frontend
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✓ Frontend is running${NC} - http://localhost:3000"
else
    echo -e "${YELLOW}⚠ Frontend may still be starting${NC}"
    echo "   Check logs: tail -f /tmp/frontend.log"
fi

echo ""
echo "✅ Services Started!"
echo ""
echo "📍 Access Points:"
echo "   🌐 Frontend:  http://localhost:3000"
echo "   ⚙️  Backend:   http://localhost:8000"
echo "   📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "📝 View Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "🛑 To Stop:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   or: pkill -f 'uvicorn main:app' && pkill -f 'next dev'"
echo ""
















