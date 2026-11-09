#!/usr/bin/env bash
# run.sh — rerun loke's 2026-11-09 upstream reproducers against one toke (and ooke) checkout.
#
#   TOKE_DIR=/path/to/toke OOKE_DIR=/path/to/ooke ./run.sh            every issue
#   TOKE_DIR=/path/to/toke ./run.sh T-60 F10.42                        selected issues
#
# TOKE_DIR must contain the built `toke` binary and its stdlib. OOKE_DIR is needed only for
# O-4 and O-5, which compile ooke's own src/template.tk (copied, never modified).
# Prints one line per issue:  ID | VERDICT | observed outcome
# VERDICT is computed from the EXPECTED stated in each reproducer's header comment:
#   DEFECT   the defect as filed was observed
#   OK       the expected behaviour was observed
#   note     no automatic verdict; read the observed text
# Build products go to $WORK (default: $TMPDIR/loke-repro-2026-11-09/<toke short commit>), never
# into this directory. MK19.11 starts server.py on 127.0.0.1:47971-47973 and stops it by PID;
# it takes about 75 seconds. Nothing is sent off the machine.

set -u
export LC_ALL=C
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${TOKE_DIR:?set TOKE_DIR to a toke checkout}"
TOKE_DIR="$(cd "$TOKE_DIR" && pwd)"
[ -x "$TOKE_DIR/toke" ] || { echo "no toke binary at $TOKE_DIR/toke" >&2; exit 2; }
REV=$(git -C "$TOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
WORK="${WORK:-${TMPDIR:-/tmp}/loke-repro-2026-11-09/$REV}"
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

# multi ID BIN MAIN LIB... : interface for each LIB, then toke --out BIN MAIN LIB... in $W
multi() {
  local bin=$1 main=$2; shift 2
  : > "$CLOG"
  ( cd "$W" || exit 1
    for f in "$@"; do "$TOKE_DIR/toke" --diag-text --emit-interface --check "$f" >>"$CLOG" 2>&1 || exit 1; done
    "$TOKE_DIR/toke" --diag-text -I . --out "$bin" "$main" "$@" >>"$CLOG" 2>&1 ); CRC=$?
}

t60() { prep T-60
  std T-60 repro.tk; local a=$(outcome) ar=$RRC
  std T-60 contents.tk; local b=$(outcome) br=$RRC
  std T-60 spawn.tk --allow-all; local c=$(outcome) cr=$RRC
  { [ "$ar" = 7 ] && [ "$br" = 0 ] && [ "$cr" = 0 ]; } && v=OK || v=DEFECT
  line T-60 $v "with @(): $a (expected 7) || named arrays: $b (expected 0) || spawn idiom: $c (expected 0)"; }

t61() { prep T-61; cp "$HERE/T-61/"*.tk "$W/"
  multi "$W/bin" repro.tk t61lib.tk
  if [ "$CRC" = 0 ]; then ( cd "$W" && run_bin "$W/bin"; printf '%s\n%s' "$RRC" "$ROUT" > run.out )
    RRC=$(sed -n 1p "$W/run.out"); ROUT=$(sed -n '2,$p' "$W/run.out"); RSIG=""; fi
  if [ "$CRC" != 0 ] && grep -q "defined with type 'i64' but expected 'i32'" "$CLOG"; then v=DEFECT
  elif [ "$CRC" = 0 ] && [ "$RRC" = 5 ]; then v=OK; else v=note; fi
  line T-61 $v "$(outcome) (filed defect: invalid IR i64 vs i32; expected exit 5)"; }

f1042() { prep F10.42
  std F10.42 repro.tk; local a=$(outcome) ac=$CRC ar=$RRC
  local bad=0; grep -q "defined with type 'ptr' but expected 'i64'" "$CLOG" && bad=1
  ( cd "$W" && "$TOKE_DIR/toke" --diag-text --check repro.tk > check.log 2>&1; echo $? > check.rc )
  std F10.42 user.tk; local u=$(outcome)
  grep -q "defined with type 'ptr' but expected 'i64'" "$CLOG" && bad=1
  std F10.42 bound.tk; local b=$(outcome)
  { [ "$ac" = 0 ] && [ "$ar" = 1 ] && [ $bad = 0 ]; } && v=OK || v=DEFECT
  line F10.42 $v "--check rc=$(cat "$W/check.rc"); std call arg: $a || user fn arg: $u || row bound first (control): $b"; }

o_tpl() { local id=$1; prep "$id"
  : "${OOKE_DIR:?set OOKE_DIR to an ooke checkout for $id}"
  cp -R "$HERE/$id/." "$W/"; cp "$OOKE_DIR/src/template.tk" "$W/"
  multi "$W/bin" repro.tk template.tk
  if [ "$CRC" = 0 ]; then ( cd "$W" && run_bin "$W/bin" --allow-all; printf '%s\n%s' "$RRC" "$ROUT" > run.out )
    RRC=$(sed -n 1p "$W/run.out"); ROUT=$(sed -n '2,$p' "$W/run.out"); RSIG=""; fi
}
o04() { o_tpl O-4; local orev; orev=$(git -C "$OOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
  [ "$CRC" = 0 ] && [ "$RRC" = 0 ] && v=OK || v=DEFECT
  line O-4 $v "ooke $orev: $(outcome) (exit = templates answering \$ok that should fail, 0..3)"; }
o05() { o_tpl O-5; local orev; orev=$(git -C "$OOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
  local cl; cl=$(grep -m1 -o 'Use `{{raw[^`]*`' "$OOKE_DIR/CHANGELOG.md" 2>/dev/null || echo "not found")
  [ "$CRC" = 0 ] && [ "$RRC" = 1 ] && v=DEFECT || v=OK
  line O-5 $v "ooke $orev: CHANGELOG says: $cl || $(outcome)"; }

mk1911() { prep MK19.11; cp "$HERE/MK19.11/repro.tk" "$W/"
  ( cd "$W" && build_direct repro.tk "$W/bin" ); CRC=$?
  if [ "$CRC" != 0 ]; then line MK19.11 note "$(outcome)"; return; fi
  python3 -I "$HERE/MK19.11/server.py" > "$W/server.log" 2>&1 & local pid=$!
  sleep 1
  ROUT=$(cd "$W" && perl -e 'alarm 150; exec @ARGV or exit 127' "$W/bin" --allow-net 2>&1); RRC=$?
  kill $pid 2>/dev/null; wait $pid 2>/dev/null
  local d s b
  d=$(printf '%s\n' "$ROUT" | grep '^drip:'); s=$(printf '%s\n' "$ROUT" | grep '^stall:'); b=$(printf '%s\n' "$ROUT" | grep '^big:')
  v=note
  printf '%s' "$d" | grep -q '^drip: ok len=8' && v=DEFECT
  printf '%s' "$s" | grep -q '^stall: ok' && v=DEFECT
  printf '%s' "$b" | grep -q '^big: ok len=67108864' && v=DEFECT
  line MK19.11 $v "exit=$RRC || $d || $s || $b"; }

ALL="T-60 T-61 F10.42 MK19.11 O-4 O-5"
echo "toke: $TOKE_DIR ($REV)   ooke: ${OOKE_DIR:-unset}   work: $WORK"
for id in ${*:-$ALL}; do
  case $id in
    T-60) t60 ;; T-61) t61 ;; F10.42) f1042 ;; MK19.11) mk1911 ;; O-4) o04 ;; O-5) o05 ;;
    *) line "$id" "?" "unknown id" ;;
  esac
done
