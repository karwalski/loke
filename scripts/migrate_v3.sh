#!/bin/bash
# Migrate all .tk files to toke v3 syntax
# 1. Remove pub keyword
# 2. Strip comment lines

DIRS="packages/core/src packages/cli/src packages/shared/src packages/mcp-toke/src packages/mcp-broker/src src"

cd /Users/matthew.watt/loke/loke

for dir in $DIRS; do
  find "$dir" -name '*.tk' -exec sed -i '' 's/pub f=/f=/g; s/pub m\./m./g; s/pub let /let /g' {} +
  find "$dir" -name '*.tk' -exec sed -i '' '/^[[:space:]]*\/\//d' {} +
done

echo "Migration complete"
