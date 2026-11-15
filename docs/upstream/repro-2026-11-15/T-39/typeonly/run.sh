#!/bin/sh
# T-39 residue at toke v3.2.0 (ea7ddf22): an import used ONLY as a struct-field type
# (`t=$holder{items:@$item}` or `it:$item`) is reported unused-import, and --lint --fix deletes it,
# after which --check fails E3011. A param-type-only use (paramonly.tk) is NOT flagged.
# Usage: TOKE=/path/to/toke sh run.sh
set -u
T=${TOKE:-/Users/matthew.watt/loke/toolchain/toke-320/toke}
HERE="$(cd "$(dirname "$0")" && pwd)"
# Build products go to $WORK, never into this directory.
WORK="${WORK:-${TMPDIR:-/tmp}/loke-repro-T-39-typeonly}"
rm -rf "$WORK"; mkdir -p "$WORK/ifc" "$WORK/out"; cp -R "$HERE/src" "$WORK/"
cd "$WORK"
"$T" -I ifc --emit-interface --emit-llvm --out ifc src/defs.tk
for f in fieldonly scalarfield paramonly; do
  echo "== $f: lint";  "$T" -I ifc --lint src/$f.tk 2>&1 | grep -o '"rule":"[^"]*"' || echo "(none)"
done
cp src/fieldonly.tk out/fieldonly.tk
"$T" -I ifc --lint --fix out/fieldonly.tk >/dev/null 2>&1
echo "== fieldonly after --lint --fix:"; cat out/fieldonly.tk
echo "== --check after fix (expect clean; actual):"
"$T" -I ifc --check out/fieldonly.tk 2>&1 | grep -o '"error_code":"[^"]*"\|"message":"[^"]*"' || echo clean
