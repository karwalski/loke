# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# port_owner.sh — sourced by smoke_serve.sh and smoke_serve_moke.sh. (F10.38)
#
# Both scripts start a server on their own port and then probe whatever answers there. On
# 2026-09-27 another worker's fake Ollama already held smoke_serve's port: loke failed to
# bind, and the script went on to probe the fake. Every route "answered", and only the few
# checks that judge a body noticed. So a smoke now refuses to start on a port something
# already holds, and before probing it confirms that the process it launched, or one of
# its own children (ooke pre-forks workers that share the listening socket), is what holds
# the port, and that nothing else does.

# The pids listening on TCP $1, one per line. lsof ships with macOS; ss is the Linux
# fallback. With neither, nothing can be confirmed, and the caller refuses.
port_listeners() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | sort -u
  elif command -v ss >/dev/null 2>&1; then
    ss -Hltnp "sport = :$1" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u
  else
    return 2
  fi
}

port_tool_present() {
  command -v lsof >/dev/null 2>&1 || command -v ss >/dev/null 2>&1
}

# True when something accepts a connection on 127.0.0.1:$1. lsof sees only processes this
# user may inspect, so a listener owned by another user is caught here instead.
port_answers() {
  ( exec 3<>"/dev/tcp/127.0.0.1/$1" ) 2>/dev/null
}

# Refuse (return 1, with a message naming the holder) when port $2 is already in use.
# $1 is the script's name, for the message.
refuse_if_port_busy() {
  local name="$1" port="$2" holders
  if ! port_tool_present; then
    echo "$name: neither lsof nor ss is available, so it cannot confirm port $port is free or who holds it; refusing (F10.38)" >&2
    return 1
  fi
  holders=$(port_listeners "$port" | tr '\n' ' ')
  if [ -n "$holders" ] || port_answers "$port"; then
    echo "$name: port $port is already in use (pid(s): ${holders:-not visible to this user}); refusing to smoke-test a server it did not start (F10.38)" >&2
    local p
    for p in $holders; do ps -o pid=,command= -p "$p" 2>/dev/null | sed 's/^/  held by: /' >&2; done
    return 1
  fi
  return 0
}

# True when pid $2 is pid $1 or a descendant of it.
pid_descends_from() {
  local root="$1" p="$2" guard=0
  while [ -n "$p" ] && [ "$p" -gt 1 ] && [ "$guard" -lt 64 ]; do
    [ "$p" = "$root" ] && return 0
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    guard=$((guard + 1))
  done
  return 1
}

# Confirm that the server on port $2 is the one launched as pid $3: it is alive, it or one
# of its children holds the listening socket, and no other process does. $1 is the name.
assert_port_owner() {
  local name="$1" port="$2" pid="$3" holders p ours=0
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name: the server it started (pid $pid) is not running; whatever answers on $port is not it (F10.38)" >&2
    return 1
  fi
  holders=$(port_listeners "$port")
  if [ -z "$holders" ]; then
    echo "$name: no process visible to this user holds port $port, so the answer did not come from pid $pid (F10.38)" >&2
    return 1
  fi
  for p in $holders; do
    if pid_descends_from "$pid" "$p"; then
      ours=1
    else
      echo "$name: pid $p holds port $port and is not the server it started (pid $pid) (F10.38)" >&2
      ps -o pid=,command= -p "$p" 2>/dev/null | sed 's/^/  held by: /' >&2
      return 1
    fi
  done
  [ "$ours" -eq 1 ]
}

# GA2.5: the addresses TCP port $1 is listening on, one per line, as lsof prints them
# (`127.0.0.1:11430`, `*:11430`, `[::1]:11430`). Empty when nothing listens.
port_bind_addresses() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -Fn 2>/dev/null | sed -n 's/^n//p' | sort -u
}

# GA2.5: confirm that port $2 listens on loopback only. Every listening socket on it must
# be bound to 127.0.0.1 or ::1; `*:port` (every interface, INADDR_ANY) or any other
# address fails, naming what it saw. $1 is the caller's name, for the message. It needs
# lsof: `ss` prints addresses differently and no smoke here runs on Linux yet, so without
# lsof it refuses rather than passing unseen.
assert_loopback_only() {
  local name="$1" port="$2" addrs a bad=0
  if ! command -v lsof >/dev/null 2>&1; then
    echo "$name: lsof is not available, so it cannot confirm port $port is bound to loopback only; refusing (GA2.5)" >&2
    return 1
  fi
  addrs=$(port_bind_addresses "$port")
  if [ -z "$addrs" ]; then
    echo "$name: nothing visible to this user listens on port $port, so its bind address cannot be confirmed (GA2.5)" >&2
    return 1
  fi
  for a in $addrs; do
    case "$a" in
      "127.0.0.1:$port"|"[::1]:$port") ;;
      *) echo "$name: port $port listens on $a, not on loopback only (GA2.5)" >&2; bad=1 ;;
    esac
  done
  [ "$bad" -eq 0 ]
}
