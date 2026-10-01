# moke.proxy.fetch — /api/proxy's fetch (MK19.9)

`handle(host; origin; ctype; body; policy)` is the whole endpoint minus HTTP plumbing:
Host must name this machine, a present Origin must be this machine, the body must be
`application/json` `{url, method: GET|POST, headers: [{name, value}], body}`. It answers a
JSON envelope: `{ok:true, status, contentType, body}` or `{ok:false, status, error}`, with
403 for a refusal, 400/415 for a bad request and 502 for an upstream failure.

`proxy(req; policy)`: `guard.check`, then `resolve` (system `getent ahosts`, else
`dscacheutil`), `guard.addressesok` on every address, then `fetchpinned`, which runs the
system curl with `--resolve host:port:<the judged address>`, `--proto =https`,
`--max-redirs 0`, `--max-filesize`, `--max-time`, `--noproxy '*'`, `-q`, `-g` and
`--data-raw`. A 3xx is refused as a redirect, a body that is not UTF-8 is refused.

Why curl and not std.http, measured against toke 3.1.0's source: the toke client resolves
inside connect and takes no address (no DNS-rebinding defence possible), reads the whole
body with no cap, and its only clock is a fixed 30-second per-read timeout. Filed as
MK19.11.

Tools are spawned by absolute path and only when they exist: at the pin, a failed spawn was
not detected by the `h == @()` idiom and the following wait blocked.

Tests: `packages/moke/tests/test_proxy_fetch.tk` (TLS stand-in on loopback).
