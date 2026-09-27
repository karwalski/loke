# Shared build helpers for run.sh (sourced). Needs TOKE_DIR and CLOG.
#
# build_direct SRC BIN [toke flags] : the normal invocation, toke --out BIN SRC.
# build_manual BIN MAIN [LIB...]    : for multi-module programs, and for programs whose
#   dependency list overflows toke's own 8192-byte clang source buffer (seen on toke 4a50b87
#   when the checkout lives at a long path and the program imports std.http). Emits a .tki
#   and IR per LIB, IR for MAIN, takes the C sources from --emit-deps (dropping any truncated
#   entry) and links with clang the way loke's scripts/build_test.sh does. Symbols still
#   undefined after that are located in src/stdlib/*.c and added (up to 6 rounds).
build_direct() {
  local src=$1 bin=$2; shift 2
  rm -f "$bin"
  "$TOKE_DIR/toke" --diag-text "$@" --out "$bin" "$src" >"$CLOG" 2>&1
}
build_manual() {
  local bin=$1 main=$2; shift 2
  local d; d=$(cd "$(dirname "$bin")" && pwd); rm -f "$bin"
  : >"$CLOG"
  local lls="" f
  for f in "$@"; do
    "$TOKE_DIR/toke" --diag-text --emit-interface --check -I "$d" "$f" >>"$CLOG" 2>&1 || return 1
    "$TOKE_DIR/toke" --diag-text -I "$d" --emit-llvm --out "$d/$(basename "$f" .tk).ll" "$f" >>"$CLOG" 2>&1 || return 1
    lls="$lls $d/$(basename "$f" .tk).ll"
  done
  "$TOKE_DIR/toke" --diag-text -I "$d" --emit-llvm --out "$d/main.ll" "$main" >>"$CLOG" 2>&1 || return 1
  ( cd "$TOKE_DIR" && ./toke -I "$d" --emit-deps "$main" 2>/dev/null ) > "$d/deps.raw"
  local srcs="$d/deps.src" flags
  : > "$srcs"
  sed '/^---/,$d' "$d/deps.raw" | while read -r f; do
    case "$f" in /*) p=$f ;; *) p=$TOKE_DIR/$f ;; esac
    [ -f "$p" ] && echo "$p" >> "$srcs"
  done
  flags=$(sed -n '/^---/,$p' "$d/deps.raw" | grep -E '^-[lLf]' | tr '\n' ' ')
  local extra="-I/opt/homebrew/include -L/opt/homebrew/lib -lm -lz -lpthread"
  case "$flags" in *-lssl*) extra="$extra -DTK_HAVE_OPENSSL -framework Security -framework CoreFoundation" ;; esac
  local i syms s hit
  for i in 1 2 3 4 5 6; do
    if xargs clang -std=c99 -D_GNU_SOURCE -O1 -w -iquote "$TOKE_DIR/src/stdlib" \
        -x ir $lls "$d/main.ll" -x c -o "$bin" $flags $extra < "$srcs" > "$d/link.log" 2>&1; then
      cat "$d/link.log" >> "$CLOG"; return 0
    fi
    syms=$(grep -o '"_[A-Za-z0-9_]*", referenced' "$d/link.log" | sed 's/^"_//; s/", referenced$//' | sort -u)
    [ -z "$syms" ] && break
    hit=0
    for s in $syms; do
      f=$(grep -l -E "^[A-Za-z_][A-Za-z0-9_ *]*[ *]$s\(" "$TOKE_DIR"/src/stdlib/*.c 2>/dev/null | head -1)
      if [ -n "$f" ] && ! grep -qx "$f" "$srcs"; then echo "$f" >> "$srcs"; hit=1; fi
    done
    [ $hit = 0 ] && break
  done
  cat "$d/link.log" >> "$CLOG"; return 1
}
# run_bin BIN [args] : runs with a 10 s alarm; sets RRC, RSIG, ROUT
run_bin() {
  local bin=$1; shift
  if [ ! -x "$bin" ]; then RRC=127; RSIG=""; ROUT="(no binary)"; return; fi
  ROUT=$(perl -e 'alarm 10; exec @ARGV or exit 127' "$bin" "$@" 2>&1); RRC=$?
  case $RRC in 129|130|131|132|133|134|135|136|137|138|139|140|141|142|143) RSIG=" (signal $((RRC-128)))";; *) RSIG="";; esac
}
