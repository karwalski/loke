#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# serve_built_loke.sh — serve a copy of the BUILT loke binary on a free port, for a test
# that judges what the server really sends. (T13.2)
#
#   scripts/lib/serve_built_loke.sh WORKDIR PORTFILE
#
# WORKDIR is created and receives a copy of packages/browser/{pages,templates,static}, the
# binary and an ooke.toml whose [server] port is a free one chosen here. The port is written
# to PORTFILE only once everything is in place, then the script execs loke, so the caller
# kills the server by killing this process.
#
# Isolation. HOME is WORKDIR/home, never the caller's, and its ~/.loke/config.toml points
# every local service loke would otherwise probe (Ollama, Presidio, LLMLingua, the privacy
# filter) at a loopback port nothing listens on. So the served copy needs none of the fixed
# ports 11430/11432/11434 and takes no lock: a page that asks Ollama for its status gets
# "not running" instead of reaching another worker's fake Ollama. Nothing here can reach a
# provider: no key is configured, and the caller only GETs pages.
#
# Exit 1, with no PORTFILE written, when the binary is not built or the copy fails.

set -u
WORK="${1:?usage: serve_built_loke.sh WORKDIR PORTFILE}"
PORTFILE="${2:?usage: serve_built_loke.sh WORKDIR PORTFILE}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/packages/browser"
BIN="$SRC/build/loke"

[ -x "$BIN" ] || { echo "serve_built_loke: $BIN not built; run scripts/build_loke.sh" >&2; exit 1; }

freeport() {
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'
}
PORT=$(freeport) || exit 1
DEAD=$(freeport) || exit 1

rm -rf "$WORK"
mkdir -p "$WORK/home/.loke" || exit 1
for d in pages templates static; do
  [ -d "$SRC/$d" ] && { cp -R "$SRC/$d" "$WORK/" || exit 1; }
done
cp "$BIN" "$WORK/loke" || exit 1
sed -E "s/^([[:space:]]*port[[:space:]]*=).*/\1 $PORT/" "$SRC/ooke.toml" > "$WORK/ooke.toml" || exit 1
cat > "$WORK/home/.loke/config.toml" <<EOF
[providers]
ollama_url = "http://127.0.0.1:$DEAD"

[privacy]
presidio_url = "http://127.0.0.1:$DEAD"
llmlingua_url = "http://127.0.0.1:$DEAD"
privacy_filter = false
privacy_filter_url = "http://127.0.0.1:$DEAD"
EOF

cd "$WORK" || exit 1
printf '%s' "$PORT" > "$PORTFILE.tmp" && mv "$PORTFILE.tmp" "$PORTFILE"
HOME="$WORK/home" exec ./loke > "$WORK/serve.log" 2>&1
