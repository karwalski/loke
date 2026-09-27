Privacy pipeline API endpoint. Exports `get` and `post`.

`post` is the only path in browser mode that reaches an external provider, and it does, in
order: open the store once (sentinel 0 on failure, never a result — T-18); check the kill
switch, treating an unreadable switch as ENGAGED; validate the input text; run the full core
privacy pipeline through `core.privacy.pipeline.runforward`; refuse with 503 when
`issafetoforward` reports that no detection layer scanned the text (NC1.9); evaluate
governance policy via `core.governance.policy.classifyrisk` and `evaluate`, auditing and
refusing with 403 on a deny (GA1.8); hold a require-approval decision with 409 and an approval id, and proceed only when a re-submission carries a valid, unexpired, single-use approval for the same request (GA5.26, `core.governance.approvalgate`); forward only the pipeline's anonymised text to
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
core.governance.policy, core.storage.audit and core.storage.db. GA1.5/GA1.6/GA1.7: forward now runs cache, then budget, then route, then dispatch. The provider is chosen by core.router.router.routerequest rather than by `if(str.len(anthropickey())>20)`, which sent a RESTRICTED request to Anthropic whenever a key happened to be configured and used two model ids that matched nothing in core.models.registry; the RESTRICTED-must-not-reach-cloud rule is re-checked here as well as inside routerequest, because this is the last line before a provider call. The semantic cache is consulted first, is keyed on the anonymised text and stores the anonymised response, and is used ONLY for requests carrying no entities — a cached response holds the placeholders of the request that produced it, and restoring it against a different request's map is a cross-request substitution. The budget is persisted in the settings store keyed by day number and verified by reading the value back, because setint returns i64!$lokeerr and T-18 makes its own report of success unreadable; the pre-flight estimate is zero because this repository has no tokeniser, so the check is against spend already recorded and is not described as a forecast. It deliberately does NOT call core.providers.dispatcher: json.enc of an @$chatmessage yields a pointer and json.enc of the undeclared $jsonobj yields a body carrying neither the model nor the messages, both measured, so the anthropic and openai request bodies cannot work and the hand-built bodies here are kept. A cloud provider with no client refuses rather than substituting another, and an empty Ollama body is now a 502 instead of a 200 with no text.

DA1.7/DA1.9: every dispatch reserves its `disclosure_log` row before transport, in ONE transaction with an `llm_dispatch` audit row (`core.audit.disclosure.reserveaudited`), and a reserve that cannot be written refuses the request with 503. The outcome audit row is written in one transaction with the completion (`completeaudited`), then the decision trace. The row carries the caller's optional `session_id` (validated before the scan, `none` when absent) and, for a local dispatch, the digest Ollama lists for the routed model as `model_version`; a cloud dispatch records `unknown`.
