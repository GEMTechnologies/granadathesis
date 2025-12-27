#!/bin/bash

# Quick script to add image API keys to .env file
# Usage: ./ADD_API_KEYS.sh

ENV_FILE="backend/lightweight/.env"

echo "🔑 Adding Image API Keys to .env file..."
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env file not found at $ENV_FILE"
    echo "Creating it now..."
    touch "$ENV_FILE"
fi

# Check if keys already exist
if grep -q "PIXABAY_API_KEY" "$ENV_FILE"; then
    echo "⚠️  PIXABAY_API_KEY already exists in .env"
    read -p "Overwrite existing keys? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    # Remove existing keys
    sed -i '/^PIXABAY_API_KEY=/d' "$ENV_FILE"
    sed -i '/^UNSPLASH_API_KEY=/d' "$ENV_FILE"
    sed -i '/^PEXELS_API_KEY=/d' "$ENV_FILE"
fi

# Add keys to .env
echo "" >> "$ENV_FILE"
echo "# ============================================" >> "$ENV_FILE"
echo "# IMAGE SEARCH APIs - Added $(date)" >> "$ENV_FILE"
echo "# ============================================" >> "$ENV_FILE"
echo "PIXABAY_API_KEY=53559453-cf8390e0a852afec094956c88" >> "$ENV_FILE"
echo "UNSPLASH_API_KEY=rbpF37LP3D6wsuYlLmTJSflSRYAoAWElFr7Ovq9z_SQ" >> "$ENV_FILE"
echo "PEXELS_API_KEY=vMiz3JQWhg8pQf8LMad7I9dwKweC65TzYDa1V7aayoAtcTUTJQrLjNqX" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"

echo "✅ API keys added successfully!"
echo ""
echo "📋 Keys added:"
echo "   - PIXABAY_API_KEY"
echo "   - UNSPLASH_API_KEY"
echo "   - PEXELS_API_KEY"
echo ""
echo "🔄 Restart your backend server for changes to take effect:"
echo "   pkill -f uvicorn"
echo "   cd backend/lightweight"
echo "   uvicorn api:app --host 0.0.0.0 --port 8000"




