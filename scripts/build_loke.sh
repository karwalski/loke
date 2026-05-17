#!/bin/sh
# build_loke.sh — Build loke native binary
# Wraps ooke's gen_app_makefile.sh with loke-specific settings:
# -I for .tki interfaces, source_paths for core modules, .ll→.o linking

set -e

PROJECTDIR="$(cd "$(dirname "$0")/.." && pwd)"
BROWSERDIR="$PROJECTDIR/packages/browser"
OOKE_DIR="${OOKE_DIR:-/Users/matthew.watt/tk/toke-ooke}"
TOKE_DIR="${TOKE_DIR:-/Users/matthew.watt/tk/toke}"
TOKE="$TOKE_DIR/toke"
STDLIB="$TOKE_DIR/src/stdlib"
VENDOR="$TOKE_DIR/stdlib/vendor"
IFACE_DIR="$PROJECTDIR/build/interfaces"

# Step 1: Copy fresh ooke .tki files
mkdir -p "$IFACE_DIR/ooke"
for f in "$OOKE_DIR/src"/ooke.*.tki; do
  [ -f "$f" ] && cp "$f" "$IFACE_DIR/ooke/$(basename "$f" | sed 's/^ooke\.//')"
done

# Step 2: Generate handlers and main
"$OOKE_DIR/scripts/gen_handlers.sh" "$BROWSERDIR/pages" "$BROWSERDIR/_handlers.tk"

# Step 3: Generate _serve_main.tk
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
  let count=args.count() as i64;
  let projectdir=mt args.get(1 as u64) {Ok:v v;Err:e "."};
  let cfg=mt config.configload(path.join(projectdir;"ooke.toml")) {Ok:v v;Err:e config.cfgdefault()};
  let handledpaths=handlers.registerall();
  (log.info(str.concat("registered ";str.concat(str.fromint(handledpaths.len);" handler routes"));@()));
  let r=mt serve.serverun(projectdir;cfg.serverport;cfg.serverworkers;cfg.buildoutput;"";"";cfg.sitename;cfg.siteurl;cfg.sitelanguage;cfg.apiprefix;cfg.servercorsorigins;handledpaths) {Ok:v 0;Err:e 1};
  <r
};
MAIN

# Step 4: Compile all modules
cd "$BROWSERDIR"
rm -rf build/ooke build/main.ll build/loke
mkdir -p build/ooke

TKC_IFLAGS="-I $IFACE_DIR"

echo "Compiling page handlers..."
for tkfile in $(find pages -name '*.tk' -type f | sort); do
  has_handler=0
  grep -q 'f=get(' "$tkfile" 2>/dev/null && has_handler=1
  grep -q 'f=post(' "$tkfile" 2>/dev/null && has_handler=1
  [ "$has_handler" -eq 0 ] && continue
  modpath=$(grep '^m=' "$tkfile" | head -1 | sed 's/m=//; s/;//')
  buildname=$(echo "$modpath" | tr '.' '_')
  $TOKE $TKC_IFLAGS --emit-interface --emit-llvm --out "build/ooke/$buildname" "$tkfile" 2>/dev/null || true
done

echo "Compiling handlers registry..."
$TOKE $TKC_IFLAGS --emit-interface --emit-llvm --out build/ooke/handlers _handlers.tk 2>/dev/null || true

echo "Compiling main..."
$TOKE $TKC_IFLAGS --emit-llvm --out build/main.ll _serve_main.tk 2>/dev/null || true

echo "Compiling core modules..."
for srcdir in "$PROJECTDIR/packages/core/src" "$PROJECTDIR/packages/shared/src" "$PROJECTDIR/src/browser" "extensions"; do
  [ -d "$srcdir" ] || continue
  for tkfile in $(find "$srcdir" -name '*.tk' -type f 2>/dev/null | sort); do
    modpath=$(grep '^m=' "$tkfile" | head -1 | sed 's/m=//; s/;//')
    [ -z "$modpath" ] && continue
    buildname=$(echo "$modpath" | tr '.' '_')
    $TOKE $TKC_IFLAGS --emit-llvm --out "build/ooke/$buildname" "$tkfile" 2>/dev/null || true
  done
done

# Step 5: Compile .ll → .o
echo "Compiling IR to object files..."
for f in build/main.ll $(find build/ooke -type f ! -name '*.tki' ! -name '*.o'); do
  clang -c -x ir "$f" -o "$f.o" 2>/dev/null || true
done
for f in $OOKE_DIR/src/ooke/*; do
  [ -f "$f" ] || continue
  echo "$f" | grep -q '\.tki$' && continue
  echo "$f" | grep -q '\.o$' && continue
  clang -c -x ir "$f" -o "$f.o" 2>/dev/null || true
done

# Step 6: Link
echo "Linking build/loke..."

# Build file lists for linker (using temp response files to avoid arg length issues)
find build -name '*.o' > /tmp/loke_obj.txt
find "$OOKE_DIR/src/ooke" -name '*.o' ! -name 'handlers.o' >> /tmp/loke_obj.txt
find "$STDLIB" -name '*.c' ! -name 'llm_tool.c' ! -name 'infer_stream.c' ! -name 'sys_glue.c' > /tmp/loke_c.txt
find "$VENDOR/cmark/src" -name '*.c' ! -name 'main.c' >> /tmp/loke_c.txt
echo "$VENDOR/tomlc99/toml.c" >> /tmp/loke_c.txt

clang -std=c99 -D_GNU_SOURCE -O1 -iquote "$STDLIB" \
  -I"$VENDOR/cmark/src" -I"$VENDOR/tomlc99" \
  -I/opt/homebrew/include -L/opt/homebrew/lib \
  -Wno-implicit-function-declaration -Wno-pedantic -DTK_HAVE_OPENSSL \
  $(cat /tmp/loke_obj.txt) \
  -x c $(cat /tmp/loke_c.txt) \
  -o build/loke -lssl -lcrypto -lz -lm -lsqlite3 \
  -framework Security -framework CoreFoundation -lobjc \
  -Wl,-undefined,dynamic_lookup

echo "Done: build/loke ($(du -h build/loke | cut -f1))"
