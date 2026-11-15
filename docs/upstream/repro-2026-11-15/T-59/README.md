# T-59 (B9) at toke v3.2.0 — scoped capability grants

`cap_probe.tk` is loke's `scripts/lib/cap_probe.tk` (copied 2026-11-15): one gated call per
class, chosen by the first argument, printing `<class>-done` only if the call returned. Each
`.toml` here is a manifest it is built with (`toke --config=<toml>`). toke tracks the ask as
**138.19** (design note `docs/decisions/138.19-scoped-capability-grants.md`, decisions D1-D5
with toke's owner, register item 3.4 of `docs/owner-decisions-2026-11-12.md`).

| manifest | run | EXPECTED (the ask) | DEFECT (as filed 2026-09-28) |
|---|---|---|---|
| `scoped_fs.toml` (`fs_read = "/nonexistent-dir-only"`) | `fs_read` (reads `/etc/hosts`) | refused (scope enforced), or the manifest rejected | `fs_read-done 1`: the scope widens to the class |
| `scoped_net.toml` (`net = "10.255.255.1:9"`) | `net` | refused, or the manifest rejected | `net-done`: the scope widens to the class |
| `loke.toml` (loke's grants, no `env_write`) | `env_write --allow-env` | a way to forbid launcher widening | `env_write-done`: the launcher adds the class |
| `envalias.toml` (`env = true`) | `env_write` | a warning, or no alias | `env_write-done` with no warning |
| `noenforce.toml` (`enforce = false`) | `fs_read` | not enforced, as `docs/reference/capabilities.md` said | `CAP001` (safe; the documentation is what is wrong) |

`run.sh T-59` prints one line with each outcome. Points 2 and 3 of T-59 (one `net` class for
listen and connect; `process_spawn` covers every program) are read from source, not measured.
