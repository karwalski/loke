#!/usr/bin/env bash
# run.sh — rerun loke's upstream toke reproducers T-1..T-30 (+ O-1) against one toke checkout.
#
#   TOKE_DIR=/path/to/toke ./run.sh            all issues
#   TOKE_DIR=/path/to/toke ./run.sh T-13 T-20  selected issues
#
# TOKE_DIR must contain the built `toke` binary, src/stdlib and stdlib/*.tki.
# Prints one line per issue:  ID | VERDICT | observed outcome
# VERDICT is computed from the EXPECTED stated in each repro's header comment:
#   DEFECT   the defect as filed (or a still-wrong variant) was observed
#   OK       the expected behaviour was observed
#   note     no automatic verdict; read the observed text
# Build products go to $WORK (default: ./.work/<toke short commit>); sources are never modified.
# O-1 compiles ooke v3.0.0-rc.1 src/store.tk (copied into O-1/) and needs no ooke checkout.
# T-15 starts a throwaway python3 HTTP server on 127.0.0.1:47913 and kills it by PID.

set -u
export LC_ALL=C
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${TOKE_DIR:?set TOKE_DIR to a toke checkout}"
TOKE_DIR="$(cd "$TOKE_DIR" && pwd)"
[ -x "$TOKE_DIR/toke" ] || { echo "no toke binary at $TOKE_DIR/toke" >&2; exit 2; }
REV=$(git -C "$TOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
WORK="${WORK:-$HERE/.work/$REV}"
mkdir -p "$WORK"
export TOKE_DIR
# shellcheck source=lib.sh
source "$HERE/lib.sh"

one() { tr '\n' ' ' | sed 's/  */ /g; s/ $//' | cut -c1-"${2:-220}"; }
firsterr() { grep -m1 -E '^(error|Undefined symbols|clang: error|ld:|.*error:)' "$1" | cut -c1-200; }
line() { printf '%-5s | %-6s | %s\n' "$1" "$2" "$3"; }

# prep ID : fresh work dir for the issue, sets W and CLOG
prep() { W="$WORK/$1"; rm -rf "$W"; mkdir -p "$W"; CLOG="$W/compile.log"; export CLOG; }

# std ID FILE [runargs] : direct compile + run; sets CRC RRC RSIG ROUT; prints nothing
std() {
  local id=$1 f=$2; shift 2
  cp "$HERE/$id/$f" "$W/"
  ( cd "$W" && build_direct "$f" "$W/bin" ); CRC=$?
  if [ $CRC -eq 0 ]; then ( cd "$W" && run_bin "$W/bin" "$@"; printf '%s\n%s\n%s' "$RRC" "$RSIG" "$ROUT" ) > "$W/run.out"
    RRC=$(sed -n 1p "$W/run.out"); RSIG=$(sed -n 2p "$W/run.out"); ROUT=$(sed -n '3,$p' "$W/run.out")
  else RRC=""; RSIG=""; ROUT=""; fi
}
outcome() {
  if [ "$CRC" != 0 ]; then echo "compile rc=$CRC: $(firsterr "$CLOG")"
  else echo "exit=$RRC$RSIG${ROUT:+ out: $(printf '%s' "$ROUT" | one x 160)}"; fi
}

t01() { prep T-01; std T-01 repro.tk
  [ "$CRC" = 0 ] && [ "$RRC" = 10 ] && v=OK || v=DEFECT; line T-1 $v "$(outcome)"; }

t02() { prep T-02; std T-02 repro.tk; local a; a=$(outcome)
  if [ "$CRC" != 0 ] && grep -q 'Terminator found' "$CLOG"; then v=DEFECT
  elif [ "$CRC" != 0 ] && grep -q '^error\[E' "$CLOG"; then v=OK; else v=note; fi
  std T-02 field.tk; line T-2 $v "i64 subject: $a || field subject: $(outcome) (expected exit 33)"; }

t03() { prep T-03; std T-03 repro.tk
  [ "$CRC" = 0 ] && [ "$RRC" = 2 ] && v=OK || v=DEFECT; line T-3 $v "$(outcome)"; }

t04() { prep T-04; std T-04 repro.tk
  grep -q 'E4033\|E3011' "$CLOG" && v=OK || v=DEFECT; line T-4 $v "$(outcome)"; }

t05() { prep T-05; std T-05 repro.tk; local a=$(outcome) ac=$CRC ar=$RRC
  grep -q 'void type only allowed' "$CLOG" && v=DEFECT || v=OK
  std T-05 ok0.tk; grep -q 'void type only allowed' "$CLOG" && v=DEFECT
  line T-5 $v "filed \$ok(void): $a || \$ok(0): $(outcome)"; }

t06() { prep T-06; std T-06 repro.tk
  [ "$CRC" = 0 ] && [ "$RRC" = 57 ] && v=OK || v=DEFECT
  local w=""; grep -q W3013 "$CLOG" && w=" [W3013 shadow warning emitted]"
  line T-6 $v "$(outcome)$w"; }

t07() { prep T-07; std T-07 repro.tk
  grep -q 'Undefined symbols' "$CLOG" && v=DEFECT || v=OK; line T-7 $v "$(outcome)"; }

t08() { prep T-08; cp "$HERE/T-08/"*.tk "$W/"
  ( cd "$W" && "$TOKE_DIR/toke" --emit-interface --check ty.tk >/dev/null 2>&1
    "$TOKE_DIR/toke" --diag-text -I . --lint --fix repro.tk > fix.log 2>&1; echo "fixrc=$?" >> fix.log
    "$TOKE_DIR/toke" --diag-text -I . --check repro.tk > after.log 2>&1; echo $? > after.rc )
  local removed=no; grep -q '^i=t:ty;' "$W/repro.tk" || removed=yes
  [ $removed = yes ] && v=DEFECT || v=OK
  line T-8 $v "lint --fix: $(grep -m1 -E 'fixed|no lint|auto-fixed' "$W/fix.log" | cut -c1-90); import removed=$removed; --check after fix rc=$(cat "$W/after.rc") $(firsterr "$W/after.log")"; }

t09() { prep T-09; std T-09 repro.tk
  if printf '%s' "$ROUT" | grep -q '^s: a b$'; then v=DEFECT; else v=OK; fi
  line T-9 $v "$(outcome)"; }

t10() { prep T-10; std T-10 repro.tk; local a=$(outcome)
  local n; n=$(grep -c '"name": *"http.post"' "$TOKE_DIR/stdlib/http.tki")
  cp "$HERE/T-10/client2.tk" "$W/"; build_manual "$W/b2" "$W/client2.tk"; local c2=$?; run_bin "$W/b2" --allow-net
  v=note; line T-10 $v "http.post entries in http.tki=$n; 4-arg client call: $a || 2-arg http.post(url;body): build rc=$c2 exit=$RRC (it registers a route; nothing is sent)"; }

t11() { prep T-11; std T-11 repro.tk; local a=$(outcome)
  std T-11 tki_arity.tk
  line T-11 note "impl-arity calls: $a || .tki-arity calls: $(outcome)"; }

t12() { prep T-12; local miss=""
  for n in json.getarr str.padright process.spawndetached file.listglob; do
    grep -q "\"$n\"" "$TOKE_DIR/stdlib/${n%%.*}.tki" || miss="$miss $n"; done
  std T-12 repro.tk
  printf '%s' "$ROUT" | grep -q 'getregulations len=0' && v=DEFECT || v=OK
  line T-12 $v "missing from .tki:${miss:- none}; $(outcome | LC_ALL=C tr -c '[:print:]\n' '?')"; }

t13() { prep T-13; std T-13 repro.tk; local a=$(outcome) ac=$CRC ar=$RRC
  std T-13 field.tk; local b=$(outcome)
  { [ "$ac" = 0 ] && [ "$ar" -ge 128 ]; } || { [ "$CRC" = 0 ] && [ "$RRC" -ge 128 ]; } && v=DEFECT || v=OK
  line T-13 $v "mut.\$internal: $a || struct field l:\$internal: $b"; }

t14() { prep T-14; std T-14 repro.tk
  [ "$RRC" = 11 ] && v=OK || v=DEFECT; line T-14 $v "$(outcome) (expected 11; 1 = returned sum != identical local)"; }

t15() { prep T-15; cp "$HERE/T-15/"*.tk "$W/"
  build_manual "$W/b" "$W/repro.tk"; run_bin "$W/b" --allow-net; local a="exit=$RRC$RSIG"
  build_manual "$W/b1" "$W/onearg.tk"; run_bin "$W/b1" --allow-net; local b="$ROUT"
  local live="(python3 unavailable)"
  if command -v python3 >/dev/null; then
    sed 's/127.0.0.1:1/127.0.0.1:47913/' "$W/repro.tk" > "$W/live.tk"
    build_manual "$W/bl" "$W/live.tk"
    python3 -c '
import http.server,socketserver
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        open("'"$W"'/hits","a").write(self.path+"\n"); self.send_response(200); self.send_header("Content-Length","2"); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self,*a): pass
socketserver.TCPServer(("127.0.0.1",47913),H).serve_forever()' & local pid=$!
    sleep 1; run_bin "$W/bl" --allow-net; kill $pid 2>/dev/null; wait $pid 2>/dev/null
    live="exit=$RRC, requests received=$( [ -f "$W/hits" ] && wc -l < "$W/hits" | tr -d ' ' || echo 0)"
  fi
  line T-15 note "closed port, mt http.get(client;path): $a | same against a live server: $live | http.get(url) closed port: $b"; }

t16() { prep T-16; std T-16 repro.tk
  grep -q "no member 'mockreq'" "$CLOG" && v=DEFECT || v=OK; line T-16 $v "$(outcome)"; }

t17() { prep T-17; std T-17 repro.tk
  printf '%s' "$ROUT" | grep -q 'parse  a=\[xyz\]' && v=OK || v=DEFECT; line T-17 $v "$(outcome)"; }

t18() { prep T-18; std T-18 repro.tk
  [ "$RRC" = 77 ] && v=OK || v=DEFECT; line T-18 $v "$(outcome) (expected 77; 57 = first arm always)"; }

t19() { prep T-19; std T-19 repro.tk; local a=$(outcome)
  grep -q E4071 "$CLOG" && v=OK || v=DEFECT; std T-19 struct.tk; grep -q E4071 "$CLOG" || v=DEFECT
  line T-19 $v "sum: $a || struct: $(outcome)"; }

t20() { prep T-20; cp "$HERE/T-20/"*.tk "$W/"
  build_manual "$W/bin" "$W/repro.tk" "$W/lib.tk"; CRC=$?; run_bin "$W/bin"
  [ "$RRC" = 55 ] && v=OK || v=DEFECT
  line T-20 $v "build rc=$CRC exit=$RRC$RSIG (expected 55; tens digit = cross-module value/10) decl: $(grep -m1 'declare.*lib_f64abs' "$W/main.ll")"; }

t21() { prep T-21; std T-21 repro.tk; local a; a=$(outcome)
  printf '%s' "$ROUT" | grep -q 'interp=\([0-9]*\) concat=\1 ' && v=OK || v=DEFECT
  local h=$(( ${#HOME} + 2 ))
  std T-21 nolink.tk
  line T-21 $v "expected every length $h: $a || std.homedir without importing std.process: $(outcome)"; }

t22() { prep T-22; std T-22 repro.tk --allow-all
  printf '%s' "$ROUT" | grep -q 'zero: ok 0' && v=OK || v=DEFECT; line T-22 $v "$(outcome)"; }

t23() { prep T-23; std T-23 repro.tk
  { [ "$CRC" = 0 ] && [ "$RRC" != 8 ]; } && v=DEFECT || v=OK; line T-23 $v "$(outcome)"; }

t24() { prep T-24; std T-24 repro.tk
  [ "$CRC" = 0 ] && [ "$RRC" != 3 ] && v=DEFECT || v=OK; line T-24 $v "$(outcome) (expected 3 or a type error)"; }

t25() { prep T-25; cp "$HERE/T-25/"*.tk "$W/"
  ( cd "$W" && "$TOKE_DIR/toke" --emit-interface --check big.tk >/dev/null 2>&1
    "$TOKE_DIR/toke" --diag-text -I . --check repro.tk > check.log 2>&1; echo $? > check.rc
    "$TOKE_DIR/toke" --diag-text -I . --emit-llvm --out r.ll repro.tk > "$CLOG" 2>&1; echo $? > ll.rc
    "$TOKE_DIR/toke" --diag-text -I . --max-funcs=200 --emit-llvm --out r2.ll repro.tk > mf.log 2>&1; echo $? > mf.rc )
  grep -q 'too many functions$' "$CLOG" && v=DEFECT || v=OK
  line T-25 $v "--check rc=$(cat "$W/check.rc"); --emit-llvm rc=$(cat "$W/ll.rc"): $(firsterr "$CLOG") (x$(grep -c E9010 "$CLOG")); with --max-funcs=200 rc=$(cat "$W/mf.rc")"; }

t26() { prep T-26; std T-26 repro.tk; local a=$(outcome)
  grep -q "use \`==\` for equality" "$CLOG" && v=DEFECT || v=OK
  std T-26 applied_advice.tk; local w=""; grep -qE '^(warning|error)' "$CLOG" && w=" [diagnosed]"
  [ "$CRC" = 0 ] && [ "$RRC" = 1 ] && v=DEFECT
  line T-26 $v "x.a=9: $a || advice applied x.a==9: $(outcome)$w"; }

t27() { prep T-27; std T-27 repro.tk; local a=$(outcome)
  ( cd "$W" && "$TOKE_DIR/toke" --emit-llvm --out r.ll repro.tk > ll.log 2>&1; echo $? > ll.rc )
  local n; n=$(grep -c 'define.*survived' "$W/r.ll" 2>/dev/null); n=${n:-0}
  sed 's/COUNT(\*)/COUNT/' "$HERE/T-27/repro.tk" > "$W/control.tk"
  ( cd "$W" && build_direct control.tk "$W/cbin" && run_bin "$W/cbin"; echo "$RRC" > c.rc )
  [ "$n" = 0 ] && v=DEFECT || v=OK
  line T-27 $v "$a || --emit-llvm rc=$(cat "$W/ll.rc"), survived defined in IR: $n || control without the paren-star: exit=$(cat "$W/c.rc")"; }

t28() { prep T-28; std T-28 repro.tk
  { [ "$CRC" = 0 ] && [ "$RRC" != 1 ]; } && v=DEFECT || v=OK; line T-28 $v "$(outcome)"; }

t29() { prep T-29; std T-29 repro.tk
  grep -qi "reserved\|keyword" "$CLOG" && v=OK || v=DEFECT; line T-29 $v "$(outcome)"; }

t30() { prep T-30; cp "$HERE/T-30/repro.tk" "$W/"
  ( cd "$W" && build_direct repro.tk "$W/bin" ); CRC=$?
  ( cd "$W" && run_bin "$W/bin" --allow-all; printf '%s\n%s' "$RRC" "$ROUT" > run.out ); ROUT=$(sed -n '2,$p' "$W/run.out"); RRC=$(sed -n 1p "$W/run.out")
  printf '%s' "$ROUT" | grep -q 'ta-after-b=ok' && v=OK || v=DEFECT; line T-30 $v "$(outcome)"; }

o01() { prep O-1; cp "$HERE/O-1/store.tk" "$HERE/O-1/tkc.toml" "$HERE/O-1/min.tk" "$W/"
  ( cd "$W" && "$TOKE_DIR/toke" --diag-text --emit-llvm --out store.ll store.tk > "$CLOG" 2>&1; echo $? > rc )
  local rc; rc=$(cat "$W/rc")
  [ "$rc" = 0 ] && v=OK || v=DEFECT
  line O-1 $v "ooke v3.0.0-rc.1 src/store.tk --emit-llvm rc=$rc $(grep -E '^error|^ -->' "$CLOG" | one x 300)"; }

ALL="T-1 T-2 T-3 T-4 T-5 T-6 T-7 T-8 T-9 T-10 T-11 T-12 T-13 T-14 T-15 T-16 T-17 T-18 T-19 T-20 T-21 T-22 T-23 T-24 T-25 T-26 T-27 T-28 T-29 T-30 O-1"
echo "toke: $TOKE_DIR ($REV)   work: $WORK"
for id in ${*:-$ALL}; do
  case $id in
    O-1) o01 ;;
    T-*) n=${id#T-}; fn=$(printf 't%02d' "$((10#$n))"); declare -f "$fn" >/dev/null && "$fn" || echo "$id | ?      | no such repro" ;;
    *) echo "$id | ?      | unknown id" ;;
  esac
done
