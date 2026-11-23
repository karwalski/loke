# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""The privacy-filter sidecar listens without a reverse-DNS lookup (story X8.13).

http.server.HTTPServer.server_bind calls socket.getfqdn on the bound address only to fill in
server_name. On the GitHub macOS runner that lookup of 127.0.0.1 took 35 s, so a stock server
did not listen for 35 s. A timing test alone cannot catch that on a machine whose resolver
answers at once, so every test here replaces socket.getfqdn with one that records the call
and then fails (in process) or stalls for 60 s (in the started sidecar): the result does not
depend on this machine's resolver.

transformers is replaced by a stub whose pipeline finds nothing, so no model is downloaded
or loaded; detection itself is not under test here.

Run: python3 packages/privacy-filter/test_server.py   (quality-gate.sh step_checks runs it)
"""

import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import types
import unittest
import urllib.request
from http.server import HTTPServer
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "server.py")
STUB_MODEL = "x8-13-stub-model"
# python3 starts and imports server.py in well under a second without transformers; the
# lookup this guards against took 35 s. Generous for a loaded CI runner, far below 35 s.
START_BOUND_S = 10.0


def _sidecar_env():
    env = dict(os.environ)
    env["LOKE_PF_MODEL"] = STUB_MODEL
    for k in ("LOKE_PF_REVISION", "LOKE_PF_THRESHOLD"):
        env.pop(k, None)
    return env


def _import_server():
    """server.py with transformers stubbed out, imported as a module (not __main__)."""
    stub = types.ModuleType("transformers")
    stub.pipeline = lambda **kw: (lambda text: [])
    with mock.patch.dict(sys.modules, {"transformers": stub}), \
            mock.patch.dict(os.environ, _sidecar_env(), clear=True), \
            mock.patch("sys.stdout", new=open(os.devnull, "w")), \
            mock.patch("sys.stderr", new=open(os.devnull, "w")):
        sys.modules.pop("pf_server_under_test", None)
        import importlib.util
        spec = importlib.util.spec_from_file_location("pf_server_under_test", SERVER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


class NoLookupOnBind(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = _import_server()

    def _forbidden_getfqdn(self):
        calls = []

        def getfqdn(name=""):
            calls.append(name)
            raise AssertionError("socket.getfqdn(%r) called while binding" % (name,))

        return calls, getfqdn

    def test_control_stock_server_does_look_up(self):
        # Without this the test below could pass because the patch missed, or because a
        # future Python stopped looking up the name, and prove nothing.
        calls, getfqdn = self._forbidden_getfqdn()
        with mock.patch("socket.getfqdn", getfqdn):
            with self.assertRaises(AssertionError):
                HTTPServer(("127.0.0.1", 0), self.server.Handler).server_close()
        self.assertEqual(calls, ["127.0.0.1"], "the stock HTTPServer resolves the bound host")

    def test_sidecar_server_binds_without_lookup(self):
        calls, getfqdn = self._forbidden_getfqdn()
        with mock.patch("socket.getfqdn", getfqdn):
            srv = self.server.Server(("127.0.0.1", 0), self.server.Handler)
        try:
            self.assertEqual(calls, [], "the sidecar's server does not call socket.getfqdn")
            self.assertEqual(srv.server_name, "127.0.0.1", "server_name is the bound host string")
            self.assertGreater(srv.server_port, 0, "server_port is the bound port")
            self.assertEqual(srv.server_port, srv.server_address[1])
            with socket.create_connection(("127.0.0.1", srv.server_port), timeout=2):
                pass
        finally:
            srv.server_close()


class StartsListeningPromptly(unittest.TestCase):
    def test_started_sidecar_answers_health_within_bound(self):
        # The sidecar's own __main__ path, in a fresh interpreter, with a resolver that would
        # stall for 60 s: /health must answer inside START_BOUND_S.
        boot = (
            "import socket, sys, time, types, runpy\n"
            "def stall(name=''):\n"
            "    sys.stderr.write('GETFQDN-CALLED %s\\n' % name); sys.stderr.flush()\n"
            "    time.sleep(60); return name\n"
            "socket.getfqdn = stall\n"
            "stub = types.ModuleType('transformers')\n"
            "stub.pipeline = lambda **kw: (lambda text: [])\n"
            "sys.modules['transformers'] = stub\n"
            "sys.argv = [sys.argv[1], '0']\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n"
        )
        t0 = time.monotonic()
        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", boot, SERVER],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_sidecar_env(), text=True,
        )
        try:
            lines = queue.Queue()
            threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout],
                             daemon=True).start()
            port, seen = None, []
            deadline = t0 + START_BOUND_S
            while port is None:
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                try:
                    line = lines.get(timeout=left)
                except queue.Empty:
                    break
                seen.append(line.rstrip("\n"))
                if "listening on http://127.0.0.1:" in line:
                    port = int(line.rsplit(":", 1)[1])
            self.assertIsNotNone(
                port, "the sidecar said it was listening within %.0f s (stdout: %r)"
                % (START_BOUND_S, seen))
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port,
                                        timeout=max(0.5, deadline - time.monotonic())) as r:
                body = json.loads(r.read())
            elapsed = time.monotonic() - t0
            self.assertEqual(body.get("model_id"), STUB_MODEL, "/health names the served model")
            self.assertTrue(body.get("ok"), "/health answers ok")
            self.assertLess(elapsed, START_BOUND_S,
                            "the sidecar answered /health %.2f s after start" % elapsed)
        finally:
            proc.kill()
            _, err = proc.communicate(timeout=5)
        self.assertNotIn("GETFQDN-CALLED", err, "the started sidecar never called socket.getfqdn")


if __name__ == "__main__":
    unittest.main()
