#!/bin/bash

# Fix workspace permissions and create default workspace

echo "🔧 Fixing workspace permissions..."

cd /home/gemtech/Desktop/thesis

# 1. Fix ownership (if root-owned)
if [ -d "thesis_data/default" ] && [ "$(stat -c '%U' thesis_data/default)" = "root" ]; then
    echo "   Fixing ownership of thesis_data/default (requires sudo)..."
    sudo chown -R gemtech:gemtech thesis_data/default
fi

# 2. Create default workspace structure
echo "   Creating default workspace structure..."
mkdir -p thesis_data/default/{sections,sources,outputs,data}

# 3. Set permissions
echo "   Setting permissions..."
chmod -R 755 thesis_data/default

# 4. Create a test file to verify
echo "   Creating test file..."
echo "# Default Workspace

This is the default workspace.

## Structure
- sections/ - For thesis sections
- sources/ - For research sources
- outputs/ - For generated outputs
- data/ - For research data

" > thesis_data/default/README.md

echo "✅ Workspace fixed!"
echo ""
echo "Default workspace: thesis_data/default/"
ls -la thesis_data/default/




