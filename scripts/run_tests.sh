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

for SRC in $(find "$DIR" -name 'test_*.tk' -not -path '*/_archived-tests/*' -not -path '*/test_harness*' | sort); do
  NAME=$(basename "$SRC" .tk)
  ORIGDIR=$(pwd)

  # Step 1: emit LLVM IR
  IFACE_DIR="$(cd "$(dirname "$0")/.." && pwd)/build/interfaces"
  if ! $TOKE -I "$IFACE_DIR" --emit-llvm --out "$BUILDDIR/$NAME.ll" "$SRC" 2>/dev/null; then
    echo "COMPILE_ERROR $SRC"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (compile)"
    continue
  fi

  # Step 2: link with full stdlib + vendor
  VENDOR="$TOKEDIR/stdlib/vendor"
  CMARK_C=$(find "$VENDOR/cmark/src" -name '*.c' ! -name 'main.c' 2>/dev/null | tr '\n' ' ')
  TOML_C="$VENDOR/tomlc99/toml.c"
  if ! find "$STDLIB" -name '*.c' ! -name 'llm_tool.c' ! -name 'infer_stream.c' ! -name 'sys_glue.c' -print0 | \
    xargs -0 clang -std=c99 -D_GNU_SOURCE -O1 -iquote "$STDLIB" \
    -I"$VENDOR/cmark/src" -I"$VENDOR/tomlc99" \
    -I/opt/homebrew/include -L/opt/homebrew/lib \
    -Wno-implicit-function-declaration -Wno-pedantic -DTK_HAVE_OPENSSL \
    -x ir "$BUILDDIR/$NAME.ll" \
    -x c $CMARK_C $TOML_C \
    -o "$BUILDDIR/$NAME" -lm -lz -lsqlite3 -lssl -lcrypto \
    -framework Security -framework CoreFoundation -lobjc \
    -Wl,-undefined,dynamic_lookup 2>/dev/null; then
    echo "LINK_ERROR   $SRC"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (link)"
    continue
  fi

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
