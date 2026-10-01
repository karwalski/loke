# moke.proxy.guard — what /api/proxy may fetch (MK19.9)

Pure rules, no socket and no process, so every bypass encoding is testable as a string.

- `check(url; policy)` judges a URL: at most 2048 bytes; no space, control character or
  backslash; `https://` exactly; no userinfo and no `%` in the authority; port 443 (or the
  test-only loopback port); a canonical lower-case DNS name; every IP literal refused (a
  non-canonical IPv4 spelling — decimal, octal, hex, short — as non-canonical, a canonical one
  by its class); no local or internal name; the host exactly on the allowlist.
- `classify4` / `classify6` name the class of a blocked address: this network, private,
  CGNAT, loopback, link-local, cloud metadata (169.254.169.254, fd00:ec2::254), documentation,
  benchmarking, multicast, reserved, unique local, site-local, IPv4-mapped, IPv4-compatible,
  NAT64, 6to4, Teredo/IETF special-purpose, and anything outside 2000::/3.
- `addressesok(addrs; port; policy)` judges every address a name resolved to; one blocked
  address refuses the name.
- `production()` is the only policy the route uses: the allowlist from `MOKE_PROXY_ALLOW`
  (entries that are addresses or local names are dropped by `configured`), 4 MiB, 15 s, and
  no test override. `loopbackport` and `cafile` exist for tests only and no configuration sets
  them.
- `canonical(target)` rebuilds the URL from the parts that were judged.

Tests: `packages/moke/tests/test_proxy_guard.tk`.
