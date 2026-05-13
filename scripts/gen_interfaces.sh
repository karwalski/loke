#!/bin/sh
# gen_interfaces.sh — Generate .tki interface files for all project modules.
#
# Creates a central interface directory (build/interfaces/) with .tki files
# laid out in directory structure matching dotted module names.
# e.g., module "core.privacy.pipeline" → build/interfaces/core/privacy/pipeline.tki
#
# Uses iterative passes: each pass generates .tki for modules whose imports
# are already resolved. Repeats until no new .tki files are produced.
#
# Usage: ./scripts/gen_interfaces.sh [project_dir] [toke_dir]

set -e

PROJECT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
TOKE_DIR="${2:-/Users/matthew.watt/tk/toke}"
TKC="$TOKE_DIR/toke"
IFACE_DIR="$PROJECT/build/interfaces"

mkdir -p "$IFACE_DIR"

# Collect all .tk source files from project packages
SOURCES=""
for dir in \
  "$PROJECT/packages/core/src" \
  "$PROJECT/packages/shared/src" \
  "$PROJECT/packages/browser/extensions" \
  "$PROJECT/src/browser"; do
  if [ -d "$dir" ]; then
    for f in $(find "$dir" -name '*.tk' -type f 2>/dev/null); do
      SOURCES="$SOURCES $f"
    done
  fi
done

total=$(echo $SOURCES | wc -w | tr -d ' ')
echo "Found $total source modules"

# Iterative passes
pass=0
prev_count=0
while true; do
  pass=$((pass + 1))
  generated=0
  failed=0
  skipped=0

  for src in $SOURCES; do
    # Extract module name from m= declaration
    modname=$(grep '^m=' "$src" | head -1 | sed 's/m=//; s/;//')
    [ -z "$modname" ] && continue

    # Convert dots to slashes for .tki path
    tkipath="$IFACE_DIR/$(echo "$modname" | tr '.' '/').tki"

    # Skip if already generated
    if [ -f "$tkipath" ]; then
      skipped=$((skipped + 1))
      continue
    fi

    # Try to generate .tki
    mkdir -p "$(dirname "$tkipath")"
    # Use --check --emit-interface with -I pointing to our interface dir
    output=$($TKC --check --emit-interface -I "$IFACE_DIR" "$src" 2>&1) || true

    # The compiler creates the .tki in the source file's directory with flat naming
    # We need to find it and move it to the correct location
    srcdir=$(dirname "$src")
    flat_tki="$srcdir/$modname.tki"

    if [ -f "$flat_tki" ]; then
      mv "$flat_tki" "$tkipath"
      generated=$((generated + 1))
    else
      # Check if it was created in cwd
      cwd_tki="$(pwd)/$modname.tki"
      if [ -f "$cwd_tki" ]; then
        mv "$cwd_tki" "$tkipath"
        generated=$((generated + 1))
      else
        failed=$((failed + 1))
      fi
    fi
  done

  cur_count=$((total - failed))
  echo "Pass $pass: generated=$generated skipped=$skipped failed=$failed (${cur_count}/${total} total)"

  # Stop if no progress
  if [ "$generated" -eq 0 ]; then
    break
  fi
done

echo ""
tki_count=$(find "$IFACE_DIR" -name '*.tki' | wc -l | tr -d ' ')
echo "Done: $tki_count .tki files in $IFACE_DIR"

if [ "$failed" -gt 0 ]; then
  echo "Warning: $failed modules could not generate .tki (likely have unresolved imports)"
fi
