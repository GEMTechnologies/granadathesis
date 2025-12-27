#!/bin/bash

# Start Celery Workers
# Runs multiple worker processes for different task queues

echo "🔧 Starting Celery Workers..."
echo ""

PROJECT_ROOT="/home/gemtech/Desktop/thesis"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Check if Redis is running
if ! pgrep redis-server > /dev/null; then
    echo "⚠️  Redis not running. Starting..."
    redis-server --daemonize yes
fi
echo "✅ Redis running"

# Function to start worker in background
start_worker() {
    local queue="$1"
    local concurrency="$2"
    
    echo "Starting worker: $queue (concurrency: $concurrency)"
    
    cd "$BACKEND_DIR/lightweight"
    source ../venv/bin/activate
    
    nohup celery -A celery_config worker \
        --queue=$queue \
        --concurrency=$concurrency \
        --loglevel=info \
        --logfile="/tmp/celery_${queue}.log" \
        > /dev/null 2>&1 &
    
    echo "  PID: $!"
}

# Start workers for different queues
start_worker "agent" 2       # Agent tasks (2 concurrent)
start_worker "images" 4      # Image generation (4 concurrent)
start_worker "browser" 2     # Browser automation (2 concurrent)
start_worker "documents" 3   # Document processing (3 concurrent)

echo ""
echo "========================================="
echo "✅ ALL WORKERS STARTED!"
echo "========================================="
echo ""
echo "📊 Worker Queues:"
echo "   agent:     2 workers"
echo "   images:    4 workers"
echo "   browser:   2 workers"
echo "   documents: 3 workers"
echo ""
echo "📝 Logs:"
echo "   tail -f /tmp/celery_agent.log"
echo "   tail -f /tmp/celery_images.log"
echo "   tail -f /tmp/celery_browser.log"
echo "   tail -f /tmp/celery_documents.log"
echo ""
echo "🛑 To stop all workers:"
echo "   pkill -f 'celery.*worker'"
echo ""
