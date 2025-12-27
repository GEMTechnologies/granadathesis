#!/bin/bash
# Fix all components to use CSS variables properly

find components -name "*.tsx" -type f | while read file; do
  # Replace common patterns
  sed -i 's/bg-panel-light dark:bg-panel-dark/[style={{backgroundColor: "var(--color-panel)"}}]/g' "$file"
  sed -i 's/bg-bg-light dark:bg-bg-dark/[style={{backgroundColor: "var(--color-bg)"}}]/g' "$file"
  sed -i 's/border-border-light dark:border-border-dark/[style={{borderColor: "var(--color-border)"}}]/g' "$file"
done

echo "✅ Fixed all components"
