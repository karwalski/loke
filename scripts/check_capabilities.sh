#!/bin/sh
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# check_capabilities.sh — F10.9: the capability manifest grants what tkc.toml's comments
# say it grants, and the three binaries carry it.
#
# Two checks, both against the pinned toke:
#
#   1. scripts/lib/cap_probe.tk, built with THIS repository's tkc.toml, performs one gated
#      call per capability class. fs_read, fs_write, net and process_spawn must return;
#      env_write must abort with CAP001. That is the manifest's claim, measured rather than
#      read: from 2026-09-22 to 2026-09-28 the file said env.write was not granted while its
#      `env = true` line granted exactly that, because `env` is toke's short spelling of
#      env_write.
#   2. Each built entry module (loke, moke, loke-cli) bakes the same grant set, 0x17. The
#      grants are emitted only into the module that defines main, so this is where a build
#      that dropped --config, or a second manifest, would show.
#
# It does not check scope: toke cannot enforce one (T-59). It does not stop a launcher
# adding --allow-* flags at run time; nothing in this repository does, and T-59 asks for a
# way to forbid it.
#
#   scripts/check_capabilities.sh          # needs TOKE_DIR; check 2 skips unbuilt binaries

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOKE="${TOKE_DIR:-$HOME/tk/toke}/toke"
[ -x "$TOKE" ] || { echo "check_capabilities: toke not found at $TOKE (set TOKE_DIR)" >&2; exit 1; }

# fs_read | fs_write | net | process_spawn, from toke's src/stdlib/capabilities.h.
WANT=23
FAILS=0
fail() { echo "  FAIL  $1" >&2; FAILS=$((FAILS + 1)); }
ok() { echo "  ok    $1"; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_capcheck.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM

got=$("$TOKE" --config="$ROOT/tkc.toml" --show-limits 2>&1 | sed -n 's/^ *cap-grants *= *//p')
[ "$got" = "0x17" ] && ok "tkc.toml parses to grants 0x17" || fail "tkc.toml parses to grants '$got', expected 0x17"

cp "$ROOT/scripts/lib/cap_probe.tk" "$WORK/"
if ! ( cd "$WORK" && "$TOKE" --config="$ROOT/tkc.toml" --out "$WORK/probe" cap_probe.tk ) > "$WORK/build.log" 2>&1; then
  cat "$WORK/build.log" >&2
  fail "cap_probe.tk did not build"
else
  for c in fs_read fs_write net process_spawn; do
    out=$("$WORK/probe" "$c" "$WORK/scratch.txt" 2>&1)
    case "$out" in
      *"$c-done"*) ok "$c is granted" ;;
      *) fail "$c should be granted; the probe said: $out" ;;
    esac
  done
  out=$("$WORK/probe" env_write 2>&1)
  case "$out" in
    *"CAP001: capability 'env.write'"*) ok "env_write is refused with CAP001" ;;
    *) fail "env_write must not be granted; the probe said: $out" ;;
  esac
fi

for ll in "$ROOT/packages/browser/build/main.ll" \
          "$ROOT/build/trees/moke/main.ll" \
          "$ROOT/build/trees/loke-cli/main.ll"; do
  [ -f "$ll" ] || { echo "  skip  $ll not built"; continue; }
  n=$(sed -n 's/^@__tk_cap_baked_grants = constant i32 //p' "$ll")
  [ "$n" = "$WANT" ] && ok "${ll#"$ROOT"/} bakes grants $n" \
    || fail "${ll#"$ROOT"/} bakes grants '${n:-none}', expected $WANT"
done

[ "$FAILS" -eq 0 ] || { echo "check_capabilities: $FAILS check(s) FAILED" >&2; exit 1; }
echo "check_capabilities: OK"
