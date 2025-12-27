#!/bin/bash

# Stop Workers Script
# Gracefully stops all background workers

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping all workers...${NC}"

if [ -f logs/workers.pid ]; then
    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "  Stopping PID $pid..."
            kill $pid
        fi
    done < logs/workers.pid
    rm logs/workers.pid
fi

# Also kill by pattern match as backup
pkill -f "lightweight.workers" || true

echo -e "${GREEN}✅ All workers stopped${NC}"
