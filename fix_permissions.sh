#!/bin/bash

# Fix permissions for web-ui .next directory
# This happens when Next.js is run as root (e.g., in Docker)

echo "🔧 Fixing permissions..."

cd /home/gemtech/Desktop/thesis/web-ui

# Check if .next exists and has root-owned files
if [ -d ".next" ]; then
    echo "   Removing root-owned .next directory..."
    sudo rm -rf .next
    echo "   ✅ Removed (Next.js will rebuild it)"
else
    echo "   ✅ No .next directory found (good)"
fi

echo "✅ Permissions fixed!"
echo ""
echo "Now you can run: ./start_local.sh"




