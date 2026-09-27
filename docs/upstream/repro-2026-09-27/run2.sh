#!/bin/bash
# run2.sh TOKE_DIR  -- compile and run the T-31..T-57 reproducers (and the R1-R8 probes)
# against the toke checkout in TOKE_DIR and print one line per issue:
#   T-NN | VERDICT | observed evidence
# VERDICT is computed from the observed output by the rule in each check below.
# Local listeners/recorders use ports 11441-11446 on 127.0.0.1 only. Nothing is sent off-host.
# Build outputs go to OUT/T-NN/run2_<label>/ where label is TOKE_DIR's basename.
set -u
TD="$(cd "${1:?usage: run2.sh TOKE_DIR}" && pwd)"
OUT="$(cd "$(dirname "$0")" && pwd)"
L="$(basename "$TD")"
TK="$TD/toke"
B="$OUT/w2tools/tkbuild.sh"
REC="$OUT/w2tools/rec.sh"
line() { printf '%-6s | %-22s | %s\n' "$1" "$2" "$3"; }
wd() { mkdir -p "$OUT/$1/run2_$L"; echo "$OUT/$1/run2_$L"; }
# build ISSUE SRC(relative to OUT/ISSUE) NAME [flags] -> binary path in $BIN, diagnostics in $DIAG
build() { local d; d=$(wd "$1"); BIN="$d/$3"; DIAG=$( (cd "$OUT/$1" && "$B" "$TD" "$2" "$BIN" --diag-text "${@:4}") 2>&1 ); }
runq() { "$@" 2>&1; }
export LC_ALL=C   # run, merge stderr
echo "# run2.sh against $TD ($(cd "$TD" && git rev-parse --short HEAD 2>/dev/null)) $(date -u +%FT%TZ)"

# ---- T-31
build T-31 repro.tk r; o=$(runq "$BIN")
case "$o" in *"valid,errfirst=err"*) v=REPRODUCES;; *"valid,errfirst=ok invalid,okfirst=err invalid,errfirst=err"*) v=FIXED;; *) v=CHANGED;; esac
line T-31 "$v" "$o"

# ---- T-32
build T-32 repro.tk r; o=$(runq "$BIN"); rc=$?
case "$o" in *"str(usage)=err i64(usage.input_tokens)=err"*) v=REPRODUCES;; *) v=CHANGED;; esac
python3 "$OUT/w2tools/sigs.py" "$TD/stdlib/json.tki" | grep -q '^json.obj ( Json, str )' && v="$v(typed json.obj exists)"
line T-32 "$v" "$(echo "$o" | tr '\n' ' ') rc=$rc (rc 139 = getval handle fed to json.i64 segfaults)"

# ---- T-33
build T-33 repro.tk r; o=$(runq "$BIN")
case "$o" in *"i64(0)=err"*) v=REPRODUCES;; *"i64(0)=ok:0 u64(0)=ok:0 f64(0.0)=ok:0 bool(false)=ok:0"*"i64(missing)=err"*) v=FIXED;; *) v=CHANGED;; esac
line T-33 "$v" "$o"

# ---- T-34
build T-34 repro.tk r; o1=$(runq "$BIN"); rc1=$?
build T-34 repro_json.tk rj; d2=$DIAG; o2=$([ -x "$BIN" ] && runq "$BIN"); rc2=$?
if [ $rc1 -ne 0 ] && echo "$o1" | grep -q "Operation not permitted"; then v=REPRODUCES
elif [ "$o1" = built ] && [ "$o2" = built ]; then v=FIXED; else v=CHANGED; fi
line T-34 "$v" "res.err: rc=$rc1 out=[$(echo "$o1" | tr -cd '[:print:]' | cut -c1-60)] | res.json: $( [ -n "$o2" ] && echo "out=$o2" || echo "$d2" | grep -m1 -o 'Undefined symbols\|"_json"' | head -1)"

# ---- T-35
d=$(wd T-35); r=""
for f in repro repro_669 repro_big; do
  "$TK" --emit-llvm "$OUT/T-35/$f.tk" --out "$d/$f.ll" >/dev/null 2>&1; trc=$?
  clang -c -x ir "$d/$f.ll" -o "$d/$f.o" >/dev/null 2>&1; crc=$?
  r="$r $f:toke=$trc,clang=$crc"
done
case "$r" in *"repro:toke=0,clang=1"*) v=REPRODUCES;; *"repro:toke=0,clang=0"*) v=FIXED;; *) v="CHANGED";; esac
line T-35 "$v" "$r (669 is the control)"

# ---- T-36
build T-36 repro.tk r; lenok=$([ -x "$BIN" ] && echo compiles || echo "rejected: $(echo "$DIAG" | grep -m1 -o 'error\[E[0-9]*\]')")
build T-36 repro_b.tk rb; o=$(runq "$BIN" | tr -cd '[:print:]\n' | head -1)
cmp=$(echo "$o" | grep -o 'compare(b,a)=[-0-9]*')
if [ "$lenok" = compiles ] && [ "$cmp" = "compare(b,a)=1" ]; then v=REPRODUCES
elif [ "$cmp" = "compare(b,a)=1" ]; then v="CHANGED"; else v=FIXED; fi
line T-36 "$v" "str.len(array): $lenok | $o"

# ---- T-37
build T-37 repro.tk r; o1=$([ -x "$BIN" ] && runq "$BIN" || echo "$DIAG" | grep -m1 -o "error: .*expected 'double'")
build T-37 repro_field.tk rf; o2=$([ -x "$BIN" ] && runq "$BIN" || echo "$DIAG" | grep -m1 -o "error: .*expected 'double'")
if [ "$o1" = "2 1.5" ] && [ "$o2" = "2 2.5" ]; then v=FIXED; elif [ "$o1" != "2 1.5" ] && [ "$o2" != "2 2.5" ]; then v=REPRODUCES; else v=CHANGED; fi
line T-37 "$v" "return: $o1 | field: $o2"

# ---- T-38
build T-38 repro.tk r
if [ -x "$BIN" ]; then o=$(runq "$BIN"; echo "rc=$?"); v=$([ "$o" = "rc=7" ] && echo FIXED || echo CHANGED); else o=$(echo "$DIAG" | grep -m1 'error'); v=REPRODUCES; fi
line T-38 "$v" "$o"

# ---- T-39
d=$(wd T-39); cp "$OUT/T-39/repro.tk" "$d/repro.tk"; cp "$OUT/T-39/t39lib.tk" "$d/t39lib.tk"
( cd "$d" && rm -f t39lib.tki && "$TK" --emit-interface --check t39lib.tk >/dev/null 2>&1 )
lint=$(cd "$d" && "$TK" --lint repro.tk --diag-text 2>&1 | grep -m1 -o 'unused-import.*')
cp "$d/repro.tk" "$d/fix.tk"; ( cd "$d" && "$TK" --lint --fix fix.tk >/dev/null 2>&1 )
chk=$(cd "$d" && "$TK" --check fix.tk --diag-text 2>&1 | grep -m1 'error'); crc=$?
if [ -n "$lint" ] && [ -n "$chk" ]; then v=REPRODUCES; elif [ -z "$lint" ] && [ -z "$chk" ]; then v=FIXED; else v=CHANGED; fi
line T-39 "$v" "lint: ${lint:-none} | imports after --fix: $(grep -c '^i=' "$d/fix.tk") | check after fix: ${chk:-ok}"

# ---- T-40
build T-40 repro.tk r; db="$(wd T-40)/t40.sqlite"; rm -f "$db"; o=$(runq "$BIN" "$db" --allow-read --allow-write)
tabs=$(sqlite3 "$db" "select name from sqlite_master" 2>&1 | tr '\n' ',')
case "$o|$tabs" in *exec-ok*"|x,") v=REPRODUCES;; *"|x,ix_x,") v=FIXED;; *) v=CHANGED;; esac
line T-40 "$v" "program: $(echo "$o" | cut -d' ' -f1-2) | sqlite_master (sqlite3 CLI): $tabs"

# ---- T-41
build T-41 repro.tk r; o=$(runq "$BIN")
bad=$(echo "$o" | grep -E '=\[[0-9]{9,}\]' | cut -d= -f1 | tr '\n' ' ')
nb=$(echo "$bad" | wc -w | tr -d ' ')
if [ "$nb" -ge 14 ]; then v=REPRODUCES; elif [ "$nb" = 0 ]; then v=FIXED; else v="CHANGED"; fi
line T-41 "$v" "$nb of 14 print an address: ${bad:-none}"

# ---- T-42
build T-42 repro.tk r
if [ -x "$BIN" ]; then o=$(runq "$BIN"); v=$([ "$o" = a ] && echo REPRODUCES || echo CHANGED); else o=$(echo "$DIAG" | grep -m1 error); v=FIXED; fi
line T-42 "$v" "undeclared \$ghost literal -> $o"

# ---- T-43
r=""; v=REPRODUCES
for f in repro:11441 repro_listen:11442; do
  n=${f%%:*}; p=${f##*:}; build T-43 $n.tk $n
  "$BIN" --allow-net >/dev/null 2>&1 & pid=$!; sleep 1.5
  la=$(lsof -nP -a -p $pid -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $9}' | head -1)
  kill $pid 2>/dev/null; wait $pid 2>/dev/null
  r="$r $n:${la:-none}"; case "$la" in 127.0.0.1:*) v=FIXED;; esac
done
v43=$v; line T-43 "$v" "listen addresses (lsof):$r"

# ---- T-44
build T-44 repro.tk r; o=$(runq "$BIN")
case "$o" in *lastbyte=110*) v=REPRODUCES;; *lastbyte=10) v=FIXED;; *) v=CHANGED;; esac
line T-44 "$v" "$o"

# ---- T-45
build T-45 repro.tk r; o=$(runq "$BIN")
case "$o" in *" 10 "*|*" 9 "*|*" 13 "*) v=REPRODUCES;; *) v=FIXED;; esac
line T-45 "$v" "$o"

# ---- T-46
build T-46 repro.tk r; o=$(runq "$BIN"; echo "rc=$?")
case "$o" in *'len(@("g";g))=1'*) v=REPRODUCES;; *'len(@("g";g))=2'*'a[last]=12345'*) v=FIXED;; *) v=CHANGED;; esac
line T-46 "$v" "$(echo "$o" | tr '\n' ' ')"

# ---- T-47a
build T-47a repro.tk r; o=$(runq "$BIN")
case "$o" in *"bytes=97 110 98 116"*) v=REPRODUCES;; *"bytes=97 10 98 9 99 13 100 34 101 92 102 65 "*) v=FIXED;; *) v=CHANGED;; esac
line T-47a "$v" "$o"

# ---- T-47b
build T-47b repro.tk r; o1=$([ -x "$BIN" ] && runq "$BIN" || echo "rejected: $(echo "$DIAG" | grep -m1 error)")
build T-47b repro_str.tk rs; o2=$(runq "$BIN")
nu=$(echo "$o2" | sed -n 's/.*nowunix=\([0-9]*\).*/\1/p'); tn=$(echo "$o2" | sed -n 's/.*time.now\/1000=\([0-9]*\).*/\1/p')
if [ -n "$nu" ] && [ -n "$tn" ] && [ $((nu - tn)) -le 2 ] && [ $((tn - nu)) -le 2 ]; then interp=ok; else interp=address; fi
case "$o1" in rejected*) arith=rejected;; *"b-a=0"*|*"b-a=1 "*) arith=numeric;; *) arith=on-handle;; esac
if [ $interp = address ]; then v=REPRODUCES; elif [ $arith = on-handle ]; then v=CHANGED; else v=FIXED; fi
line T-47b "$v" "interpolation=$interp [$o2] | arithmetic=$arith [$o1]"

# ---- T-48 (http only; https is never attempted)
lg="$(wd T-48)/rec.log"
build T-48 repro.tk r; d1=$DIAG; $REC start 11443 "$lg"; o1=$([ -x "$BIN" ] && runq "$BIN" --allow-net | tr '\n' ' '); sleep 0.3; $REC stop 11443 "$lg"
log1=$(cut -d' ' -f1-2 "$lg" 2>/dev/null | tr '\n' ',')
build T-48 repro_urlfirst.tk ru; $REC start 11443 "$lg.u"; runq "$BIN" --allow-net >/dev/null; sleep 0.3; $REC stop 11443 "$lg.u"
log2=$(cut -d' ' -f1-2 "$lg.u" 2>/dev/null | tr '\n' ',')
if [ -z "$o1" ]; then v="CHANGED"; o1="loke shape rejected: $(echo "$d1" | grep -m1 -o 'error\[E[0-9]*\]: type mismatch: expected .str., got .httpclient.')"
elif echo "$log1" | grep -q messages-loke; then v=FIXED; else v=REPRODUCES; fi
line T-48 "$v" "loke shape: $o1 recorder=[$log1] | url-first variant recorder=[$log2] | https unmeasured"

# ---- T-49
build T-49 repro.tk r; o=$(runq "$BIN" --allow-net); rc=$?
[ $rc = 139 ] && v=REPRODUCES || v=CHANGED
line T-49 "$v" "$(echo "$o" | tr '\n' ' ') rc=$rc"

# ---- T-50
build T-50 repro.tk r
if [ -x "$BIN" ]; then o=$(runq "$BIN" --allow-run); case "$o" in *"true->err"*) v=REPRODUCES;; *) v=CHANGED;; esac
else o=$(echo "$DIAG" | grep -m1 -o "error\[E[0-9]*\]: type mismatch: expected an error union 'T!E', got 'i32'"); v="FIXED(rejected)"; fi
line T-50 "$v" "$o"

# ---- T-51
build T-51 repro.tk r; o1=$(runq "$BIN" | tr '\n' ' ')
build T-51 repro_errfirst.tk re; o2=$(runq "$BIN" | tr '\n' ' ')
case "$o1" in *"dec arm=ok"*) v=REPRODUCES;; *) v="NO-STANDALONE-REPRO";; esac
line T-51 "$v" "ok-first: $o1| err-first (T-31 order): $o2"

# ---- T-52
d=$(wd T-52); ( cd "$d" && "$TK" --emit-interface --check "$OUT/T-52/repro.tk" >/dev/null 2>&1 ); rc=$?
[ $rc = 139 ] && v=REPRODUCES || v=FIXED
line T-52 "$v" "toke --emit-interface --check exit=$rc"

# ---- T-53
build T-53 repro.tk r; o1=$([ -x "$BIN" ] && runq "$BIN" || echo "$DIAG" | grep -m1 error)
build T-53 repro.tk r2 --max-params=24; o2=$([ -x "$BIN" ] && runq "$BIN" || echo "$DIAG" | grep -m1 error)
[ "$o1" = "16 17 20" ] && v=FIXED || v=REPRODUCES
line T-53 "$v" "default: $o1 | --max-params=24: $o2"

# ---- T-54 (needs t54lib compiled by the same toke; built as a separate .ll and linked in)
d=$(wd T-54); cp "$OUT/T-54/gen.py" "$d/"; ( cd "$d" && python3 gen.py 58 )
r=""
for fl in "" "--max-structs=256"; do
  ( cd "$d" && rm -f t54lib.tki && "$TK" $fl --emit-interface --emit-llvm t54lib.tk --out "$d/t54lib.ll" >/dev/null 2>&1 )
  BIN="$d/ri${fl:+_flag}"; rm -f "$BIN"
  DIAG=$(cd "$d" && W2_EXTRA_LL="$d/t54lib.ll" "$B" "$TD" repro_import.tk "$BIN" --diag-text $fl 2>&1)
  o=$([ -x "$BIN" ] && runq "$BIN" || echo "$DIAG" | grep -m1 -o 'error\[E[0-9]*\][^,]*')
  r="$r | ${fl:-default}: $o"
done
case "$r" in *"default: error[E4034]"*) v=REPRODUCES;; *"default: one=1"*) v=FIXED;; *) v=CHANGED;; esac
line T-54 "$v" "58 lib types + std.http$r"

# ---- T-55
build T-55 repro.tk r; o=$(runq "$BIN" | tr '\n' ' ')
rx=$(echo "$o" | sed -n 's/.*ratio_x10=\([0-9]*\).*/\1/p')
if [ "${rx:-0}" -ge 30 ]; then v=REPRODUCES; elif [ "${rx:-0}" -le 25 ]; then v=FIXED; else v=CHANGED; fi
line T-55 "$v" "$o(2x the bytes: x10 ratio of time; 20=linear, 40=quadratic)"

# ---- T-56
d=$(wd T-56); cp "$OUT/T-56/gen.py" "$d/"; ( cd "$d" && python3 gen.py 35 ); LL=""
for i in $(seq -f %02g 1 35); do ( cd "$d" && "$TK" --emit-interface --emit-llvm p$i.tk --out "$d/p$i.ll" >/dev/null 2>&1 ); LL="$LL $d/p$i.ll"; done
r=""
for fl in "" "--max-imports=64"; do
  BIN="$d/r${fl:+_flag}"; rm -f "$BIN"
  DIAG=$(cd "$d" && W2_EXTRA_LL="$LL" "$B" "$TD" repro.tk "$BIN" --diag-text $fl 2>&1)
  o=$([ -x "$BIN" ] && runq "$BIN" || echo "$DIAG" | grep -m1 -o 'error\[E[0-9]*\][^,]*')
  r="$r | ${fl:-default}: $o"
done
case "$r" in *"default: error[E9010]"*) v=REPRODUCES;; *"default: sum=630"*) v=FIXED;; *) v=CHANGED;; esac
line T-56 "$v" "36 imports (35 pages + std.io)$r"

# ---- T-57
lg="$(wd T-57)/rec.log"; build T-57 repro.tk r
$REC start 11445 "$lg"; o=$(runq "$BIN" --allow-net | tr '\n' ' '); sleep 0.3; $REC stop 11445 "$lg"
rl=$(cut -d' ' -f1-2 "$lg" 2>/dev/null | sort | uniq -c | tr -s ' ' | tr '\n' ',')
if ! grep -q /health "$lg" 2>/dev/null && echo "$o" | grep -q 'first_ok_call=257'; then v=REPRODUCES
elif grep -q /health "$lg" 2>/dev/null; then v=FIXED; else v=CHANGED; fi
line T-57 "$v" "$o| recorder:${rl:-empty}"

# ---- capability probes R1-R8
sig() { python3 "$OUT/w2tools/sigs.py" "$TD/stdlib/$1.tki" | grep -E "$2" | tr '\n' ';'; }
line R1 "$([ "$v43" = FIXED ] && echo present || echo absent)" "http serve sigs: $(sig http '^http\.(serve|serveworkers|servetls|servetlsworkers|listen) ')"
line R2 "flag-only" "default max-imports=$("$TK" --show-limits 2>&1 | sed -n 's/ *max-imports *= *//p'); see T-56 line for --max-imports=64"
line R3 "see-T-53/T-54" "default max-structs=$("$TK" --show-limits 2>&1 | sed -n 's/ *max-structs *= *//p') max-params=$("$TK" --show-limits 2>&1 | sed -n 's/ *max-params *= *//p')"
line R4 "$(grep -qi 'status\|osstatus' "$TD/stdlib/keychain.tki" && echo present || echo absent)" "keychain sigs: $(sig keychain .)"
line R5 "$(grep -qi 'keychainpath\|createkeychain\|"path"' "$TD/stdlib/keychain.tki" && echo present || echo absent)" "(no keychain path/create/delete member in keychain.tki)"
line R6 "see-T-48" "postheaders sig: $(sig http '^http\.postheaders ') url-first measured to send over http only"
d=$(wd w2probes/R7); lg="$d/rec.log"; BIN="$d/r7"; ( cd "$OUT/w2probes" && "$B" "$TD" r7_delete.tk "$BIN" >/dev/null 2>&1 )
$REC start 11446 "$lg"; runq "$BIN" --allow-net >/dev/null; sleep 0.3; $REC stop 11446 "$lg"
line R7 "$(grep -q DELETE "$lg" 2>/dev/null && echo present || echo absent)" "http.delete(client;path) recorder=[$(cat "$lg" 2>/dev/null | tr '\n' ',')] lowered to: $("$TK" --emit-llvm "$OUT/w2probes/r7_delete.tk" --out "$d/r7.ll" >/dev/null 2>&1; grep -o '@tk_http_delete_[a-z]*' "$d/r7.ll" | head -1)"
d=$(wd w2probes/R8); BIN="$d/r8a"; ( cd "$OUT/w2probes" && "$B" "$TD" r8_twodb.tk "$BIN" >/dev/null 2>&1 ); rm -f "$d/A.db" "$d/B.db"
o=$(runq "$BIN" "$d/A.db" "$d/B.db" --allow-read --allow-write); BIN="$d/r8b"; ( cd "$OUT/w2probes" && "$B" "$TD" r8_tx.tk "$BIN" >/dev/null 2>&1 ); rm -f "$d/tx.db"; o2=$(runq "$BIN" "$d/tx.db" --allow-read --allow-write)
line R8 "single-conn" "$o | files: A=[$(sqlite3 "$d/A.db" .tables 2>&1)] B=[$(sqlite3 "$d/B.db" .tables 2>&1)] | db.exec sig: $(sig db '^db\.exec ') | tx via exec: $o2"
