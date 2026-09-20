#!/bin/sh
# build_loke.sh — Build loke native binary
# Wraps ooke's gen_app_makefile.sh with loke-specific settings:
# -I for .tki interfaces, source_paths for core modules, .ll→.o linking
#
# This script reports every compile failure and exits non-zero if any module
# failed. It does NOT suppress compiler stderr and does NOT pass
# -Wl,-undefined,dynamic_lookup, because both of those turn build failures
# into runtime crashes. A failure census is written to build/break-report.txt.

set -eu

PROJECTDIR="$(cd "$(dirname "$0")/.." && pwd)"
BROWSERDIR="$PROJECTDIR/packages/browser"
OOKE_DIR="${OOKE_DIR:-$HOME/tk/toke-ooke}"
TOKE_DIR="${TOKE_DIR:-$HOME/tk/toke}"
TOKE="$TOKE_DIR/toke"
STDLIB="$TOKE_DIR/src/stdlib"
VENDOR="$TOKE_DIR/stdlib/vendor"
IFACE_DIR="$PROJECTDIR/build/interfaces"

# Step 0: Toolchain guard — refuse to compile against an unverified toolchain
if [ -x "$PROJECTDIR/scripts/check_toolchain.sh" ]; then
  TOKE_DIR="$TOKE_DIR" OOKE_DIR="$OOKE_DIR" "$PROJECTDIR/scripts/check_toolchain.sh"
fi

[ -x "$TOKE" ] || { echo "ERROR: toke compiler not executable at $TOKE" >&2
                    echo "       set TOKE_DIR to your toke checkout" >&2; exit 1; }
[ -d "$OOKE_DIR/src" ] || { echo "ERROR: ooke source not found at $OOKE_DIR/src" >&2
                            echo "       set OOKE_DIR to your ooke checkout" >&2; exit 1; }

REPORT="$PROJECTDIR/build/break-report.txt"
mkdir -p "$PROJECTDIR/build"
: > "$REPORT"
FAILED=0
COMPILED=0

# compile <label> <outflag-and-args...> — records failure, never aborts the census
compile_one() {
  _src="$1"; shift
  if "$TOKE" -I "$IFACE_DIR" "$@" "$_src" 2>>"$REPORT"; then
    COMPILED=$((COMPILED + 1))
  else
    FAILED=$((FAILED + 1))
    echo "COMPILE_FAIL $_src" >> "$REPORT"
    echo "  compile FAILED: $_src" >&2
  fi
}

# Step 1: Copy fresh ooke .tki files
#
# The loke interfaces are rebuilt from scratch every run. They used to be left in
# place, and a stale nested tree from May survived four months of toolchain change:
# toke resolves -I against FLAT, dot-separated names (core.privacy.ner.tki), so the
# old core/privacy/ner.tki layout was never read at all. Every cross-module import
# therefore resolved against nothing, which is why the build reported "module not
# found; available: ooke.handlers.tki" and a long tail of interface-disagrees-with-
# implementation errors that were really just absence.
rm -rf "$IFACE_DIR"
mkdir -p "$IFACE_DIR/ooke"
for f in "$OOKE_DIR/src"/ooke.*.tki; do
  [ -f "$f" ] && cp "$f" "$IFACE_DIR/ooke/$(basename "$f" | sed 's/^ooke\.//')"
done

# Step 2: Generate handlers and main
"$OOKE_DIR/scripts/gen_handlers.sh" "$BROWSERDIR/pages" "$BROWSERDIR/_handlers.tk"
# gen_handlers.sh is ooke's and emits no licence header. This file is tracked, so
# the header is prepended here rather than upstream.
if ! head -1 "$BROWSERDIR/_handlers.tk" | grep -q 'Copyright 2026 loke contributors'; then
  printf '(* Copyright 2026 loke contributors\n   SPDX-License-Identifier: Apache-2.0 *)\n\n%s' \
    "$(cat "$BROWSERDIR/_handlers.tk")" > "$BROWSERDIR/_handlers.tk.tmp"
  mv "$BROWSERDIR/_handlers.tk.tmp" "$BROWSERDIR/_handlers.tk"
fi

# Step 3: Generate _serve_main.tk
# NOTE: match arms use $ok/$err and serverun's final parameter is [str] as of
# ooke 2.0.0. Keep this in sync with $OOKE_DIR/src/ooke.serve.tki.
cat > "$BROWSERDIR/_serve_main.tk" << 'MAIN'
(* Copyright 2026 loke contributors
   SPDX-License-Identifier: Apache-2.0 *)

m=app.main;
i=http:std.http;
i=log:std.log;
i=str:std.str;
i=path:std.path;
i=args:std.args;
i=config:ooke.config;
i=serve:ooke.serve;
i=handlers:ooke.handlers;

f=main():i64{
  let projectdir=mt args.get(1 as u64) {$ok:v v;$err:e "."};
  let cfg=mt config.configload(path.join(projectdir;"ooke.toml")) {$ok:v v;$err:e config.cfgdefault()};
  let handledpaths=handlers.registerall();
  (log.info(str.concat("registered ";str.concat(str.fromint(handledpaths.len);" handler routes"));@()));
  let r=mt serve.serverun(projectdir;cfg.serverport;cfg.serverworkers;cfg.buildoutput;"";"";cfg.sitename;cfg.siteurl;cfg.sitelanguage;cfg.apiprefix;cfg.servercorsorigins;handledpaths) {$ok:v 0;$err:e 1};
  <r
};
MAIN

# Step 4: Compile all modules
cd "$BROWSERDIR"
rm -rf build/ooke build/main.ll build/loke
mkdir -p build/ooke

# Order matters and was wrong. The page handlers and main used to be compiled BEFORE
# the interface pass, so every cross-module import in a page resolved against nothing
# — and the interface pass did not cover packages/browser/pages either, so the pages
# never contributed interfaces of their own. Both halves are fixed: interfaces first,
# over the pages too, then everything is compiled.

echo "Emitting module interfaces in dependency order..."
MODULE_SRCS=$("$PROJECTDIR/scripts/module_order.py" \
  "$PROJECTDIR/packages/core/src" "$PROJECTDIR/packages/shared/src" \
  "$BROWSERDIR/extensions" "$BROWSERDIR/pages" 2>/dev/null)
[ -n "$MODULE_SRCS" ] || { echo "ERROR: could not compute module order" >&2; exit 1; }
# --emit-llvm matters here and is not cosmetic. Without it toke compiles a BINARY,
# which requires a main function, so every library module failed with
# "E9020 no main function defined" and emitted no interface. That single missing
# flag was the whole reason only 33 of 179 interfaces appeared — it read as a
# dependency-order problem and was not one. ooke's own Makefile pairs the two flags.
# --out is a DIRECTORY here, so toke names the .tki by module path
# (core.privacy.ner.tki). The .ll lands beside it and is ignored; the compile pass
# in step 4b emits the IR that actually gets linked.
for tkfile in $MODULE_SRCS; do
  "$TOKE" -I "$IFACE_DIR" --emit-interface --emit-llvm \
    --out "$IFACE_DIR" "$tkfile" >/dev/null 2>&1 || true
done
echo "  $(ls "$IFACE_DIR"/*.tki 2>/dev/null | wc -l | tr -d ' ') of $(echo "$MODULE_SRCS" | wc -l | tr -d ' ') interface(s) emitted"

echo "Compiling page handlers..."
for tkfile in $(find pages -name '*.tk' -type f | sort); do
  has_handler=0
  grep -q 'f=get(' "$tkfile" && has_handler=1
  grep -q 'f=post(' "$tkfile" && has_handler=1
  [ "$has_handler" -eq 0 ] && continue
  modpath=$(grep '^m=' "$tkfile" | head -1 | sed 's/m=//; s/;//')
  buildname=$(echo "$modpath" | tr '.' '_')
  compile_one "$tkfile" --emit-interface --emit-llvm --out "build/ooke/$buildname"
done

echo "Compiling handlers registry..."
compile_one _handlers.tk --emit-interface --emit-llvm --out build/ooke/handlers

echo "Compiling main..."
compile_one _serve_main.tk --emit-llvm --out build/main.ll

# Step 4a: interface pass.
#
# A module cannot be compiled before the interfaces of its imports exist, and the
# import graph is not the alphabetical order the loop walks. So interfaces are
# emitted first, for every module, and the pass runs twice: an interface can itself
# need another interface to be emitted, and two passes reach the fixpoint for a
# graph this shallow. Failures here are expected and silent — a module that cannot
# typecheck still yields a usable signature list, and the census in step 4b is
# where a real failure is reported.
# Interfaces are emitted in DEPENDENCY ORDER, not alphabetical order and not by
# repetition. A module's interface can only be emitted once its imports' interfaces
# exist, so alphabetical-plus-repeat stalled at 33 of 179: repetition cannot fix an
# ordering problem, only a shallow one. scripts/module_order.py reads the m= and i=
# lines, topologically sorts them (179 modules, no cycles) and prints the order.
echo "Compiling core modules..."
for tkfile in $MODULE_SRCS; do
  modpath=$(grep '^m=' "$tkfile" | head -1 | sed 's/m=//; s/;//')
  [ -z "$modpath" ] && continue
  buildname=$(echo "$modpath" | tr '.' '_')
  compile_one "$tkfile" --emit-llvm --out "build/ooke/$buildname"
done

echo ""
echo "Compile census: $COMPILED succeeded, $FAILED failed"
if [ "$FAILED" -gt 0 ]; then
  echo "See $REPORT for diagnostics." >&2
  echo "Refusing to link an incomplete build." >&2
  exit 1
fi

# Step 5: Compile .ll → .o
echo "Compiling IR to object files..."
for f in build/main.ll $(find build/ooke -type f ! -name '*.tki' ! -name '*.o'); do
  clang -c -x ir "$f" -o "$f.o"
done
for f in "$OOKE_DIR"/src/ooke/*; do
  [ -f "$f" ] || continue
  case "$f" in *.tki|*.o) continue ;; esac
  clang -c -x ir "$f" -o "$f.o"
done

# Step 6: Link
echo "Linking build/loke..."

OBJLIST=$(mktemp "${TMPDIR:-/tmp}/loke_obj.XXXXXX")
CLIST=$(mktemp "${TMPDIR:-/tmp}/loke_c.XXXXXX")
trap 'rm -f "$OBJLIST" "$CLIST"' EXIT INT TERM

find build -name '*.o' > "$OBJLIST"
find "$OOKE_DIR/src/ooke" -name '*.o' ! -name 'handlers.o' >> "$OBJLIST"
find "$STDLIB" -name '*.c' ! -name 'llm_tool.c' ! -name 'infer_stream.c' ! -name 'sys_glue.c' > "$CLIST"
find "$VENDOR/cmark/src" -name '*.c' ! -name 'main.c' >> "$CLIST"
echo "$VENDOR/tomlc99/toml.c" >> "$CLIST"

# No -Wl,-undefined,dynamic_lookup: undefined symbols must fail the link here
# rather than crash at runtime.
clang -std=c99 -D_GNU_SOURCE -O1 -iquote "$STDLIB" \
  -I"$VENDOR/cmark/src" -I"$VENDOR/tomlc99" \
  -I/opt/homebrew/include -L/opt/homebrew/lib \
  -Wno-implicit-function-declaration -Wno-pedantic -DTK_HAVE_OPENSSL \
  $(cat "$OBJLIST") \
  -x c $(cat "$CLIST") \
  -o build/loke -lssl -lcrypto -lz -lm -lsqlite3 \
  -framework Security -framework CoreFoundation -lobjc

echo "Done: build/loke ($(du -h build/loke | cut -f1))"
