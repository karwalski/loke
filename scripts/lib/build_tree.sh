#!/bin/sh
# build_tree.sh — compile ONE tree of toke modules, census what breaks, link if asked.
#
# Why this exists
# ---------------
# scripts/build_loke.sh compiles exactly four roots (packages/core/src,
# packages/shared/src, packages/browser/extensions, packages/browser/pages) — 218
# modules, green. It is also the only place in this repo that knows how to compile a
# tree at all: the fresh-interface copy, the dependency-ordered interface pass, and
# the compile census were all written inline in that one script.
#
# 247 non-test .tk files in six other trees had therefore never been compiled once:
# legacy src/ (102), packages/moke (96 incl. pages and data), packages/cli (26),
# packages/browser/src (13), packages/mcp-broker (6), packages/mcp-toke (4). Measured
# cold, they cost 951 errors across 247 files — and roughly a third of that was not a
# defect. It was the absence of a per-tree interface pass: packages/cli alone had
# eleven "module 'cli.output' not found" errors for its OWN sibling module, because
# build/interfaces only ever held interfaces for the four built roots.
#
# So the pipeline is extracted here and the tree is a parameter. The link phase is a
# parameter too, which is the point: two of the five targets must not link at all
# (legacy src/ has no entry point, and packages/browser/src imports std.webview,
# which the toolchain does not have), and pretending otherwise would report a missing
# stdlib module as a broken tree.
#
# What it measures
# ----------------
#   * how many of the tree's modules emit an interface,
#   * how many compile, with every diagnostic captured to a per-tree break report,
#   * optionally, the tree's undefined symbols (scripts/symbol_census.py),
#   * optionally, whether the tree links.
#
# What it does NOT measure
# ------------------------
# Whether the tree is CORRECT. A module that compiles and links can still be wrong,
# and a tree with zero errors has only been type-checked. It also does not run the
# tree's tests — that is scripts/run_tests.sh.
#
# It does not suppress compiler stderr and does not pass -Wl,-undefined,dynamic_lookup,
# because both turn a build failure into a runtime crash.
#
# Usage
# -----
#   scripts/lib/build_tree.sh [options] <name> <root>...
#
#   --link=none|binary     none (default) type-checks only; binary links an executable
#   --main=FILE            entry-point .tk compiled to <objroot>/main.ll (link=binary)
#   --binary=PATH          output executable (default <objroot>/<name>)
#   --extra=FILE[:NAME]    extra .tk outside the roots, compiled into the census
#   --iface=DIR            interface dir (default build/trees/<name>/interfaces)
#   --objdir=DIR           object dir   (default build/trees/<name>/obj)
#   --report=FILE          break report (default build/trees/<name>/break-report.txt)
#   --legacy-report=FILE   also copy the break report here when done
#   --exclude=RELPATH      drop this source from the tree (repeatable)
#   --iface-root=DIR       root used for the INTERFACE pass only, not compiled or
#                          censused — how a small tree gets resolvable sibling
#                          imports without inflating its own error count (repeatable)
#   --no-link=BUILDNAME    compile and census this module but keep its object off the
#                          link line, e.g. a second f=main (repeatable)
#   --handler-iface-pass=DIR  re-emit interfaces for page handlers under DIR
#   --gen-handlers=PAGES:OUT  run ooke's gen_handlers.sh over PAGES into OUT
#   --link-objdir=DIR      extra object dir on the link line (repeatable)
#   --ooke-objs            put ooke's own objects on the link line
#   --symbols / --no-symbols   undefined-symbol census (default: on)
#   --probe                per-module link probe (slow; off by default)
#   --keep-going           attempt the link even though modules failed to compile.
#                          It does NOT make the run a pass: the exit status still
#                          reports the failures.
#
# Exit status: 0 only if every module compiled and, when linking, the link succeeded.
# The census and the symbol census always run first, so a red tree still produces its
# full diagnostic set — that is the run where the classification is worth reading.

set -eu

PROJECTDIR="$(cd "$(dirname "$0")/../.." && pwd)"
OOKE_DIR="${OOKE_DIR:-$HOME/tk/toke-ooke}"
TOKE_DIR="${TOKE_DIR:-$HOME/tk/toke}"
TOKE="$TOKE_DIR/toke"
STDLIB="$TOKE_DIR/src/stdlib"
VENDOR="$TOKE_DIR/stdlib/vendor"
# loke's capability manifest (F10.9). toke looks for ./tkc.toml in the CURRENT
# directory; this script may cd, so the path is passed explicitly. Without it every
# compiled binary traps CAP001 on its first log line.
TKCONFIG="--config=$PROJECTDIR/tkc.toml"

LINK=none
MAIN=
BINARY=
IFACE_DIR=
OBJDIR=
REPORT=
LEGACY_REPORT=
EXTRAS=
EXCLUDES=
IFACE_ROOTS=
NO_LINK=
HANDLER_IFACE=
GEN_HANDLERS=
LINK_OBJDIRS=
OOKE_OBJS=0
SYMBOLS=1
PROBE=0
KEEP_GOING=0

die() { echo "ERROR: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --link=*)               LINK=${1#*=} ;;
    --main=*)               MAIN=${1#*=} ;;
    --binary=*)             BINARY=${1#*=} ;;
    --iface=*)              IFACE_DIR=${1#*=} ;;
    --objdir=*)             OBJDIR=${1#*=} ;;
    --report=*)             REPORT=${1#*=} ;;
    --legacy-report=*)      LEGACY_REPORT=${1#*=} ;;
    --extra=*)              EXTRAS="$EXTRAS ${1#*=}" ;;
    --exclude=*)            EXCLUDES="$EXCLUDES ${1#*=}" ;;
    --iface-root=*)         IFACE_ROOTS="$IFACE_ROOTS ${1#*=}" ;;
    --no-link=*)            NO_LINK="$NO_LINK ${1#*=}" ;;
    --handler-iface-pass=*) HANDLER_IFACE=${1#*=} ;;
    --gen-handlers=*)       GEN_HANDLERS=${1#*=} ;;
    --link-objdir=*)        LINK_OBJDIRS="$LINK_OBJDIRS ${1#*=}" ;;
    --ooke-objs)            OOKE_OBJS=1 ;;
    --symbols)              SYMBOLS=1 ;;
    --no-symbols)           SYMBOLS=0 ;;
    --probe)                PROBE=1 ;;
    --keep-going)           KEEP_GOING=1 ;;
    --help|-h)              sed -n '1,80p' "$0"; exit 0 ;;
    --*)                    die "unknown option $1" ;;
    *)                      break ;;
  esac
  shift
done

[ $# -ge 2 ] || die "usage: $0 [options] <name> <root>..."
NAME=$1; shift
ROOTS="$*"

case "$LINK" in none|binary) ;; *) die "--link must be none or binary" ;; esac

TREEDIR="$PROJECTDIR/build/trees/$NAME"
: "${IFACE_DIR:=$TREEDIR/interfaces}"
: "${OBJDIR:=$TREEDIR/obj}"
: "${REPORT:=$TREEDIR/break-report.txt}"
OBJROOT=$(dirname "$OBJDIR")
: "${BINARY:=$OBJROOT/$NAME}"

# A tool that is missing is a failure, not a reason to skip the step. scripts/
# quality-gate.sh once reported "Gate passed" in one second on a tree where 294 of
# 532 files did not type-check, because every step tested `command -v ooke` and the
# binary is named ooke-toke.
[ -x "$TOKE" ] || die "toke compiler not executable at $TOKE (set TOKE_DIR)"
[ -d "$OOKE_DIR/src" ] || die "ooke source not found at $OOKE_DIR/src (set OOKE_DIR)"

mkdir -p "$TREEDIR" "$(dirname "$REPORT")"

# ── one run of a target at a time ────────────────────────────────────────────
#
# Step 1 does `rm -rf` on the interface dir and the object dir. Two runs of the same
# target therefore delete each other's outputs mid-flight, and the result is not a
# clean failure: one run reported "198 succeeded, 20 failed" with 60
# module-interface-missing errors and then could not find a single object to link,
# because another worker had started scripts/build_loke.sh forty seconds earlier. That
# nearly went into a baseline as loke's real number.
#
# mkdir is the atomic test-and-set. The lock is waited for, not skipped: a build that
# quietly proceeds without it is the bug.
LOCK="$PROJECTDIR/build/trees/$NAME.lock"
mkdir -p "$PROJECTDIR/build/trees"
_waited=0
until mkdir "$LOCK" 2>/dev/null; do
  if [ "$_waited" -eq 0 ]; then
    echo "[$NAME] another build of this target holds $LOCK; waiting..." >&2
    if [ -f "$LOCK/pid" ] && ! kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then
      echo "[$NAME] the holder (pid $(cat "$LOCK/pid")) is gone; taking the lock" >&2
      rm -rf "$LOCK"
      continue
    fi
  fi
  _waited=$((_waited + 5))
  if [ "$_waited" -gt "${LOKE_BUILD_LOCK_TIMEOUT:-1800}" ]; then
    die "timed out after ${_waited}s waiting for $LOCK. If no build is running, rm -rf it."
  fi
  sleep 5
done
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM

: > "$REPORT"
FAILED=0
COMPILED=0

# Records a failure; never aborts the census. One module that cannot compile must not
# hide the state of the other 217.
compile_one() {
  _src="$1"; shift
  if "$TOKE" $TKCONFIG -I "$IFACE_DIR" "$@" "$_src" 2>>"$REPORT"; then
    COMPILED=$((COMPILED + 1))
  else
    FAILED=$((FAILED + 1))
    echo "COMPILE_FAIL $_src" >> "$REPORT"
    echo "  compile FAILED: $_src" >&2
  fi
}

modpath_of() { grep '^m=' "$1" | head -1 | sed 's/m=//; s/;//'; }

# toke mangles a module path by replacing '.' with '_' and appending the function
# name, so core.privacy.placeholder.restore is _core_privacy_placeholder_restore.
# The object file is named for the module part alone. scripts/symbol_census.py
# inverts this; keep the two in step.
buildname_of() { echo "$1" | tr '.' '_'; }

# The per-module link probe needs the toke C stdlib as an ARCHIVE so it links lazily.
# scripts/run_tests.sh builds exactly this archive at the same path and explains why
# -force_load is wrong here: it drags in every page handler, which need ooke's own
# objects, and turns a privacy unit test into a link against the whole application.
# Reuse its archive when it is there rather than building a second copy.
STDLIB_A="${LOKE_STDLIB_ARCHIVE:-/tmp/loke-tests/libtokestd.a}"
ensure_stdlib_archive() {
  if [ -f "$STDLIB_A" ]; then echo "$STDLIB_A"; return 0; fi
  echo "[$NAME] building $STDLIB_A (once) ..." >&2
  mkdir -p "$(dirname "$STDLIB_A")"
  _objdir="$(dirname "$STDLIB_A")/stdobj"
  rm -rf "$_objdir"; mkdir -p "$_objdir"
  _cf="-std=c99 -D_GNU_SOURCE -O1 -iquote $STDLIB -I$VENDOR/cmark/src -I$VENDOR/tomlc99 -I/opt/homebrew/include -Wno-implicit-function-declaration -Wno-pedantic -DTK_HAVE_OPENSSL"
  # One file at a time: the whole set at once is what exhausted memory in run_tests.sh.
  # The three roots are listed separately because a single find with -o clauses applies
  # its ! -name only to the first branch, which silently dropped tomlc99/toml.c and
  # left toml_parse undefined for anything that reads a config file.
  { find "$STDLIB" -name '*.c'
    find "$VENDOR/cmark/src" -name '*.c'
    echo "$VENDOR/tomlc99/toml.c"
  } | while read -r c; do
    case "$c" in *infer_stream.c|*cmark/src/main.c) continue ;; esac
    clang $_cf -c "$c" -o "$_objdir/$(echo "$c" | tr '/' '_').o" 2>/dev/null \
      || echo "  skipped (does not build): $c" >&2
  done
  ar rcs "$STDLIB_A" "$_objdir"/*.o 2>/dev/null
  [ -f "$STDLIB_A" ] || die "could not build $STDLIB_A; the link probe cannot run"
  echo "$STDLIB_A"
}

# ── Step 1: fresh interface dir, seeded with ooke's .tki ──────────────────────
#
# Rebuilt from scratch every run. They used to be left in place, and a stale nested
# tree from May survived four months of toolchain change: toke resolves loke's own -I
# lookups against FLAT dot-separated names (core.privacy.ner.tki), so the old
# core/privacy/ner.tki layout was never read at all. Every cross-module import
# resolved against nothing, which is why the build reported "module not found;
# available: ooke.handlers.tki" and a long tail of interface-disagrees-with-
# implementation errors that were really just absence.
#
# ooke's own interfaces are the exception and go in a nested ooke/ subdirectory —
# that is where toke looks for them, and it is the layout build_loke.sh has always
# used. Each tree gets its OWN interface dir: packages/moke/src/_handlers.tk and
# packages/browser/_handlers.tk both declare m=ooke.handlers, so one shared dir would
# have them silently overwrite each other.
echo "[$NAME] interfaces -> $IFACE_DIR"
rm -rf "$IFACE_DIR" "$OBJDIR" "$OBJROOT/main.ll" "$OBJROOT/main.ll.o" "$BINARY"
mkdir -p "$IFACE_DIR/ooke" "$OBJDIR"
for f in "$OOKE_DIR/src"/ooke.*.tki; do
  [ -f "$f" ] && cp "$f" "$IFACE_DIR/ooke/$(basename "$f" | sed 's/^ooke\.//')"
done

# ── Step 2: optional generated handler registry ───────────────────────────────
if [ -n "$GEN_HANDLERS" ]; then
  _pages=${GEN_HANDLERS%%:*}
  _out=${GEN_HANDLERS#*:}
  [ -x "$OOKE_DIR/scripts/gen_handlers.sh" ] \
    || die "ooke gen_handlers.sh not executable at $OOKE_DIR/scripts/gen_handlers.sh"
  "$OOKE_DIR/scripts/gen_handlers.sh" "$_pages" "$_out"
  # gen_handlers.sh is ooke's and emits no licence header. These files are tracked,
  # so the header is prepended here rather than upstream.
  if ! head -1 "$_out" | grep -q 'Copyright 2026 loke contributors'; then
    printf '(* Copyright 2026 loke contributors\n   SPDX-License-Identifier: Apache-2.0 *)\n\n%s' \
      "$(cat "$_out")" > "$_out.tmp"
    mv "$_out.tmp" "$_out"
  fi
fi

# ── Step 3: module order ─────────────────────────────────────────────────────
#
# A module's interface can only be emitted once the interfaces of its imports exist,
# and the import graph is not the alphabetical order a find|sort loop walks. Emitting
# alphabetically and repeating until the count stopped growing reached 33 of 179 and
# stalled: repetition cannot fix an ordering problem, only a shallow one.
MODULE_SRCS=$("$PROJECTDIR/scripts/module_order.py" $ROOTS 2>/dev/null) || true
[ -n "$MODULE_SRCS" ] || die "could not compute module order for roots: $ROOTS"

# The interface pass gets the tree's roots PLUS any --iface-root. That is how a small
# tree gets an honest count: packages/browser/src is 13 files and imports shared.log
# and twenty page.* modules, so without their interfaces its 13 files would report
# twenty "module not found" errors that are not defects in those 13 files at all.
# Only the tree's own roots are compiled, censused and linked.
IFACE_SRCS=$MODULE_SRCS
if [ -n "$IFACE_ROOTS" ]; then
  IFACE_SRCS=$("$PROJECTDIR/scripts/module_order.py" $ROOTS $IFACE_ROOTS 2>/dev/null) || true
  [ -n "$IFACE_SRCS" ] || die "could not compute module order for iface roots"
fi

if [ -n "$EXCLUDES" ]; then
  _keep=
  for _src in $MODULE_SRCS; do
    _drop=0
    for _ex in $EXCLUDES; do
      case "$_src" in *"$_ex") _drop=1 ;; esac
    done
    [ "$_drop" -eq 1 ] && { echo "[$NAME] excluded: $_src" >&2; continue; }
    _keep="$_keep$_src
"
  done
  MODULE_SRCS=$_keep
fi

NMODULES=$(echo "$MODULE_SRCS" | grep -c . || true)

# ── Step 4a: interface pass, in dependency order ─────────────────────────────
#
# --emit-llvm matters here and is not cosmetic. Without it toke compiles a BINARY,
# which requires a main function, so every library module failed with "E9020 no main
# function defined" and emitted no interface. That one missing flag was the whole
# reason only 33 of 179 interfaces appeared — it read as a dependency-order problem
# and was not one. --out is a DIRECTORY here, so toke names the .tki by module path
# (core.privacy.ner.tki); the .ll lands beside it and is ignored, because step 4b
# emits the IR that actually gets linked.
#
# Failures here are expected and silent: a module that cannot type-check still yields
# a usable signature list, and step 4b is where a real failure is reported.
NIFACE_SRCS=$(echo "$IFACE_SRCS" | grep -c . || true)
echo "[$NAME] emitting interfaces for $NIFACE_SRCS module(s) in dependency order"
echo "[$NAME]   ($NMODULES of them are this tree's own; the rest are --iface-root)"
for tkfile in $IFACE_SRCS; do
  "$TOKE" $TKCONFIG -I "$IFACE_DIR" --emit-interface --emit-llvm \
    --out "$IFACE_DIR" "$tkfile" >/dev/null 2>&1 || true
done
NIFACE=$(ls "$IFACE_DIR"/*.tki 2>/dev/null | wc -l | tr -d ' ')
echo "[$NAME]   $NIFACE of $NIFACE_SRCS interface(s) emitted"

# Page handlers get a second interface emission into the object dir. Kept because
# build_loke.sh has always done it and its census count includes these compiles.
mkdir -p "$OBJDIR"
if [ -n "$HANDLER_IFACE" ]; then
  echo "[$NAME] compiling page handlers..."
  for tkfile in $(find "$HANDLER_IFACE" -name '*.tk' -type f | sort); do
    has_handler=0
    grep -q 'f=get(' "$tkfile" && has_handler=1
    grep -q 'f=post(' "$tkfile" && has_handler=1
    [ "$has_handler" -eq 0 ] && continue
    compile_one "$tkfile" --emit-interface --emit-llvm \
      --out "$OBJDIR/$(buildname_of "$(modpath_of "$tkfile")")"
  done
fi

# Extra sources outside the roots: a generated handler registry, for instance.
for _extra in $EXTRAS; do
  _file=${_extra%%:*}
  _out=${_extra#*:}
  [ "$_out" = "$_extra" ] && _out=$(buildname_of "$(modpath_of "$_file")")
  echo "[$NAME] compiling $_file -> $_out"
  compile_one "$_file" --emit-interface --emit-llvm --out "$OBJDIR/$_out"
done

# ── Step 4b: compile census ──────────────────────────────────────────────────
echo "[$NAME] compiling modules..."
for tkfile in $MODULE_SRCS; do
  modpath=$(modpath_of "$tkfile")
  [ -z "$modpath" ] && continue
  compile_one "$tkfile" --emit-llvm --out "$OBJDIR/$(buildname_of "$modpath")"
done

# The entry point, if this target has one.
if [ "$LINK" = binary ]; then
  [ -n "$MAIN" ] || die "--link=binary needs --main=FILE"
  [ -f "$MAIN" ] || die "main not found: $MAIN"
  echo "[$NAME] compiling main $MAIN"
  mkdir -p "$OBJROOT"
  compile_one "$MAIN" --emit-llvm --out "$OBJROOT/main.ll"
fi

if [ -n "$LEGACY_REPORT" ]; then
  mkdir -p "$(dirname "$LEGACY_REPORT")"
  cp "$REPORT" "$LEGACY_REPORT"
fi

echo ""
echo "[$NAME] compile census: $COMPILED succeeded, $FAILED failed"

# ── Step 5: IR -> objects ────────────────────────────────────────────────────
#
# Done before the symbol census, not after, because the census reads .o files. A
# module whose IR does not assemble is reported, not skipped: clang exiting non-zero
# here has been mistaken for success before, because the loop's status was the status
# of the last iteration rather than of any particular file.
echo "[$NAME] compiling IR to object files..."
IRFAIL=0
for f in $(find "$OBJDIR" -type f ! -name '*.tki' ! -name '*.o' 2>/dev/null); do
  clang -c -x ir "$f" -o "$f.o" || { IRFAIL=$((IRFAIL + 1)); echo "  IR->obj FAILED: $f" >&2; }
done
if [ -f "$OBJROOT/main.ll" ]; then
  clang -c -x ir "$OBJROOT/main.ll" -o "$OBJROOT/main.ll.o" \
    || { IRFAIL=$((IRFAIL + 1)); echo "  IR->obj FAILED: $OBJROOT/main.ll" >&2; }
fi
[ "$IRFAIL" -gt 0 ] && echo "[$NAME] $IRFAIL object(s) did not assemble from IR" >&2

# ── Step 5a: undefined-symbol census (F10.23c) ───────────────────────────────
#
# An unknown method call is not checked at compile time; it becomes an undefined
# symbol at LINK time, and the default experience is a wall of "ld: Undefined
# symbols" that attributes nothing to any module. This runs before the link so the
# attribution exists whether or not the link is attempted — which is the only way a
# check-only tree gets the information at all.
SYMJSON="$TREEDIR/symbol-census.json"
if [ "$SYMBOLS" -eq 1 ]; then
  SYMARGS="--objdir $OBJDIR --json $SYMJSON"
  [ -f "$OBJROOT/main.ll.o" ] && SYMARGS="$SYMARGS --object $OBJROOT/main.ll.o"
  for d in $LINK_OBJDIRS; do SYMARGS="$SYMARGS --defines-objdir $d"; done
  # handlers.o is skipped for the same reason step 7 leaves it off the link line: the
  # APPLICATION supplies ooke.handlers, and treating ooke's placeholder as a definition
  # made the moke census report 1 undefined symbol where the link then found two.
  [ "$OOKE_OBJS" -eq 1 ] && SYMARGS="$SYMARGS --defines-objdir $OOKE_DIR/src/ooke --defines-skip handlers.o"
  for r in $ROOTS; do SYMARGS="$SYMARGS --source-root $r"; done
  if [ "$PROBE" -eq 1 ]; then
    SYMARGS="$SYMARGS --probe --stdlib-archive $(ensure_stdlib_archive)"
    [ "$OOKE_OBJS" -eq 1 ] && SYMARGS="$SYMARGS --probe-archive-dir $OOKE_DIR/src/ooke"
  elif [ -f "$STDLIB_A" ]; then
    # Used only to SUBTRACT the C runtime's definitions. It is not built here when it
    # is absent: that costs two minutes and only changes the c-runtime line, which
    # the census labels as unfiltered when the archive was not consulted.
    SYMARGS="$SYMARGS --stdlib-archive $STDLIB_A"
  fi
  "$PROJECTDIR/scripts/symbol_census.py" --tree "$NAME" $SYMARGS || true
fi

# --keep-going says "attempt the link anyway", not "call it a pass". Those were the
# same flag for one run of scripts/build_trees.sh and it reported src-legacy as
# "target OK" with 72 of 102 modules failing to compile, which is the same class of
# lie quality-gate.sh told when it reported "Gate passed" on a tree where 294 of 532
# files did not type-check.
if [ "$FAILED" -gt 0 ]; then
  echo "See $REPORT for diagnostics." >&2
  if [ "$KEEP_GOING" -eq 0 ]; then
    [ "$LINK" = binary ] && echo "Refusing to link an incomplete build." >&2
    exit 1
  fi
  [ "$LINK" = binary ] && echo "[$NAME] linking anyway (--keep-going); $FAILED module(s) are missing from it." >&2
fi

if [ "$LINK" = none ]; then
  echo "[$NAME] check-only target; no link requested."
  [ "$FAILED" -gt 0 ] && exit 1
  exit 0
fi

[ -f "$OBJROOT/main.ll.o" ] || die "no main object at $OBJROOT/main.ll.o; cannot link"
if [ "$OOKE_OBJS" -eq 1 ]; then
  for f in "$OOKE_DIR"/src/ooke/*; do
    [ -f "$f" ] || continue
    case "$f" in *.tki|*.o) continue ;; esac
    clang -c -x ir "$f" -o "$f.o"
  done
fi

# ── Step 7: link ─────────────────────────────────────────────────────────────
echo "[$NAME] linking $BINARY..."

OBJLIST=$(mktemp "${TMPDIR:-/tmp}/loke_obj.XXXXXX")
CLIST=$(mktemp "${TMPDIR:-/tmp}/loke_c.XXXXXX")
# Re-set, not added to: sh has one EXIT trap, so the lock has to be released here too
# or it outlives the run and every later build waits half an hour for a dead process.
trap 'rm -f "$OBJLIST" "$CLIST"; rm -rf "$LOCK"' EXIT INT TERM

# Explicit object dirs, not a single `find build -name '*.o'` sweep: with five
# targets writing objects under build/, one sweep would put moke's objects on loke's
# link line and duplicate every symbol in core.
echo "$OBJROOT/main.ll.o" > "$OBJLIST"
find "$OBJDIR" -name '*.o' >> "$OBJLIST"
for d in $LINK_OBJDIRS; do find "$d" -name '*.o' >> "$OBJLIST"; done
# Modules kept off the link line. packages/cli/src/main.tk, packages/mcp-broker/src/
# main.tk and packages/mcp-toke/src/main.tk each declare f=main, so all three emit a
# `_main` and the loke-cli link would fail on duplicate symbols. They are still
# compiled and still censused — the exclusion is of the OBJECT, not of the check.
for _nl in $NO_LINK; do
  grep -v "/$_nl\.o$" "$OBJLIST" > "$OBJLIST.f" || true
  mv "$OBJLIST.f" "$OBJLIST"
  echo "[$NAME] kept off the link line: $_nl" >&2
done
if [ "$OOKE_OBJS" -eq 1 ]; then
  find "$OOKE_DIR/src/ooke" -name '*.o' ! -name 'handlers.o' >> "$OBJLIST"
fi

# sys_glue.c and llm_tool.c are INCLUDED. They were excluded from build_loke.sh's
# first commit with no recorded reason, alongside infer_stream.c, and the omission
# cost the link: tk_sys_platform_w, tk_sys_isarm64_w, tk_sys_totalramgb_w,
# tk_sys_cpucount_w, tk_sys_diskfreegb_w, tk_sys_chipname_w and tk_sys_datadir_w are
# defined in sys_glue.c and nowhere else, and installer/detect, setup/wizard and
# pages/installer all call them. llm_tool.c was excluded the same way while
# llm_tool_glue.c was kept, so the glue's calls to llm_chatwithtools,
# llm_parse_tool_calls, llm_submitresult and llm_tool_result_msgs had no definitions.
# infer_stream.c stays out: it is the only one of the three that does not build here.
find "$STDLIB" -name '*.c' ! -name 'infer_stream.c' > "$CLIST"
find "$VENDOR/cmark/src" -name '*.c' ! -name 'main.c' >> "$CLIST"
echo "$VENDOR/tomlc99/toml.c" >> "$CLIST"

# No -Wl,-undefined,dynamic_lookup: undefined symbols must fail the link here rather
# than crash at runtime.
clang -std=c99 -D_GNU_SOURCE -O1 -iquote "$STDLIB" \
  -I"$VENDOR/cmark/src" -I"$VENDOR/tomlc99" \
  -I/opt/homebrew/include -L/opt/homebrew/lib \
  -Wno-implicit-function-declaration -Wno-pedantic -DTK_HAVE_OPENSSL \
  $(cat "$OBJLIST") \
  -x c $(cat "$CLIST") \
  -o "$BINARY" -lssl -lcrypto -lz -lm -lsqlite3 \
  -framework Security -framework CoreFoundation -lobjc

echo "[$NAME] done: $BINARY ($(du -h "$BINARY" | cut -f1))"
# A binary that links is still not a pass while modules are missing from it.
[ "$FAILED" -gt 0 ] && exit 1
exit 0
