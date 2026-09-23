#!/bin/sh
# run_tests.sh — discover and run all test files
# Usage: ./scripts/run_tests.sh [directory]

DIR="${1:-.}"
# Accept TOKE_DIR (what CI exports) or legacy TOKEDIR; default to $HOME/tk/toke.
TOKEDIR="${TOKE_DIR:-${TOKEDIR:-$HOME/tk/toke}}"
TOKE=$TOKEDIR/toke
# The capability manifest, as in build_loke.sh: without it a test binary traps CAP001
# the first time the code under test writes a log line.
TKCONFIG="--config=$(cd "$(dirname "$0")/.." && pwd)/tkc.toml"
STDLIB=$TOKEDIR/src/stdlib
BUILDDIR="/tmp/loke-tests"
SCRIPTDIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTDIR="$(cd "$SCRIPTDIR/.." && pwd)"
IFACE_DIR="$PROJECTDIR/build/interfaces"
mkdir -p "$BUILDDIR"
if [ ! -x "$TOKE" ]; then
  echo "ERROR: toke compiler not executable at $TOKE" >&2
  echo "       set TOKE_DIR to your toke checkout" >&2
  exit 1
fi

# ── Build the support archives once ──────────────────────────────────────────
#
# This used to recompile the whole toke stdlib from C, plus cmark and tomlc99, for
# EVERY test — around 120 full stdlib builds per run. Adding loke's 198 module objects
# to each of those link lines took it past what this machine has: the suite ran the
# host out of memory. Compiling each once into an archive is the same link, minus the
# repetition.
VENDOR="$TOKEDIR/stdlib/vendor"
STDLIB_A="$BUILDDIR/libtokestd.a"
LOKE_A="$BUILDDIR/libloke.a"
MODULE_DIR="$PROJECTDIR/packages/browser/build/ooke"

CFLAGS="-std=c99 -D_GNU_SOURCE -O1 -iquote $STDLIB -I$VENDOR/cmark/src -I$VENDOR/tomlc99 -I/opt/homebrew/include -Wno-implicit-function-declaration -Wno-pedantic -DTK_HAVE_OPENSSL"

# Rebuild the stdlib archive only when a source is newer than it.
NEWEST_C=$(find "$STDLIB" "$VENDOR/cmark/src" "$VENDOR/tomlc99" -name '*.c' -newer "$STDLIB_A" 2>/dev/null | head -1)
if [ ! -f "$STDLIB_A" ] || [ -n "$NEWEST_C" ]; then
  echo "Building $STDLIB_A (once) ..."
  OBJDIR="$BUILDDIR/stdobj"
  rm -rf "$OBJDIR"; mkdir -p "$OBJDIR"
  # One file at a time: the whole set at once is what exhausted memory.
  # The three roots are listed separately. A single find with -o clauses applies its
  # ! -name only to the first branch, which silently dropped tomlc99/toml.c and left
  # toml_parse undefined for anything that reads a config file.
  { find "$STDLIB" -name '*.c'
    find "$VENDOR/cmark/src" -name '*.c'
    echo "$VENDOR/tomlc99/toml.c"
  } | while read -r c; do
    case "$c" in *infer_stream.c|*cmark/src/main.c) continue ;; esac
    o="$OBJDIR/$(echo "$c" | tr '/' '_').o"
    clang $CFLAGS -c "$c" -o "$o" 2>/dev/null || echo "  skipped (does not build): $c" >&2
  done
  rm -f "$STDLIB_A"
  ar rcs "$STDLIB_A" "$OBJDIR"/*.o 2>/dev/null
  echo "  $(ls "$OBJDIR"/*.o 2>/dev/null | wc -l | tr -d ' ') objects archived"
fi

# loke's own modules, so a test can call the real thing instead of a copy of it.
# Everything in build/ooke is archived. handlers.o used to be excluded on the
# assumption that it defines a main — it does not, `nm -g` shows neither _main nor
# _tk_main — and excluding it made ooke.handlers.registerall unlinkable, so the two
# tests that check route registration could not run. main.ll.o is the only object with
# a main and it lives one directory up.
if [ -d "$MODULE_DIR" ]; then
  NEWEST_O=$(find "$MODULE_DIR" -name '*.o' -newer "$LOKE_A" 2>/dev/null | head -1)
  if [ ! -f "$LOKE_A" ] || [ -n "$NEWEST_O" ]; then
    echo "Building $LOKE_A (once) ..."
    rm -f "$LOKE_A"
    find "$MODULE_DIR" -name '*.o' -print0 | xargs -0 ar rcs "$LOKE_A" 2>/dev/null
    echo "  $(find "$MODULE_DIR" -name '*.o' | wc -l | tr -d ' ') modules archived"
  fi
else
  echo "NOTE: $MODULE_DIR not found — run scripts/build_loke.sh first, or tests that" >&2
  echo "      call into loke will fail to link rather than silently test a stub." >&2
fi

# ooke's objects, for the page modules: they call ooke.template and ooke.serve.
OOKE_DIR="${OOKE_DIR:-$HOME/tk/toke-ooke}"
OOKE_A="$BUILDDIR/libooke.a"
if [ -d "$OOKE_DIR/src/ooke" ]; then
  NEWEST_OO=$(find "$OOKE_DIR/src/ooke" -name '*.o' -newer "$OOKE_A" 2>/dev/null | head -1)
  if [ ! -f "$OOKE_A" ] || [ -n "$NEWEST_OO" ]; then
    echo "Building $OOKE_A (once) ..."
    rm -f "$OOKE_A"
    find "$OOKE_DIR/src/ooke" -name '*.o' ! -name 'handlers.o' -print0 \
      | xargs -0 ar rcs "$OOKE_A" 2>/dev/null
  fi
fi

# A fixed database key for the suite.
#
# Without it, core.storage.db.ensuredbkey reads the macOS keychain, and
# SecItemCopyMatching blocks on an authorisation dialog that a headless test process
# can never answer — the run does not fail, it hangs. Two integration tests hung the
# whole suite this way. This key is for tests only and is deliberately obvious.
export LOKE_DB_KEY="${LOKE_DB_KEY:-0000000000000000000000000000000000000000000000000000000000000001}"

PASS=0
FAIL=0
ERRORS=""

# AD1.8 — the exclusion is now the one product module, spelled out in full.
#
# packages/core/src/privacy/test_harness.tk is a library module whose name happens to
# start with test_: it declares no main and must not be discovered as a test. The
# exclusion used to be the glob '*/test_harness*', which also swallowed anything else
# beginning with that prefix — including tests/unit/privacy/test_harness_runner.tk, the
# driver that finally executes the harness. Naming the file rather than a prefix keeps
# the product module out and lets the runner in. The pattern has no leading */ so it
# still matches when run_tests.sh is pointed at a subdirectory and find prints a
# relative path with no ./ prefix.
for SRC in $(find "$DIR" -name 'test_*.tk' -not -path '*/_archived-tests/*' -not -path '*packages/core/src/privacy/test_harness.tk' | sort); do
  NAME=$(basename "$SRC" .tk)
  ORIGDIR=$(pwd)

  # Step 1: emit LLVM IR
  if ! $TOKE $TKCONFIG -I "$IFACE_DIR" --emit-llvm --out "$BUILDDIR/$NAME.ll" "$SRC" 2>/dev/null; then
    echo "COMPILE_ERROR $SRC"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (compile)"
    continue
  fi

  # Step 2: link against the prebuilt archives.
  #
  # The archives link lazily, so a test pulls in the modules it actually references
  # and their transitive dependencies, and nothing else. -force_load was wrong here:
  # it dragged in every page handler, which need ooke's own objects, and turned a
  # privacy unit test into a link against the whole application.
  if ! clang $CFLAGS -L/opt/homebrew/lib \
    -x ir "$BUILDDIR/$NAME.ll" -x none \
    $([ -f "$LOKE_A" ] && echo "$LOKE_A") $([ -f "$OOKE_A" ] && echo "$OOKE_A") "$STDLIB_A" \
    -o "$BUILDDIR/$NAME" -lm -lz -lsqlite3 -lssl -lcrypto \
    -framework Security -framework CoreFoundation -lobjc \
    2>/dev/null; then
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
    # A crash is not an assertion count. Printing the raw exit status as
    # "$EXIT failures" reported three segfaulting tests as "139 failures", which
    # reads as 139 assertions and is a completely different problem to diagnose.
    # Above 128 the process died on a signal: 139 is SIGSEGV, 134 SIGABRT, 136 SIGFPE.
    if [ "$EXIT" -gt 128 ]; then
      SIG=$((EXIT - 128))
      case "$SIG" in
        11) WHY="SIGSEGV — segmentation fault" ;;
        6)  WHY="SIGABRT — aborted" ;;
        8)  WHY="SIGFPE — arithmetic fault" ;;
        *)  WHY="killed by signal $SIG" ;;
      esac
      echo "CRASH        $SRC ($WHY)"
      ERRORS="$ERRORS\n  $SRC ($WHY)"
    else
      echo "FAIL         $SRC ($EXIT assertion(s) failed)"
      ERRORS="$ERRORS\n  $SRC ($EXIT assertion(s) failed)"
    fi
    FAIL=$((FAIL+1))
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
