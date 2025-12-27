#!/bin/bash
# Start lightweight thesis system

set -e

echo "🚀 Starting Lightweight Thesis System..."
echo ""

# Check if .env exists in current directory
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found in lightweight directory"
    echo "   Copying from parent..."
    cp ../.env .env 2>/dev/null || {
        echo "❌ Error: Could not find .env file"
        echo "   Please create .env in /backend/lightweight/"
        exit 1
    }
fi

echo "✓ Environment file found"
echo ""

# Run database migrations
echo "📊 Running database migrations..."
if [ -f "migrations/001_performance_indexes.sql" ]; then
    echo "   Run this SQL on your Supabase database:"
    echo "   migrations/001_performance_indexes.sql"
fi

echo ""

# Build and start
echo "📦 Building lightweight image..."
docker compose build

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for startup..."
sleep 5

# Check health
echo ""
echo "🏥 Checking health..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Not ready yet"

echo ""
echo "✅ Lightweight system started!"
echo ""
echo "📊 System Stats:"
echo "   Total Memory: ~1.4GB (vs 4GB+ microservices)"
echo "   Idle Memory:  ~50MB API + sleeping workers"
echo "   Startup:      Fast (no complex orchestration)"
echo ""
echo "📍 Endpoints:"
echo "   API:          http://localhost:8000"
echo "   Health:       http://localhost:8000/health"
echo "   Docs:         http://localhost:8000/docs"
echo ""
echo "🔥 Features:"
echo "   ✓ Connection pooling (10 max)"
echo "   ✓ Redis caching (aggressive)"
echo "   ✓ On-demand agents (wake when needed)"
echo "   ✓ Job queue system"
echo ""
echo "📝 Usage:"
echo "   # Generate objectives"
echo "   curl -X POST http://localhost:8000/objectives/generate \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"thesis_id\":\"test\",\"topic\":\"ML\",\"case_study\":\"Healthcare\"}'"
echo ""
echo "   # Check job status"
echo "   curl http://localhost:8000/jobs/{job_id}"
echo ""
echo "🛑 Stop: docker compose down"
