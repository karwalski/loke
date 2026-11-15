# T-64 (2026-11-15) stand-in servers, loopback only. Started and killed by PID by run.sh.
#   47990 stall    : Content-Length 8, three body bytes, then nothing for 45 s
#   47991 chunkcut : chunked, one chunk "abc", then the connection closes with no last chunk
#   47992 closerst : no Content-Length, "abc", then the connection is reset (SO_LINGER 0)
#   47993 closeok  : no Content-Length, "abc", then a clean close (the control: $ok "abc")
import socket, struct, sys, threading, time
def serve(port, fn):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port)); s.listen(8)
    while True:
        c, _ = s.accept()
        threading.Thread(target=fn, args=(c,), daemon=True).start()
def stall(c):
    try:
        c.recv(65536)
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 8\r\nConnection: close\r\n\r\nabc")
        time.sleep(45)
    finally: c.close()
def chunkcut(c):
    try:
        c.recv(65536)
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n3\r\nabc\r\n")
        time.sleep(0.2)
    finally: c.close()
def closerst(c):
    try:
        c.recv(65536)
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nabc")
        time.sleep(0.2)
        c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    finally: c.close()
def closeok(c):
    try:
        c.recv(65536)
        c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nabc")
    finally: c.close()
for p, f in ((47990, stall), (47991, chunkcut), (47992, closerst), (47993, closeok)):
    threading.Thread(target=serve, args=(p, f), daemon=True).start()
while True: time.sleep(3600)
