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
mkdir -p "$IFACE_DIR/ooke"
for f in "$OOKE_DIR/src"/ooke.*.tki; do
  [ -f "$f" ] && cp "$f" "$IFACE_DIR/ooke/$(basename "$f" | sed 's/^ooke\.//')"
done

# Step 2: Generate handlers and main
"$OOKE_DIR/scripts/gen_handlers.sh" "$BROWSERDIR/pages" "$BROWSERDIR/_handlers.tk"

# Step 3: Generate _serve_main.tk
# NOTE: match arms use $ok/$err and serverun's final parameter is [str] as of
# ooke 2.0.0. Keep this in sync with $OOKE_DIR/src/ooke.serve.tki.
cat > "$BROWSERDIR/_serve_main.tk" << 'MAIN'
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

echo "Compiling core modules..."
for srcdir in "$PROJECTDIR/packages/core/src" "$PROJECTDIR/packages/shared/src" "extensions"; do
  [ -d "$srcdir" ] || continue
  for tkfile in $(find "$srcdir" -name '*.tk' -type f | sort); do
    modpath=$(grep '^m=' "$tkfile" | head -1 | sed 's/m=//; s/;//')
    [ -z "$modpath" ] && continue
    buildname=$(echo "$modpath" | tr '.' '_')
    compile_one "$tkfile" --emit-llvm --out "build/ooke/$buildname"
  done
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
