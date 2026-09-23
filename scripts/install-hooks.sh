#!/bin/sh
# install-hooks.sh — point git at the version-controlled hooks in githooks/.
#
# Why core.hooksPath rather than copying into .git/hooks: a hook inside .git is not
# version-controlled, so it cannot be reviewed, cannot be updated by a pull, and is
# invisible to anyone reading the repository. Story X4.2 was marked Done claiming a
# pre-push hook was in place; .git/hooks contained only the .sample files, and nobody
# could have noticed from the tree. Pointing at a tracked directory makes the hook a
# reviewable artefact and makes its absence visible.
#
# The gate checks this is installed, so forgetting is caught rather than silent.

set -eu
REPO=$(git rev-parse --show-toplevel)
cd "$REPO"

git config core.hooksPath githooks
chmod +x githooks/* 2>/dev/null || true

echo "hooks installed: core.hooksPath = githooks"
echo "  pre-push -> quality-gate.sh --step checks, plus check_sweep_commit.py"
echo
echo "To remove: git config --unset core.hooksPath"
