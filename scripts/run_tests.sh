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
# Overridable so two runs can proceed at once. The archives (libloke.a, libmoke.a,
# libtokestd.a) are built INTO this directory, so a hardcoded path meant a second
# concurrent run rebuilt the first one's archives underneath it — which shows up as a
# test that fails to link for no reason anybody can reproduce afterwards.
BUILDDIR="${BUILDDIR:-/tmp/loke-tests}"
# Exported so a test can tell its throwaway HOME (under $BUILDDIR/home) from a real one
# (NC1.10's test_limits writes config.toml only there).
export BUILDDIR
SCRIPTDIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTDIR="$(cd "$SCRIPTDIR/.." && pwd)"
IFACE_DIR="$PROJECTDIR/build/interfaces"
mkdir -p "$BUILDDIR"
if [ ! -x "$TOKE" ]; then
  echo "ERROR: toke compiler not executable at $TOKE" >&2
  echo "       set TOKE_DIR to your toke checkout" >&2
  exit 1
fi

# ── X4.9: refuse to run against a stale build ────────────────────────────────
#
# This has produced a false product defect three times, and each time it cost the same
# half hour: a test fails, the failure is read as a bug in the module under test, the
# module is read carefully, and nothing is wrong with it — the objects in
# packages/browser/build/ooke were older than the source they were built from, so the
# test linked yesterday's code and asserted against today's expectations. Once in the
# other direction too: a test PASSED against stale objects after the source had been
# changed to break it.
#
# The archive rebuild below compares the archive against the OBJECTS, which is the wrong
# end of the chain: nothing compared the objects against the .tk files. So this does.
#
# It refuses rather than rebuilding. Rebuilding silently would make a stale run
# impossible and would also make this script the build system, with a second opinion
# about link order, module order and which trees exist — and when that opinion drifts
# from build_loke.sh's, the failure is a linker error nobody can place. One line saying
# "your build is stale, run the build" cannot drift.
#
# `-newer` compares mtime, so touching a file without changing it trips this. That is the
# right direction to be wrong in: a needless rebuild costs a minute, and a green suite
# against code that is not the code costs a day.
check_stale() {
  # $1 = human name, $2 = object dir, $3.. = source roots
  local name="$1" objdir="$2"; shift 2
  [ -d "$objdir" ] || return 0
  local newest_obj
  newest_obj=$(ls -t "$objdir"/*.o 2>/dev/null | head -1)
  [ -n "$newest_obj" ] || return 0
  local stale
  stale=$(find "$@" -name '*.tk' -not -path '*/build/*' -not -path '*/tests/*' \
            -newer "$newest_obj" 2>/dev/null | head -3)
  if [ -n "$stale" ]; then
    echo "STALE BUILD: $name source is newer than its compiled objects." >&2
    echo "  newest object: $newest_obj" >&2
    echo "$stale" | sed 's/^/  newer source: /' >&2
    echo "" >&2
    echo "  Every test that links $name would run against the OLD code, and would" >&2
    echo "  report a defect in whatever it happens to disagree with. Story X4.9." >&2
    echo "  Run: scripts/build_loke.sh   (and scripts/build_tree.sh moke for moke)" >&2
    return 1
  fi
  return 0
}

STALE=0
check_stale "loke" "$PROJECTDIR/packages/browser/build/ooke" \
  "$PROJECTDIR/packages/core" "$PROJECTDIR/packages/shared" \
  "$PROJECTDIR/packages/browser" || STALE=1
if [ -d "$PROJECTDIR/build/trees/moke/obj" ]; then
  # Every root the moke tree compiles, not only packages/moke. It also builds core, shared
  # and mcp-toke, and libmoke.a carries its own copies of those objects. When mcp-toke
  # changed and moke was not rebuilt, a test linked moke's STALE mcptoke objects, so a
  # fix under test was not in the binary that ran (2026-09-25).
  check_stale "moke" "$PROJECTDIR/build/trees/moke/obj" \
    "$PROJECTDIR/packages/moke" "$PROJECTDIR/packages/mcp-toke" \
    "$PROJECTDIR/packages/core" "$PROJECTDIR/packages/shared" || STALE=1
fi
if [ -d "$PROJECTDIR/build/trees/loke-cli/obj" ]; then
  check_stale "loke-cli" "$PROJECTDIR/build/trees/loke-cli/obj" \
    "$PROJECTDIR/packages/mcp-broker" "$PROJECTDIR/packages/cli" || STALE=1
fi
if [ "$STALE" -ne 0 ]; then
  exit 2
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

# Rebuild the stdlib archive only when a source is newer than it, or when it was built
# from another toke. The mtime test alone cannot see a toolchain SWITCH: pointing TOKE_DIR
# at a different checkout whose sources are older than the archive (the move from toke
# 3.0.0 to 3.1.0, F10.39) would link every test against the previous runtime. The stamp
# names the checkout and its VERSION.
STDLIB_STAMP="$STDLIB_A.toke"
STDLIB_WANT="$TOKEDIR $(cat "$TOKEDIR/VERSION" 2>/dev/null)"
NEWEST_C=$(find "$STDLIB" "$VENDOR/cmark/src" "$VENDOR/tomlc99" -name '*.c' -newer "$STDLIB_A" 2>/dev/null | head -1)
if [ ! -f "$STDLIB_A" ] || [ -n "$NEWEST_C" ] || [ "$(cat "$STDLIB_STAMP" 2>/dev/null)" != "$STDLIB_WANT" ]; then
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
    case "$c" in *cmark/src/main.c) continue ;; esac
    o="$OBJDIR/$(echo "$c" | tr '/' '_').o"
    clang $CFLAGS -c "$c" -o "$o" 2>/dev/null || echo "  skipped (does not build): $c" >&2
  done
  rm -f "$STDLIB_A"
  ar rcs "$STDLIB_A" "$OBJDIR"/*.o 2>/dev/null
  echo "$STDLIB_WANT" > "$STDLIB_STAMP"
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

# moke's modules, so a test under packages/moke/tests/ can call the real thing.
#
# X7.2 recorded moke's 33 tests as untestable, and the reason was this script rather than the
# code: it passed a single `-I build/interfaces` and linked only loke's archive, so no test
# could reach a moke module. The 33 compiled anyway — precisely BECAUSE they import nothing and
# assert a local struct of literals against the same literals, which is the X7.1 trap in its
# clearest form. The first moke test to import production code (test_upload_csv.tk, MK21.17)
# therefore failed to compile where the vacuous ones passed.
#
# Six moke objects still do not assemble (T-35 truncation in the four data modules, T-37 in
# compute and ml/engine — see MK21.16), so this archive is deliberately "whatever assembled".
# The archive links LAZILY, so a test pulls in only what it references: a test that needs one
# of the six fails at link with a named undefined symbol, which is the honest outcome, and a
# test that does not is unaffected.
MOKE_OBJ_DIR="$PROJECTDIR/build/trees/moke/obj"
MOKE_IFACE_DIR="$PROJECTDIR/build/trees/moke/interfaces"
MOKE_A="$BUILDDIR/libmoke.a"
if [ -d "$MOKE_OBJ_DIR" ]; then
  NEWEST_M=$(find "$MOKE_OBJ_DIR" -name '*.o' -newer "$MOKE_A" 2>/dev/null | head -1)
  if [ ! -f "$MOKE_A" ] || [ -n "$NEWEST_M" ]; then
    echo "Building $MOKE_A (once) ..."
    rm -f "$MOKE_A"
    find "$MOKE_OBJ_DIR" -name '*.o' -print0 | xargs -0 ar rcs "$MOKE_A" 2>/dev/null
    echo "  $(find "$MOKE_OBJ_DIR" -name '*.o' | wc -l | tr -d ' ') moke modules archived"
  fi
fi

# T11.2 — the loke-cli tree's OWN modules (packages/mcp-broker and packages/cli), so a test
# can import mcpbroker.* or cli.* instead of re-declaring them. Before this, no module under
# packages/mcp-broker was reachable from any test: build_loke.sh does not compile that tree,
# and a test importing it failed to compile for want of an interface.
#
# Only the tree's own prefixes are archived, and never an object that carries a main: the
# core and shared objects in the same directory are the same modules libloke.a already
# holds. Build it with: scripts/build_trees.sh loke-cli
CLI_OBJ_DIR="$PROJECTDIR/build/trees/loke-cli/obj"
CLI_IFACE_DIR="$PROJECTDIR/build/trees/loke-cli/interfaces"
CLI_A="$BUILDDIR/libcli.a"
if [ -d "$CLI_OBJ_DIR" ]; then
  NEWEST_C=$(find "$CLI_OBJ_DIR" \( -name 'mcpbroker_*.o' -o -name 'cli_*.o' -o -name 'mcptoke_*.o' \) -newer "$CLI_A" 2>/dev/null | head -1)
  if [ ! -f "$CLI_A" ] || [ -n "$NEWEST_C" ]; then
    echo "Building $CLI_A (once) ..."
    rm -f "$CLI_A"
    find "$CLI_OBJ_DIR" \( -name 'mcpbroker_*.o' -o -name 'cli_*.o' -o -name 'mcptoke_*.o' \) ! -name '*_main.o' -print0 \
      | xargs -0 ar rcs "$CLI_A" 2>/dev/null
  fi
fi

# ooke's objects, for the page modules: they call ooke.template and ooke.serve.
# Taken from build/ooke-objs, which build_tree.sh compiles from ooke's source with the
# same toke as everything else. Not from $OOKE_DIR/src/ooke: that IR came from an older
# toke and declared tk_current_error as a plain global, which crashed the server
# (F10.36).
OOKE_BUILD="$PROJECTDIR/build/ooke-objs"
OOKE_A="$BUILDDIR/libooke.a"
if [ -d "$OOKE_BUILD" ]; then
  NEWEST_OO=$(find "$OOKE_BUILD" -name '*.o' -newer "$OOKE_A" 2>/dev/null | head -1)
  if [ ! -f "$OOKE_A" ] || [ -n "$NEWEST_OO" ]; then
    echo "Building $OOKE_A (once) ..."
    rm -f "$OOKE_A"
    find "$OOKE_BUILD" -name '*.o' ! -name 'handlers.o' -print0 \
      | xargs -0 ar rcs "$OOKE_A" 2>/dev/null
  fi
else
  echo "ERROR: $OOKE_BUILD is missing. Run scripts/build_loke.sh first (F10.36)." >&2
  exit 1
fi

# LOKE_DB_KEY — no longer exported, and nothing reads it (X8.3, 2026-09-27).
#
# core.storage.db.ensuredbkey once read this variable before the keychain; that fallback
# was removed, and the last reader, dbkeyfromenv, was deleted with the one assertion that
# kept it alive. The sealed mapping store takes its secret as a PARAMETER, so the tests in
# tests/unit/privacy/test_mapping_{encryption,deletion}.tk pass a 64-character literal of
# their own and never touch the keychain. See the X8.3 note in core.storage.db.

# ── F3b.13: no test may depend on, or change, the developer's own ~/.loke ─────
#
# Every test binary used to run with the developer's HOME. std.homedir(), proc.homedir() and
# os.getenv("HOME") all resolve through $HOME, so about sixty tests created their scratch
# directories inside the real ~/.loke (~/.loke/test-mapping-deletion and friends), and
# anything that loaded the user's configuration read the real thing: after F3b.3,
# page.api.pipeline.pipelineconfig() reads ~/.loke/config.toml through shared.config.loaded(),
# so a developer with privacy.privacy_filter = true silently changed what the pipeline tests
# exercised. settings.json, loke.db, logs and the memory palace were in the same position.
#
# Two parts, as for the smokes (which already run the server under a throwaway HOME):
#   1. each test binary gets its own FRESH, EMPTY HOME under $BUILDDIR/home/<test>, removed
#      and recreated before it runs. The scratch directories the tests create move with it.
#   2. a guard that makes a miss visible. scripts/lib/realhome_guard.c is injected into every
#      test binary; it records each libc filesystem call (open, stat, access, opendir, mkdir,
#      unlink, rename, ...) whose path is the REAL ~/.loke or under it — a read as much as a
#      write. A test that touched it fails, whatever its own assertions said, and so does the
#      run. That catches a hardcoded path or a getpwuid() fallback, which a HOME override
#      alone would not.
#
# The keychain — X8.7, 2026-10-01. No test is given the user's keychain any more. Until
# toke 3.1.0 the three keychain tests used the real LOGIN keychain, and their throwaway
# HOME got a link to the real Library/Keychains so the Security framework could find it.
# That link is gone. Each keychain test now creates its own keychain FILE under its
# throwaway HOME (std.keychain.create), selects it (std.keychain.use: every later call in
# the process goes there, with user interaction disallowed) and destroys it at the end.
#
# The throwaway HOME alone does NOT keep a test out of the login keychain. Measured
# 2026-10-01 at toke 3.1.0: under an empty HOME with no Library/Keychains, a default-keychain
# exists() for a never-written account returned at once with errSecItemNotFound (-25300),
# kind "notfound" — the query was answered from a keychain search list (apparently
# resolved per user, not through $HOME; not investigated further) instead of failing "nokeychain". (The 2026-09-28 hang was
# the pre-3.1.0 runtime waiting on a dialog.) So a test that forgets use() must be assumed
# to reach the user's keychains; the guard below is what catches one that writes.
#
# Keychain traffic goes to securityd over IPC, not through a path, so the ~/.loke guard
# cannot see it. The keychain guard below watches the one thing a write to the login
# keychain must change, the file's metadata — see KEYCHAIN GUARD.
REALHOME="${HOME:?HOME must be set}"
GUARD_PREFIX="$REALHOME/.loke"
TESTHOME_ROOT="$BUILDDIR/home"
GUARD_SRC="$SCRIPTDIR/lib/realhome_guard.c"
GUARD_DYLIB="$BUILDDIR/realhome_guard.dylib"
case "$TESTHOME_ROOT" in
  "$GUARD_PREFIX"|"$GUARD_PREFIX"/*)
    echo "ERROR: BUILDDIR ($BUILDDIR) is inside the real ~/.loke; the test HOMEs must not be" >&2
    exit 3 ;;
esac
if [ ! -f "$GUARD_DYLIB" ] || [ "$GUARD_SRC" -nt "$GUARD_DYLIB" ]; then
  if ! clang -dynamiclib -O1 -o "$GUARD_DYLIB" "$GUARD_SRC"; then
    echo "ERROR: could not build the real-HOME guard from $GUARD_SRC (F3b.13)" >&2
    exit 3
  fi
fi
# Prove the guard is live before trusting its silence. A guard that failed to load (a
# hardened binary strips DYLD_INSERT_LIBRARIES, and so would a future linker flag) reports
# nothing, which is indistinguishable from "nothing touched ~/.loke". The probe is linked
# the same way as a test binary and only stat()s a name that does not exist: it reads
# nothing and creates nothing in the real ~/.loke.
GUARD_PROBE="$BUILDDIR/realhome_guard_probe"
if [ ! -x "$GUARD_PROBE" ] || [ "$GUARD_SRC" -nt "$GUARD_PROBE" ]; then
  printf '#include <sys/stat.h>\nint main(int c,char**v){struct stat s;(void)c;(void)stat(v[1],&s);return 0;}\n' \
    | clang -x c -o "$GUARD_PROBE" - || { echo "ERROR: could not build the guard probe (F3b.13)" >&2; exit 3; }
fi
rm -f "$BUILDDIR/realhome_guard_probe.log"
LOKE_GUARD_PREFIX="$GUARD_PREFIX" LOKE_GUARD_LOG="$BUILDDIR/realhome_guard_probe.log" \
  DYLD_INSERT_LIBRARIES="$GUARD_DYLIB" "$GUARD_PROBE" "$GUARD_PREFIX/.f3b13-guard-probe-does-not-exist"
if ! grep -q 'f3b13-guard-probe' "$BUILDDIR/realhome_guard_probe.log" 2>/dev/null; then
  echo "ERROR: the real-HOME guard did not record the probe's access, so it is not active and" >&2
  echo "       a test reaching the real ~/.loke would pass unseen. Refusing to run (F3b.13)." >&2
  exit 3
fi
mkdir -p "$TESTHOME_ROOT"
GUARDED=0

# ── KEYCHAIN GUARD (X8.7): no test may write to the user's login keychain ─────────────
#
# What is watched: the login keychain FILE's metadata — modification and change times to
# the nanosecond, size and inode, from stat(1). Never its contents: nothing here opens the
# file, lists its items or reads a secret. Every item added, changed or deleted is a write
# to that SQLite file, so a test that writes to the login keychain changes this metadata.
# A test that only READS it (a lookup, an exists()) changes nothing here and is NOT caught;
# that is the limit of a guard that reads no keychain data, stated rather than hidden.
#
# Why per test, and why a re-run. Other processes write the login keychain too (measured
# 2026-10-01 on the development machine: the file changed within two minutes of watching,
# with no loke process involved), so a change during a test's run is only a suspicion. The
# runner snapshots the metadata immediately before and after each test binary; on a change
# it runs that test ONCE more under a fresh HOME and fails it only if the metadata changes
# AGAIN during the second run. A test that writes to the keychain writes on every run; a
# coincidence with another process does not repeat on demand. A test whose second run is
# clean is reported (KEYCHAIN? line) but not failed. The cost, accepted: a test that really
# does write to the keychain is run twice, so it writes twice before it is failed.
#
# LOKE_KEYCHAIN_GUARD_FILES overrides the watched files, for the guard's own mutation test
# (point it at a throwaway keychain the mutant writes to). It is never needed otherwise.
KC_GUARD_FILES="${LOKE_KEYCHAIN_GUARD_FILES:-$REALHOME/Library/Keychains/login.keychain-db}"
KC_GUARD_LIVE=""
for f in $KC_GUARD_FILES; do [ -f "$f" ] && KC_GUARD_LIVE="$KC_GUARD_LIVE $f"; done
kcstat() {
  [ -n "$KC_GUARD_LIVE" ] || return 0
  # shellcheck disable=SC2086
  stat -f '%N %Fm %Fc %z %i' $KC_GUARD_LIVE 2>/dev/null
}
if [ -n "$KC_GUARD_LIVE" ]; then
  KC_SUITE_BEFORE=$(kcstat)
else
  echo "NOTE: keychain guard inactive — none of $KC_GUARD_FILES exists (not macOS, or no login keychain)"
fi
KC_SUSPECTS=""

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
# .claude/ holds agent worktrees, each a whole copy of the repo; discovering their tests ran
# other branches' work-in-progress as if it were this tree's.
for SRC in $(find "$DIR" -name 'test_*.tk' -not -path '*/_archived-tests/*' -not -path '*/.claude/*' -not -path '*packages/core/src/privacy/test_harness.tk' | sort); do
  NAME=$(basename "$SRC" .tk)
  ORIGDIR=$(pwd)

  # Step 1: emit LLVM IR
  # Two interface dirs. `-I` is repeatable, and the moke tree's interfaces are needed by
  # packages/moke/tests/*. build/interfaces is listed FIRST so loke's own modules always win a
  # name collision — both trees emit shared.types.tki, and the moke tree's copy is only as fresh
  # as the last moke build.
  if ! $TOKE $TKCONFIG -I "$IFACE_DIR" $([ -d "$MOKE_IFACE_DIR" ] && echo "-I $MOKE_IFACE_DIR") $([ -d "$CLI_IFACE_DIR" ] && echo "-I $CLI_IFACE_DIR") \
       --emit-llvm --out "$BUILDDIR/$NAME.ll" "$SRC" 2>/dev/null; then
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
    $([ -f "$LOKE_A" ] && echo "$LOKE_A") $([ -f "$MOKE_A" ] && echo "$MOKE_A") $([ -f "$CLI_A" ] && echo "$CLI_A") \
    $([ -f "$OOKE_A" ] && echo "$OOKE_A") "$STDLIB_A" \
    -o "$BUILDDIR/$NAME" -lm -lz -lsqlite3 -lssl -lcrypto \
    -framework Security -framework CoreFoundation -lobjc \
    2>/dev/null; then
    echo "LINK_ERROR   $SRC"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (link)"
    continue
  fi

  # Step 3: run, under a fresh throwaway HOME and the real-HOME guard (F3b.13, above).
  TESTHOME="$TESTHOME_ROOT/$NAME"
  GUARD_LOG="$BUILDDIR/$NAME.realhome.log"
  rm -rf "$TESTHOME" "$GUARD_LOG"
  mkdir -p "$TESTHOME"
  KC_BEFORE=$(kcstat)
  HOME="$TESTHOME" LOKE_GUARD_PREFIX="$GUARD_PREFIX" LOKE_GUARD_LOG="$GUARD_LOG" \
    DYLD_INSERT_LIBRARIES="$GUARD_DYLIB" "$BUILDDIR/$NAME" 2>/dev/null
  EXIT=$?
  KC_AFTER=$(kcstat)
  GUARDED=$((GUARDED+1))
  KC_TOUCHED=""
  if [ "$KC_BEFORE" != "$KC_AFTER" ]; then
    # Suspicion only: confirm with a second run (KEYCHAIN GUARD, above). The re-run's
    # own result is discarded; only whether the keychain changed again counts.
    rm -rf "$TESTHOME"; mkdir -p "$TESTHOME"
    KC_BEFORE2=$(kcstat)
    HOME="$TESTHOME" LOKE_GUARD_PREFIX="$GUARD_PREFIX" LOKE_GUARD_LOG="$GUARD_LOG" \
      DYLD_INSERT_LIBRARIES="$GUARD_DYLIB" "$BUILDDIR/$NAME" >/dev/null 2>&1
    KC_AFTER2=$(kcstat)
    if [ "$KC_BEFORE2" != "$KC_AFTER2" ]; then
      KC_TOUCHED=1
    else
      echo "KEYCHAIN?    $SRC (the watched keychain file changed during its run but not during a re-run: another process, not counted)"
      KC_SUSPECTS="$KC_SUSPECTS $NAME"
    fi
  fi
  if [ -n "$KC_TOUCHED" ]; then
    # Judged first, like REAL_HOME: a test that passed by writing to the user's keychain
    # has not passed.
    echo "KEYCHAIN     $SRC (the watched keychain file,$KC_GUARD_LIVE, changed during this test and again during a re-run; the test's own exit was $EXIT)"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (wrote to the user's login keychain — X8.7 keychain guard)"
  elif [ -s "$GUARD_LOG" ]; then
    # Judged before the test's own result: a test that passed by reading a developer's
    # config has not passed.
    echo "REAL_HOME    $SRC (touched the real ~/.loke; the test's own exit was $EXIT)"
    sort -u "$GUARD_LOG" | head -5 | sed 's/^/               /'
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  $SRC (touched the real ~/.loke — see $GUARD_LOG)"
  elif [ "$EXIT" -eq 0 ]; then
    echo "PASS         $SRC"
    PASS=$((PASS+1))
  else
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
echo "Real-HOME guard: $GUARDED test binaries ran under a throwaway HOME with the guard on $GUARD_PREFIX (F3b.13)"
if [ -n "$KC_GUARD_LIVE" ]; then
  KC_SUITE_AFTER=$(kcstat)
  if [ "$KC_SUITE_BEFORE" = "$KC_SUITE_AFTER" ]; then
    echo "Keychain guard: the watched keychain file's metadata ($KC_GUARD_LIVE ) is identical before and after the run (X8.7)"
  else
    echo "Keychain guard: the watched keychain file changed during the run; per-test checks attribute it as above (suspects not confirmed:${KC_SUSPECTS:- none}) (X8.7)"
  fi
fi
if [ -n "$ERRORS" ]; then
  echo ""
  echo "Failures:$ERRORS"
fi

exit $FAIL
