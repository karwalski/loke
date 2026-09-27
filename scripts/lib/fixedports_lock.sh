# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# fixedports_lock.sh — sourced by smoke_e2e.sh and smoke_ui.sh, which must own 11430, 11432
# and 11434. Two runs at once share those ports: one test's requests reach the other's
# servers, and smoke_ui used to SKIP (exit 0) when it found a port taken, so a collision
# could read as a pass. The quality gate runs both, so parallel gates collided too.
#
# A directory lock, because mkdir is atomic. The owner's pid is written inside it, and a
# lock whose owner has died is taken over rather than waited on for ever.

FIXEDPORTS_LOCK="${FIXEDPORTS_LOCK:-/tmp/loke-fixedports.lock}"
FIXEDPORTS_WAIT="${FIXEDPORTS_WAIT:-1800}"

acquire_fixedports() {
  local waited=0 owner
  while ! mkdir "$FIXEDPORTS_LOCK" 2>/dev/null; do
    owner=$(cat "$FIXEDPORTS_LOCK/pid" 2>/dev/null)
    if [ -n "$owner" ] && ! kill -0 "$owner" 2>/dev/null; then
      rm -rf "$FIXEDPORTS_LOCK"
      continue
    fi
    if [ "$waited" -ge "$FIXEDPORTS_WAIT" ]; then
      echo "fixed-port lock $FIXEDPORTS_LOCK still held by pid ${owner:-?} after ${waited}s" >&2
      return 1
    fi
    sleep 5; waited=$((waited + 5))
  done
  echo $$ > "$FIXEDPORTS_LOCK/pid"
}

release_fixedports() {
  if [ "$(cat "$FIXEDPORTS_LOCK/pid" 2>/dev/null)" = "$$" ]; then rm -rf "$FIXEDPORTS_LOCK"; fi
}
