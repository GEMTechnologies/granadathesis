#!/bin/bash
# Start all microservices

set -e

echo "🚀 Starting Thesis Microservices..."
echo ""

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo "❌ Error: ../.env file not found"
    echo "   Copy .env file to parent directory"
    exit 1
fi

echo "✓ Environment file found"
echo ""

# Build and start services
echo "📦 Building Docker images..."
docker compose build

echo ""
echo "🔄 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check health
echo ""
echo "🏥 Checking service health..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Gateway not ready yet"

echo ""
echo "✅ Services started!"
echo ""
echo "📍 Service URLs:"
echo "   Gateway:    http://localhost:8000"
echo "   Objectives: http://localhost:8001"
echo "   Content:    http://localhost:8002"
echo "   Search:     http://localhost:8003"
echo ""
echo "📝 View logs: docker-compose logs -f [service-name]"
echo "🛑 Stop all:  docker-compose down"
