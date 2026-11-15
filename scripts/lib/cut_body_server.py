#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""A local stand-in that answers in Ollama's shape and then cuts the body short. (F10.52)

Usage: cut_body_server.py <port-file>

It binds three consecutive ports on 127.0.0.1, the first free triple from 47980, 47983 or
47986 (all inside 47980-47989), and writes the first of them to <port-file> once all three
are listening. Each port answers every request with the same body, and differs only in how
that body ends:

  base     whole    : Content-Length is the body's length and the body is sent whole (the
                      control: a caller must succeed here, or the cut cases prove nothing)
  base+1   chunkcut : chunked, the whole body as one chunk, then the connection closes with
                      no last chunk
  base+2   stall    : Content-Length is the body's length plus 16, the body is sent, then
                      nothing until the client gives up (toke's per-read timer, 30 s)

The body sent before the cut is itself complete JSON, so a client that answered the cut
response as a success would hand its caller something that parses (T-64: toke 3.1.0 answered
the stall `$ok` with the short body). At toke 3.2.0 every client call answers `$err`.

A connection that sends nothing (the `nc -z` reachability probe) is closed unanswered.
"""
import socket
import sys
import threading
import time

BODIES = {
    "/api/tags": b'{"models":[{"name":"cut:1b","size":1,"digest":"sha256:cut"}]}',
    "/api/ps": b'{"models":[{"name":"cut:1b","size":1}]}',
    "/api/generate": b'{"model":"cut:1b","response":"partial answer","done":true}',
    "/api/chat": b'{"model":"cut:1b","message":{"role":"assistant","content":"partial answer"},"done":true}',
    "/api/pull": b'{"status":"success"}',
}
OTHER = b'{"ok":true,"status":"ok"}'


def readrequest(c):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = c.recv(65536)
        if not chunk:
            return None
        data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    want = 0
    for line in lines[1:]:
        k, _, v = line.partition(b":")
        if k.strip().lower() == b"content-length":
            want = int(v.strip() or b"0")
    while len(rest) < want:
        chunk = c.recv(65536)
        if not chunk:
            break
        rest += chunk
    parts = lines[0].split(b" ")
    path = parts[1].decode("latin-1") if len(parts) > 1 else "/"
    return path.split("?", 1)[0]


def answer(c, mode):
    try:
        path = readrequest(c)
        if path is None:
            return
        body = BODIES.get(path, OTHER)
        if mode == "whole":
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s" % (len(body), body))
        elif mode == "chunkcut":
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n%x\r\n%s\r\n" % (len(body), body))
            time.sleep(0.2)
        else:
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s" % (len(body) + 16, body))
            c.settimeout(45)
            try:
                while c.recv(65536):
                    pass
            except OSError:
                pass
    except OSError:
        pass
    finally:
        c.close()


def serve(s, mode):
    while True:
        c, _ = s.accept()
        threading.Thread(target=answer, args=(c, mode), daemon=True).start()


def bindtriple():
    for base in (47980, 47983, 47986):
        socks = []
        try:
            for p in range(base, base + 3):
                s = socket.socket()
                s.bind(("127.0.0.1", p))
                s.listen(16)
                socks.append(s)
            return base, socks
        except OSError:
            for s in socks:
                s.close()
    sys.exit("cut_body_server: no free port triple in 47980-47989")


def main():
    base, socks = bindtriple()
    for s, mode in zip(socks, ("whole", "chunkcut", "stall")):
        threading.Thread(target=serve, args=(s, mode), daemon=True).start()
    with open(sys.argv[1], "w") as f:
        f.write(str(base))
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
