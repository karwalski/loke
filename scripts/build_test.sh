#!/bin/sh
# build_test.sh — compile and run a single toke test file standalone
# Usage: ./scripts/build_test.sh tests/unit/memory/test_aaak.tk
set -e

TOKEDIR=/Users/matthew.watt/tk/toke
TOKE=$TOKEDIR/toke
STDLIB=$TOKEDIR/src/stdlib
SRC="$1"

if [ -z "$SRC" ]; then
  echo "Usage: $0 <test.tk>"
  exit 1
fi

NAME=$(basename "$SRC" .tk)
BUILDDIR="/tmp/loke-tests"
mkdir -p "$BUILDDIR"

# Step 1: emit LLVM IR (suppress warnings)
$TOKE --emit-llvm --out "$BUILDDIR/$NAME.ll" "$SRC" 2>/dev/null

# Step 2: get deps (paths are relative to toke dir) and compile
cd "$TOKEDIR"
$TOKE --emit-deps "$OLDPWD/$SRC" 2>/dev/null | grep -v '^---' | sort -u | \
  xargs clang -std=c99 -D_GNU_SOURCE -O1 -iquote "$STDLIB" \
  -x ir "$BUILDDIR/$NAME.ll" -x c \
  -o "$BUILDDIR/$NAME" -lm -lz 2>/dev/null
cd "$OLDPWD"

# Step 3: run
"$BUILDDIR/$NAME"
EXIT=$?

if [ $EXIT -eq 0 ]; then
  echo "PASS $SRC"
else
  echo "FAIL $SRC ($EXIT failures)"
fi

exit $EXIT
