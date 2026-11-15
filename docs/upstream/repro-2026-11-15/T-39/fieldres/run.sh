#!/bin/sh
# Field-resolution sibling of T-39 at toke v3.2.0 (ea7ddf22). user.tk imports proto ONLY so
# that r.text resolves on a $res returned by server.handle. --lint reports `p` unused-import;
# after --lint --fix, --check still passes but compiling (--emit-llvm) fails E4034
# "no struct in scope declares a field 'text'". Two defects: the lint false positive, and
# --check accepting what the compile rejects.  Usage: TOKE=/path/to/toke sh run.sh
set -u
T=${TOKE:-${TOKE_DIR:?set TOKE to a toke binary or TOKE_DIR to a toke checkout}/toke}
HERE="$(cd "$(dirname "$0")" && pwd)"
# Build products go to $WORK, never into this directory.
WORK="${WORK:-${TMPDIR:-/tmp}/loke-repro-T-39-fieldres}"
rm -rf "$WORK"; mkdir -p "$WORK/ifc" "$WORK/out"; cp -R "$HERE/src" "$WORK/"
cd "$WORK"
"$T" -I ifc --emit-interface --emit-llvm --out ifc src/proto.tk
"$T" -I ifc --emit-interface --emit-llvm --out ifc src/server.tk
echo "== lint user.tk:"; "$T" -I ifc --lint src/user.tk 2>&1 | grep -o '"rule":"[^"]*","severity":"[^"]*","stage":"[^"]*","message":"[^"]*"' || echo "(none)"
echo "== compile BEFORE fix:"; "$T" -I ifc --emit-llvm --out out src/user.tk >/dev/null 2>&1 && echo ok || echo FAIL
cp src/user.tk out/user.tk
"$T" -I ifc --lint --fix out/user.tk >/dev/null 2>&1
echo "== after --lint --fix:"; cat out/user.tk
echo "== --check after fix:"; "$T" -I ifc --check out/user.tk 2>&1 | grep -o '"error_code":"[^"]*"\|"message":"[^"]*"' || echo clean
echo "== compile after fix:"; "$T" -I ifc --emit-llvm --out out out/user.tk 2>&1 | grep -o '"error_code":"[^"]*"\|"message":"[^"]*"' || echo ok
