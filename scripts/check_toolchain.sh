#!/bin/sh
# check_toolchain.sh — verify the local toke/ooke checkouts meet TOOLCHAIN.lock
#
# The two dependencies are gated differently, deliberately:
#
#   toke  — gated on COMMIT ANCESTRY. Upstream states that no tagged toke
#           release works for loke; the requirement is a build of main at or
#           after toke_min_commit. The VERSION file is unreliable for this
#           purpose (it still reads 2.8.0 well past the v2.8.0 tag, so the tag
#           predates the commit loke needs), and is therefore advisory only.
#
#   ooke  — gated on VERSION. loke needs released 3.0.0, and a "-dev" suffix
#           does not satisfy that.
#
# Exit codes:
#   0 — requirements met
#   1 — a requirement is unmet, or a checkout is missing
#
# Usage:
#   ./scripts/check_toolchain.sh
#   TOKE_DIR=... OOKE_DIR=... ./scripts/check_toolchain.sh

set -eu

PROJECTDIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$PROJECTDIR/TOOLCHAIN.lock"
TOKE_DIR="${TOKE_DIR:-$HOME/tk/toke}"
OOKE_DIR="${OOKE_DIR:-$HOME/tk/toke-ooke}"

[ -f "$LOCK" ] || { echo "ERROR: $LOCK not found" >&2; exit 1; }

lockval() { sed -n "s/^$1[[:space:]]*=[[:space:]]*//p" "$LOCK" | sed 's/[[:space:]]*$//' | head -1; }

STATUS=0

echo "Toolchain check:"

# ── toke: commit ancestry ────────────────────────────────────────────────
TOKE_MIN=$(lockval toke_min_commit)
TOKE_WANT_V=$(lockval toke_version)

if [ ! -d "$TOKE_DIR" ]; then
  echo "ERROR: toke checkout not found at $TOKE_DIR" >&2
  echo "       set TOKE_DIR, or clone $(lockval toke_repo)" >&2
  STATUS=1
elif [ ! -d "$TOKE_DIR/.git" ]; then
  echo "ERROR: $TOKE_DIR is not a git checkout, so commit ancestry cannot be verified." >&2
  echo "       loke requires a build of toke main at or after $TOKE_MIN; a release" >&2
  echo "       tarball cannot satisfy that because no tagged release works." >&2
  STATUS=1
else
  toke_head=$(git -C "$TOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
  toke_v="unknown"
  [ -f "$TOKE_DIR/VERSION" ] && toke_v=$(tr -d ' \n' < "$TOKE_DIR/VERSION")

  if ! git -C "$TOKE_DIR" cat-file -e "$TOKE_MIN^{commit}" 2>/dev/null; then
    echo "ERROR: toke commit $TOKE_MIN is not present in $TOKE_DIR." >&2
    echo "       Fetch main: git -C $TOKE_DIR fetch origin main" >&2
    STATUS=1
  elif git -C "$TOKE_DIR" merge-base --is-ancestor "$TOKE_MIN" HEAD 2>/dev/null; then
    echo "  toke: OK   $toke_head is at or after $TOKE_MIN (version $toke_v, advisory)"
  else
    echo "ERROR: toke at $toke_head is BEFORE the required commit $TOKE_MIN." >&2
    echo "       loke needs a build of main at or after $TOKE_MIN. No tagged" >&2
    echo "       release works, so checking out a tag will not help." >&2
    STATUS=1
  fi

  if [ "$toke_v" != "$TOKE_WANT_V" ]; then
    echo "  note: toke VERSION is $toke_v, lock records $TOKE_WANT_V (advisory, not gated)"
  fi
fi

# ── ooke: released version ───────────────────────────────────────────────
OOKE_MIN=$(lockval ooke_min_version)

if [ ! -d "$OOKE_DIR" ]; then
  echo "ERROR: ooke checkout not found at $OOKE_DIR" >&2
  echo "       set OOKE_DIR, or clone $(lockval ooke_repo)" >&2
  STATUS=1
else
  ooke_head=$(git -C "$OOKE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
  ooke_v="unknown"
  [ -f "$OOKE_DIR/VERSION" ] && ooke_v=$(tr -d ' \n' < "$OOKE_DIR/VERSION")

  # A pre-release suffix does not satisfy a released-version requirement.
  case "$ooke_v" in
    *-*)
      echo "ERROR: ooke is $ooke_v, which is a pre-release. loke requires released" >&2
      echo "       $OOKE_MIN. The toolchain migration stays on hold until it ships." >&2
      STATUS=1
      ;;
    unknown)
      echo "ERROR: ooke VERSION not readable at $OOKE_DIR/VERSION" >&2
      STATUS=1
      ;;
    *)
      # Numeric compare on major.minor.patch, so 3.0.10 > 3.0.9.
      if [ "$(printf '%s\n%s\n' "$OOKE_MIN" "$ooke_v" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" = "$OOKE_MIN" ]; then
        echo "  ooke: OK   $ooke_v at $ooke_head (requires $OOKE_MIN or later)"
      else
        echo "ERROR: ooke is $ooke_v, which is older than the required $OOKE_MIN." >&2
        STATUS=1
      fi
      ;;
  esac
fi

if [ "$STATUS" -ne 0 ]; then
  hold=$(lockval hold_status)
  [ -n "$hold" ] && echo "" && echo "TOOLCHAIN.lock records: $hold" >&2
fi

exit "$STATUS"
