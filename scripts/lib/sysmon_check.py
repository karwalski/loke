#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Judge a /sysmon answer against the machine's own readings (BG1.2).

    sysmon_check.py <url> --loke-parent <pid>   # loke's /sysmon: loke is a process of that server
    sysmon_check.py <url> --loke-null           # moke's /sysmon with no loke: the loke entry is null

/sysmon reported 0 MB used, 0% RAM and 0% CPU on every machine, and an empty body on loke. A
status code said none of that, so this reads the body and compares each figure with what macOS
itself says, read here independently of loke's parsers (sysctl, vm_stat, top, ps). Prints one
line per check, "ok" or "FAIL", and exits 1 if any failed.

Tolerances, and why. The machine's figures move while they are read, so the dynamic ones are
bracketed: the machine is sampled immediately before and after the request.
  * cpu_count and total_ram_mb are hardware constants (hw.ncpu, hw.memsize), compared exactly.
  * used_ram_mb is compared with vm_stat's active + wired + compressed pages (the definition
    loke uses) and must lie within the two samples widened by 5% of total RAM. Measured on a
    16 GB machine under parallel builds, that sum moves by a few hundred MB between samples
    seconds apart; 5% (about 820 MB there) allows that and still fails a zero or a figure in
    the wrong unit.
  * cpu_percent is one top sample, an instantaneous reading. It must be above 0 (top itself is
    running, so the machine is never measured fully idle), at most 100, and within 30 points of
    the two samples: back-to-back samples on the same loaded machine were measured up to 23
    points apart. A constant 0, the old defect, fails the first condition.
  * loke's ram_mb is compared with ps's RSS for the pid it names, within 50% or 20 MB, whichever
    is larger: a server's resident memory changes between two reads, but not by that much.
"""
import json, re, subprocess, sys, urllib.request

fails = []
def check(cond, label, detail=""):
    print(("  ok   " if cond else "  FAIL ") + "/sysmon " + label + ("" if cond else ": " + detail),
          file=sys.stdout if cond else sys.stderr)
    if not cond:
        fails.append(label)

def run(*argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=30).stdout

def used_mb():
    out = run("vm_stat")
    page = int(re.search(r"page size of (\d+) bytes", out).group(1))
    def pages(name):
        return int(re.search(re.escape(name) + r":\s+(\d+)\.", out).group(1))
    return (pages("Pages active") + pages("Pages wired down") + pages("Pages occupied by compressor")) * page // 1048576

def busy():
    m = re.search(r"CPU usage:.*?([\d.]+)% idle", run("top", "-l", "1", "-n", "0", "-s", "0"))
    return 100.0 - float(m.group(1))

def proc(pid):
    out = run("ps", "-c", "-o", "ppid=,rss=,comm=", "-p", str(pid)).split()
    return (int(out[0]), int(out[1]) / 1024.0, out[2]) if len(out) >= 3 else None

url, mode = sys.argv[1], sys.argv[2]
ncpu = int(run("sysctl", "-n", "hw.ncpu"))
total = int(run("sysctl", "-n", "hw.memsize")) // 1048576
u0, b0 = used_mb(), busy()
with urllib.request.urlopen(url, timeout=60) as r:
    ctype, body = r.headers.get("Content-Type", ""), r.read().decode()
u1, b1 = used_mb(), busy()

check(ctype.startswith("application/json"), "is served as JSON", ctype)
try:
    d = json.loads(body)
except ValueError:
    check(False, "answers a JSON body", repr(body[:160]))
    sys.exit(1)
check(d.get("cpu_count") == ncpu, "cpu_count is hw.ncpu (%d)" % ncpu, str(d.get("cpu_count")))
check(d.get("total_ram_mb") == total, "total_ram_mb is hw.memsize in MiB (%d)" % total, str(d.get("total_ram_mb")))
used, lo, hi = d.get("used_ram_mb"), min(u0, u1) - total * 0.05, max(u0, u1) + total * 0.05
check(isinstance(used, int) and used > 0 and lo <= used <= hi,
      "used_ram_mb is vm_stat's active+wired+compressed (%d..%d MiB, +/-5%% of total)" % (min(u0, u1), max(u0, u1)), str(used))
check(d.get("free_ram_mb") == total - (used or 0), "free_ram_mb is total minus used", str(d.get("free_ram_mb")))
rp = d.get("ram_percent")
check(isinstance(rp, (int, float)) and used and abs(rp - used * 100.0 / total) < 0.5,
      "ram_percent is used over total", str(rp))
cpu = d.get("cpu_percent")
check(isinstance(cpu, (int, float)) and 0 < cpu <= 100 and min(b0, b1) - 30 <= cpu <= max(b0, b1) + 30,
      "cpu_percent is top's busy share (%.1f..%.1f%%, +/-30 points)" % (min(b0, b1), max(b0, b1)), str(cpu))
ol = d.get("ollama", "absent")
check(ol is None or (isinstance(ol, dict) and ol.get("pid", 0) > 0 and "ollama" in ((proc(ol["pid"]) or (0, 0, ""))[2])),
      "ollama is null or a running ollama process", json.dumps(ol))
lk = d.get("loke", "absent")
if mode == "--loke-null":
    check(lk is None, "loke is null, not zeros, when loke cannot be measured", json.dumps(lk))
else:
    parent = int(sys.argv[3])
    p = proc(lk["pid"]) if isinstance(lk, dict) and lk.get("pid", 0) > 0 else None
    check(p is not None and p[2] == "loke" and (lk["pid"] == parent or p[0] == parent),
          "loke is this server's process (pid %d or a worker it forked)" % parent, json.dumps(lk))
    if p:
        check(abs(lk.get("ram_mb", 0) - p[1]) <= max(20.0, p[1] * 0.5),
              "loke ram_mb is ps's RSS for that pid (%.1f MiB, +/-50%% or 20 MiB)" % p[1], json.dumps(lk))
sys.exit(1 if fails else 0)
