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

  # The requirement is now a named pre-release, v3.0.0-rc.1, so a pre-release
  # suffix no longer disqualifies a build. What still has to hold is that the
  # version is at least the pinned one, and an rc ordering needs its own
  # comparison: 3.0.0-rc.2 is newer than 3.0.0-rc.1, and plain 3.0.0 is newer
  # than any rc of it.
  #
  # Accepting an rc is a deliberate reversal of the earlier decision to wait for a
  # final release. It does not relax the publication bar: a figure measured here is
  # labelled with the exact version it was measured against, so if the final tag
  # moves, every affected number can be found again.
  ooke_core=${ooke_v%%-*}
  ooke_pre=${ooke_v#*-}
  [ "$ooke_pre" = "$ooke_v" ] && ooke_pre=""
  min_core=${OOKE_MIN%%-*}
  min_pre=${OOKE_MIN#*-}
  [ "$min_pre" = "$OOKE_MIN" ] && min_pre=""

  if [ "$ooke_v" = "unknown" ]; then
    echo "ERROR: ooke VERSION not readable at $OOKE_DIR/VERSION" >&2
    STATUS=1
  elif [ "$(printf '%s\n%s\n' "$min_core" "$ooke_core" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" != "$min_core" ]; then
    echo "ERROR: ooke is $ooke_v, older than the required $OOKE_MIN." >&2
    STATUS=1
  elif [ "$ooke_core" = "$min_core" ] && [ -n "$min_pre" ] && [ -n "$ooke_pre" ] \
       && [ "$(printf '%s\n%s\n' "$min_pre" "$ooke_pre" | sort -V | head -1)" != "$min_pre" ]; then
    echo "ERROR: ooke is $ooke_v, an earlier pre-release than the required $OOKE_MIN." >&2
    STATUS=1
  else
    note=""
    [ -n "$ooke_pre" ] && note="  (pre-release: any figure measured here is labelled $ooke_v)"
    echo "  ooke: OK   $ooke_v at $ooke_head (requires $OOKE_MIN or later)$note"
  fi
fi

# A pin nobody else can fetch is not a pin. CI dies on this with git exit 128 and
# a message about path arguments, which reads as a syntax error and is not one, so
# report it here where there is a local checkout to ask.
for pair in "toke:$TOKE_DIR" "ooke:$OOKE_DIR"; do
  name=${pair%%:*}
  dir=${pair#*:}
  sha=$(lockval "${name}_commit")
  [ -n "$sha" ] && [ -d "$dir/.git" ] || continue
  if ! git -C "$dir" cat-file -e "${sha}^{commit}" 2>/dev/null; then
    echo "WARNING: ${name}_commit $sha is not in $dir at all — the lock is stale" >&2
    continue
  fi
  if [ -z "$(git -C "$dir" branch -r --contains "$sha" 2>/dev/null)" ]; then
    echo "WARNING: ${name}_commit $sha is on no remote branch. CI cannot fetch it," >&2
    echo "         so the build is unreproducible off this machine. Push it, or" >&2
    echo "         re-pin TOOLCHAIN.lock to a published commit." >&2
  fi
done

if [ "$STATUS" -ne 0 ]; then
  hold=$(lockval hold_status)
  [ -n "$hold" ] && echo "" && echo "TOOLCHAIN.lock records: $hold" >&2
fi

exit "$STATUS"
