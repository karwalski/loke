Privacy pipeline API endpoint. Exports `get` and `post`.

`post` is the only path in browser mode that reaches an external provider, and it does, in
order: open the store once (sentinel 0 on failure, never a result — T-18); check the kill
switch, treating an unreadable switch as ENGAGED; validate the input text; run the full core
privacy pipeline through `core.privacy.pipeline.runforward`; refuse with 503 when
`issafetoforward` reports that no detection layer scanned the text (NC1.9); evaluate
governance policy via `core.governance.policy.classifyrisk` and `evaluate`, auditing and
refusing with 403 on a deny (GA1.8); forward only the pipeline's anonymised text to
Anthropic or local Ollama; extract the provider's reply text with the typed `json.arr`
accessor; restore placeholders into that plain text via `core.privacy.placeholder.restore`
over a map derived from the deduped entity list with `mapfromentities` (GA1.2); and write one
row to the hash-chained audit trail via `core.storage.audit.insertevent` — including on a
provider failure, because a trail that records only successes describes a system that never
has an outage (GA1.4).

The response carries `response` (restored, what the user reads), `anthropic_raw` (the
anonymised body the provider actually returned, kept distinct on purpose), `audited`, and the
privacy metadata `entities_found`, `sensitivity`, `layers_completed`, `layers_degraded` and
`request_id`.

**Not on this path, deliberately.** Intelligent routing (GA1.7) — the provider is still
chosen by whether the Anthropic key is longer than twenty characters, because
`selector.select` returns a result whose error arm is dead under T-18, and a failed selection
read as a success could send restricted data to a cloud endpoint. Token optimisation (GA1.5),
the semantic cache (GA1.6 — `cache.lookup` structurally cannot return a hit), and the
keychain fallback for API keys. The cost figure in the audit row is 0.0 rather than an
estimate, because `calccost` returns an f64 across a module boundary and is corrupted until
LS1.1h lands.

**History worth keeping.** This file was 240 lines at `2b8942e` with restoration, policy and
audit all wired. `09b0a67`, a mechanical `tplrenderfile` sweep, cut it to 79 and removed every
call while keeping the imports; its message does not mention the file. This companion was
never updated, so it kept describing the working version — which is how the regression was
eventually found. GA1.10 recovered the intent, not the code: the lost version returned bare
sum variants (T-13), had two helpers whose whole body was a discarded trailing `mt` (T-19),
discarded `addentry`'s return with an off-by-one loop, and hardcoded a developer's home
directory (X8.5).

Depends on std.http, std.str, std.json, std.file, std, shared.log, shared.types,
core.privacy.pipeline, core.privacy.placeholder, core.governance.killswitch,
core.governance.policy, core.storage.audit and core.storage.db.
