#!/usr/bin/env bash
# run.sh — loke's 2026-11-15 upstream reproducers, against one toke checkout.
#
#   TOKE_DIR=/path/to/toke ./run.sh                  every item
#   TOKE_DIR=/path/to/toke ./run.sh T-65 T-67        selected items
#   TOKE_DIR=/path/to/toke ./run.sh RW               only the 2026-09-27 rewrites (rewrites/)
#
# TOKE_DIR must contain the built `toke` binary and its stdlib. No ooke is needed.
# Prints one line per item:  ID | VERDICT | observed outcome
# VERDICT is computed from the EXPECTED stated in each reproducer's header comment:
#   DEFECT   the defect as filed was observed
#   OK       the expected behaviour was observed
#   OPEN     an open upstream ask: the behaviour that motivates it was observed (T-59,
#            127.319, 138.32); it turns OK when the ask lands
#   note     no automatic verdict; read the observed text
# Build products go to $WORK (default: $TMPDIR/loke-repro-2026-11-15/<toke short commit>), never
# into this directory. Servers bind 127.0.0.1 ports 47990-47999 only and are stopped by PID:
# T-64 starts T-64/server.py on 47990-47993 and takes about 65 seconds (two 30 s read
# timeouts); RW starts rewrites/recorder.py on 47993, 47995 and 47996 and binds 47997 (T-43).
# Nothing is sent off the machine. T-67 deliberately crashes its probe (SIGSEGV), which is the
# defect; it spawns /usr/bin/true and waits on nothing else.

set -u
export LC_ALL=C
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${TOKE_DIR:?set TOKE_DIR to a toke checkout}"
TOKE_DIR="$(cd "$TOKE_DIR" && pwd)"
[ -x "$TOKE_DIR/toke" ] || { echo "no toke binary at $TOKE_DIR/toke" >&2; exit 2; }
REV=$(git -C "$TOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
WORK="${WORK:-${TMPDIR:-/tmp}/loke-repro-2026-11-15/$REV}"
mkdir -p "$WORK"
export TOKE_DIR
# shellcheck source=lib.sh
source "$HERE/lib.sh"

one() { tr '\n' ' ' | sed 's/  */ /g; s/ $//' | cut -c1-"${1:-220}"; }
firsterr() { grep -m1 -E '^(error|Undefined symbols|clang: error|ld:|.*error:)' "$1" | cut -c1-200; }
line() { printf '%-7s | %-6s | %s\n' "$1" "$2" "$3"; }

prep() { W="$WORK/$1"; rm -rf "$W"; mkdir -p "$W"; CLOG="$W/compile.log"; export CLOG; }

# std ID FILE [runargs] : direct compile + run of one file; sets CRC RRC RSIG ROUT
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
  else echo "exit=$RRC$RSIG${ROUT:+ out: $(printf '%s' "$ROUT" | one 200)}"; fi
}
# chk ID FILE : toke --check of one file already copied into $W; sets KRC, KLOG
chk() { local f=$2; KLOG="$W/check-$f.log"
  ( cd "$W" && "$TOKE_DIR/toke" --diag-text --check "$f" > "$KLOG" 2>&1 ); KRC=$?; }

t64() { prep T-64; cp "$HERE/T-64/repro.tk" "$W/"
  ( cd "$W" && build_direct repro.tk "$W/bin" ); CRC=$?
  if [ "$CRC" != 0 ]; then line T-64 note "$(outcome)"; return; fi
  python3 -I "$HERE/T-64/server.py" > "$W/server.log" 2>&1 & local pid=$!
  sleep 1
  ROUT=$(cd "$W" && perl -e 'alarm 150; exec @ARGV or exit 127' "$W/bin" --allow-net 2>&1); RRC=$?
  kill $pid 2>/dev/null; wait $pid 2>/dev/null
  [ "$RRC" = 0 ] && v=OK || v=DEFECT
  line T-64 $v "exit=$RRC (lines differing from EXPECTED) || $(printf '%s\n' "$ROUT" | sed 's/ want=[^|]*$//' | one 600)"; }

t65() { prep T-65
  std T-65 repro.tk; local a=$(outcome) ac=$CRC ar=$RRC
  local bad=0; grep -q "multiple definition of local value named 't0'" "$CLOG" && bad=1
  chk T-65 repro.tk
  std T-65 control.tk; local c=$(outcome)
  if [ "$ac" = 0 ] && [ "$ar" = 5 ]; then v=OK
  elif [ $bad = 1 ] && [ "$KRC" = 0 ]; then v=DEFECT
  elif [ "$KRC" != 0 ]; then v="OK (now rejected at --check)"
  else v=note; fi
  line T-65 "$v" "param t0: --check rc=$KRC; build: $a (expected exit 5) || local t0 (control): $c"; }

t66() { prep T-66
  std T-66 repro.tk; local a=$(outcome) ac=$CRC
  chk T-66 repro.tk
  if [ "$KRC" != 0 ]; then v=OK
  elif [ "$ac" = 0 ]; then v=OK
  elif grep -q 'E9005' "$CLOG"; then v=DEFECT
  else v=note; fi
  line T-66 "$v" "--check rc=$KRC; build: $a"; }

t67() { prep T-67
  std T-67 repro.tk --allow-run; local a=$(outcome) ac=$CRC ar=$RRC
  chk T-67 repro.tk; local ak=$KRC
  std T-67 laundered.tk --allow-run; local l=$(outcome) lr=$RRC
  chk T-67 laundered.tk; local lk=$KRC
  std T-67 zero.tk --allow-run; local z=$(outcome)
  std T-67 abistr.tk; local sa=$(outcome) sc=$CRC sr=$RRC
  chk T-67 abistr.tk; local sk=$KRC
  if [ "$ak" != 0 ]; then v="OK (now rejected at --check)"
  elif [ "$ac" = 0 ] && [ "$ar" = 0 ] && printf '%s' "$ROUT" | grep -q 'wait(0)=-1'; then v=OK
  else v=DEFECT; fi
  { [ "$ac" = 0 ] && [ "$ar" = 139 ]; } || { [ "$sc" = 0 ] && [ "$sr" = 139 ]; } && v=DEFECT
  line T-67 "$v" "process.wait(5): --check rc=$ak; $a || via h:i64 helper: --check rc=$lk; $l || wait(0) control: $z || str.toupper(42): --check rc=$sk; $sa"; }

t59() { prep T-59; cp "$HERE/T-59/"* "$W/"
  local m out r=""
  for m in scoped_fs scoped_net loke envalias noenforce; do
    ( cd "$W" && "$TOKE_DIR/toke" --diag-text --config="$W/$m.toml" --out "$W/$m" cap_probe.tk ) > "$W/$m.clog" 2>&1 \
      || { r="$r || $m: build failed $(firsterr "$W/$m.clog")"; continue; }
    grep -qE '^(warning|error)' "$W/$m.clog" && r="$r || $m: $(grep -m1 -E '^(warning|error)' "$W/$m.clog" | cut -c1-120)"
  done
  local fs net wid ali enf
  fs=$(cd "$W" && "$W/scoped_fs" fs_read 2>&1 | head -1)
  net=$(cd "$W" && "$W/scoped_net" net 2>&1 | head -1)
  wid=$(cd "$W" && "$W/loke" env_write --allow-env 2>&1 | head -1)
  ali=$(cd "$W" && "$W/envalias" env_write 2>&1 | head -1)
  enf=$(cd "$W" && "$W/noenforce" fs_read 2>&1 | head -1)
  case "$fs|$net|$wid|$ali" in *-done*) v=OPEN ;; *) v=note ;; esac
  line T-59 "$v" "fs_read=\"/nonexistent-dir-only\" reading /etc/hosts: $fs || net=\"10.255.255.1:9\": $net || loke manifest + --allow-env: $wid || env=true: $ali || enforce=false, fs_read: $enf$r"; }

p127319() { prep 127.319
  std 127.319 repro.tk; local a=$(outcome) ac=$CRC
  cp "$HERE/127.319/mapget.tk" "$W/"; chk 127.319 mapget.tk; local mk=$KRC mm; mm=$(grep -m1 -E '^error' "$KLOG" | cut -c1-110)
  chk 127.319 repro.tk
  if [ "$KRC" != 0 ]; then v=OK; elif [ "$ac" = 0 ]; then v=OPEN; else v=note; fi
  line 127.319 "$v" "std T!E used unmatched: --check rc=$KRC; $a || m.get(k)+1 (127.244, control): --check rc=$mk $mm"; }

p13832() { prep 138.32; cp "$HERE/138.32/annot.tk" "$W/"
  chk 138.32 annot.tk
  if [ "$KRC" = 0 ]; then v=OK; elif grep -q 'E2005' "$KLOG"; then v=OPEN; else v=note; fi
  line 138.32 "$v" "h:handle in a parameter: --check rc=$KRC $(grep -m1 -E '^error' "$KLOG" | cut -c1-120)"; }

# ---- RW: the 2026-09-27 reproducers that no longer build as written, rewritten for v3.2.0
rec_start() { rm -f "$2" "$2.port"; W2_PORT=$1 python3 -I "$HERE/rewrites/recorder.py" "$2" "$2.port" answer >/dev/null 2>&1 & echo $! > "$2.pid"
  local i; for i in $(seq 50); do [ -f "$2.port" ] && break; sleep 0.1; done; }
rec_stop() { local p; [ -f "$1.pid" ] || return 0; p=$(cat "$1.pid"); kill "$p" 2>/dev/null; wait "$p" 2>/dev/null; rm -f "$1.pid"; }
rwone() { local id=$1 f=$2; shift 2; std rewrites "$f" "$@"; }
rw() { prep RW
  local lg="$W/rec57.log"
  rec_start 47995 "$lg"; rwone RW p57.tk --allow-net; local o57=$(outcome); sleep 0.3; rec_stop "$lg"
  local n57; n57=$(grep -c '^GET /health' "$lg" 2>/dev/null)
  line T-57 "$( [ "${n57:-0}" = 300 ] && echo OK || echo DEFECT)" "clientget x300: $o57 || recorder GET /health: ${n57:-0}"
  rwone RW p15.tk --allow-net; local o15=$(outcome)
  line T-15 "$(printf '%s' "$ROUT" | grep -q 'clientget=err' && printf '%s' "$ROUT" | grep -q 'geturl=err' && echo OK || echo DEFECT)" "closed port: $o15"
  lg="$W/rec10.log"; rec_start 47996 "$lg"; rwone RW p10.tk --allow-net; local o10=$(outcome); sleep 0.3; rec_stop "$lg"
  local r10; r10=$(cut -d' ' -f1-2 "$lg" 2>/dev/null | tr '\n' ',')
  v=DEFECT; case "$r10" in *"POST /post"*"PUT /put"*"DELETE /del"*) v=OK ;; esac
  line T-10 $v "$o10 || recorder: $r10"
  lg="$W/rec48.log"; rec_start 47993 "$lg"; rwone RW p48.tk --allow-net; local o48=$(outcome); sleep 0.3; rec_stop "$lg"
  line T-48 "$(grep -q 'x-api-key=k1;content-type=application/json' "$lg" 2>/dev/null && echo OK || echo DEFECT)" "$o48 || recorder: $(one 160 < "$lg" 2>/dev/null)"
  rwone RW p32.tk; line T-32 "$(printf '%s' "$ROUT" | grep -q '=150' && echo OK || echo DEFECT)" "$(outcome)"
  rwone RW p49.tk --allow-net; line T-49 "$(printf '%s' "$ROUT" | grep -q 'fd>0=true' && echo OK || echo DEFECT)" "$(outcome)"
  rwone RW pr8.tk --allow-all; local t8="A=[$(sqlite3 "$W/A.db" .tables 2>&1 | one)] B=[$(sqlite3 "$W/B.db" .tables 2>&1 | one)]"
  line R8 "$(printf '%s' "$ROUT" | grep -q 'ha=1 hb=2' && echo OK || echo DEFECT)" "$(outcome) || $t8"
  rwone RW p16.tk; line T-16 "$(printf '%s' "$ROUT" | grep -q 'body=\[got POST /x body=hello\]' && echo OK || echo DEFECT)" "$(outcome)"
  rwone RW p36.tk; line T-36 "$(printf '%s' "$ROUT" | grep -q 'compare(a,b)=-1 compare(b,a)=1 compare(a,a)=0 padleft=\[007\] tof32=12345' && echo OK || echo DEFECT)" "$(outcome)"
  rwone RW p09.tk; line T-9 "$(printf '%s' "$ROUT" | grep -q 'S: _ _' && echo OK || echo DEFECT)" "$(outcome) (the lazy line: see run.sh T-9 in repro-2026-09-27, E4075)"
  rwone RW p55.tk; local rx; rx=$(printf '%s' "$ROUT" | sed -n 's/.*ratio_x10=\([0-9]*\).*/\1/p')
  line T-55 "$( [ "${rx:-99}" -le 25 ] && echo OK || echo DEFECT)" "$(outcome) (x10 ratio for 2x the bytes: 20 linear, 40 quadratic)"
  cp "$HERE/rewrites/p43.tk" "$W/"; ( cd "$W" && build_direct p43.tk "$W/b43" ) ; local la=none
  if [ -x "$W/b43" ]; then ( cd "$W" && exec "$W/b43" --allow-net ) >/dev/null 2>&1 & local p=$!; sleep 1.5
    la=$(lsof -nP -a -p $p -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $9}' | head -1); kill $p 2>/dev/null; wait $p 2>/dev/null; fi
  v=DEFECT; case "$la" in 127.0.0.1:*) v=OK ;; esac
  line T-43 $v "http.serveon(\"127.0.0.1\";47997) listens on: ${la:-none}"; }

ALL="T-64 T-65 T-66 T-67 T-59 127.319 138.32 RW"
echo "toke: $TOKE_DIR ($REV)   work: $WORK"
for id in ${*:-$ALL}; do
  case $id in
    T-64) t64 ;; T-65) t65 ;; T-66) t66 ;; T-67) t67 ;; T-59) t59 ;;
    127.319) p127319 ;; 138.32) p13832 ;; RW) rw ;;
    *) line "$id" "?" "unknown id" ;;
  esac
done
