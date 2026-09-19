#!/bin/sh
# check_toolchain.sh — verify the local toke/ooke checkouts match TOOLCHAIN.lock
#
# Exit codes:
#   0 — versions match the lock (commit drift is a warning only)
#   1 — major version drift, or a checkout is missing
#
# Usage:
#   ./scripts/check_toolchain.sh            # check against TOOLCHAIN.lock
#   TOKE_DIR=... OOKE_DIR=... ./scripts/check_toolchain.sh

set -eu

PROJECTDIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$PROJECTDIR/TOOLCHAIN.lock"
TOKE_DIR="${TOKE_DIR:-$HOME/tk/toke}"
OOKE_DIR="${OOKE_DIR:-$HOME/tk/toke-ooke}"

[ -f "$LOCK" ] || { echo "ERROR: $LOCK not found" >&2; exit 1; }

lockval() { sed -n "s/^$1[[:space:]]*=[[:space:]]*//p" "$LOCK" | head -1; }

WANT_TOKE_V=$(lockval toke_version)
WANT_TOKE_C=$(lockval toke_commit)
WANT_OOKE_V=$(lockval ooke_version)
WANT_OOKE_C=$(lockval ooke_commit)

STATUS=0

check_one() {
  _name="$1"; _dir="$2"; _wantv="$3"; _wantc="$4"

  if [ ! -d "$_dir" ]; then
    echo "ERROR: $_name checkout not found at $_dir" >&2
    echo "       set ${_name}_DIR or clone $(lockval "$(echo "$_name" | tr 'A-Z' 'a-z')_repo")" >&2
    STATUS=1
    return
  fi

  _gotv="unknown"
  [ -f "$_dir/VERSION" ] && _gotv=$(tr -d ' \n' < "$_dir/VERSION")
  _gotc=$(git -C "$_dir" rev-parse --short HEAD 2>/dev/null || echo unknown)

  _wantmajor=$(echo "$_wantv" | cut -d. -f1)
  _gotmajor=$(echo "$_gotv" | cut -d. -f1)

  if [ "$_gotmajor" != "$_wantmajor" ]; then
    echo "ERROR: $_name major version drift — lock wants $_wantv, found $_gotv" >&2
    echo "       A major bump is a breaking change. Run a toolchain-currency pass (F10)." >&2
    STATUS=1
  elif [ "$_gotv" != "$_wantv" ]; then
    echo "WARN:  $_name version $_gotv differs from locked $_wantv (same major)" >&2
  fi

  if [ "$_gotc" != "$_wantc" ]; then
    echo "WARN:  $_name at commit $_gotc, lock verified against $_wantc" >&2
    echo "       Build may differ from the verified baseline." >&2
  fi

  echo "  $_name: $_gotv @ $_gotc (locked: $_wantv @ $_wantc)"
}

echo "Toolchain check:"
check_one TOKE "$TOKE_DIR" "$WANT_TOKE_V" "$WANT_TOKE_C"
check_one OOKE "$OOKE_DIR" "$WANT_OOKE_V" "$WANT_OOKE_C"

exit "$STATUS"
