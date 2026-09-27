#!/bin/bash
# rec.sh start PORT LOG | stop PORT : run the recorder on a fixed port (11441-11449), PID in LOG.pid
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$1" in
start) rm -f "$3" "$3.port"; W2_PORT=$2 python3 "$HERE/recorder.py" "$3" "$3.port" answer >/dev/null 2>&1 & echo $! > "$3.pid"
       for i in $(seq 50); do [ -f "$3.port" ] && break; sleep 0.1; done;;
stop)  [ -f "$3.pid" ] && kill "$(cat "$3.pid")" 2>/dev/null; rm -f "$3.pid";;
esac
