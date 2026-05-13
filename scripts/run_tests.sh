#!/bin/sh
# run_tests.sh — discover and run all test files
# Usage: ./scripts/run_tests.sh [directory]

DIR="${1:-.}"
TOKEDIR=/Users/matthew.watt/tk/toke
TOKE=$TOKEDIR/toke
STDLIB=$TOKEDIR/src/stdlib
BUILDDIR="/tmp/loke-tests"
mkdir -p "$BUILDDIR"

PASS=0
FAIL=0
ERRORS=""

for SRC in $(find "$DIR" -name 'test_*.tk' | sort); do
  NAME=$(basename "$SRC" .tk)
  ORIGDIR=$(pwd)

  # Step 1: emit LLVM IR
  if ! $TOKE --emit-llvm --out "$BUILDDIR/$NAME.ll" "$SRC" 2>/dev/null; then
    echo "COMPILE_ERROR $SRC"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (compile)"
    continue
  fi

  # Step 2: link (deps are relative to toke dir)
  cd "$TOKEDIR"
  if ! $TOKE --emit-deps "$ORIGDIR/$SRC" 2>/dev/null | grep -v '^---' | sort -u | \
    xargs clang -std=c99 -D_GNU_SOURCE -O1 -iquote "$STDLIB" \
    -x ir "$BUILDDIR/$NAME.ll" -x c \
    -o "$BUILDDIR/$NAME" -lm -lz 2>/dev/null; then
    cd "$ORIGDIR"
    echo "LINK_ERROR   $SRC"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (link)"
    continue
  fi
  cd "$ORIGDIR"

  # Step 3: run
  if "$BUILDDIR/$NAME" 2>/dev/null; then
    echo "PASS         $SRC"
    PASS=$((PASS+1))
  else
    EXIT=$?
    echo "FAIL         $SRC ($EXIT failures)"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC ($EXIT failures)"
  fi
done

echo ""
echo "=== Results ==="
echo "Pass: $PASS"
echo "Fail: $FAIL"
echo "Total: $((PASS+FAIL))"
if [ -n "$ERRORS" ]; then
  echo ""
  echo "Failures:$ERRORS"
fi

exit $FAIL
