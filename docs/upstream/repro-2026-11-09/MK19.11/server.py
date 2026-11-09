# MK19.11 stand-in servers, loopback only. Started and killed by PID by run.sh.
#   47971 drip : headers with Content-Length 8, then one body byte every DRIP seconds (default 5)
#   47972 stall: headers with Content-Length 8, three body bytes, then nothing for 45 s
#   47973 big  : a 64 MiB body of 'a', Content-Length set
import socket, sys, threading, time
DRIP = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
def serve(port, fn):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port)); s.listen(4)
    while True:
        c, _ = s.accept()
        threading.Thread(target=fn, args=(c,), daemon=True).start()
def head(c, n):
    c.recv(4096)
    c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % n)
def drip(c):
    try:
        head(c, 8)
        for b in b"abcdefgh":
            time.sleep(DRIP); c.sendall(bytes([b]))
    finally: c.close()
def stall(c):
    try:
        head(c, 8); c.sendall(b"abc"); time.sleep(45)
    finally: c.close()
def big(c):
    try:
        n = 64 * 1024 * 1024; head(c, n); chunk = b"a" * 65536
        for _ in range(n // 65536): c.sendall(chunk)
    except OSError: pass
    finally: c.close()
for p, f in ((47971, drip), (47972, stall), (47973, big)):
    threading.Thread(target=serve, args=(p, f), daemon=True).start()
while True: time.sleep(3600)
