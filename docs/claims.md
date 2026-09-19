# Claims Register

**Version:** 1.0
**Last updated:** 2026-09-19
**Story:** X6.1

Every externally-visible claim loke makes, mapped to the code that implements it and the test or
measurement that proves it. A claim that cannot be traced to both is not a claim loke is entitled to
make, and this file says so.

## Precedence and scope

[metrics-baseline.md](metrics-baseline.md) is the only source from which this project publishes
figures, and it takes precedence over this file and over every other page. **This register therefore
does not restate any figure.** Where a claim *is* a figure, the row names the claim and points at
metrics-baseline rather than repeating the number. If this file and metrics-baseline ever disagree
about a figure, metrics-baseline is right and this file is a bug.

Scope is the externally-visible surface: `README.md`, `docs/features-loke.md`,
`docs/features-moke.md`, `docs/architecture.md`, and the public site at loke.tokelang.dev. Internal
specification documents are out of scope unless a claim from one has escaped into the four files above.

## Verdicts

| Verdict | Meaning |
|---|---|
| `verified` | The code does what the claim says, and a named file and line prove it. It does **not** mean a figure has been measured or that a test exercises the path — the *Proof* column says which. |
| `partial` | The mechanism exists but the claim overstates it: narrower scope, an unwired path, a known defect, or a figure with no measurement. |
| `stub` | Code exists with the right shape and the wrong behaviour — a fixed return value, an ignored argument, a hardcoded result. Reads as implemented; is not. |
| `absent` | No implementing code was found. |

A row's *Proof* column names a committed test or measurement, or the story ID that would create one.
"No test" means no committed test exercises the production module. Because 54 of 86 test files
re-declare their subject rather than importing it (see [test-coverage.md](test-coverage.md)), a test
file merely *existing* for a module is not proof and is not recorded as such.

---

## Summary

| Verdict | Count |
|---|---|
| `verified` | 33 |
| `absent` | 26 |
| `partial` | 22 |
| `stub` | 14 |
| **Total** | **95** |

By subsystem:

| Subsystem | `verified` | `partial` | `stub` | `absent` | Rows |
|---|---|---|---|---|---|
| [A. Privacy detection and anonymisation](#a-privacy-detection-and-anonymisation) | 8 | 2 | 0 | 3 | 13 |
| [B. Multi-layer composition — epic F3b](#b-multi-layer-composition--epic-f3b) | 0 | 0 | 1 | 9 | 10 |
| [C. Token optimisation](#c-token-optimisation) | 3 | 2 | 0 | 1 | 6 |
| [D. Routing](#d-routing) | 3 | 2 | 1 | 2 | 8 |
| [E. Governance, audit and compliance](#e-governance-audit-and-compliance) | 5 | 2 | 5 | 1 | 13 |
| [F. Metrics and savings](#f-metrics-and-savings) | 0 | 2 | 2 | 0 | 4 |
| [G. Agents](#g-agents) | 2 | 2 | 1 | 2 | 7 |
| [H. Memory](#h-memory) | 4 | 1 | 1 | 2 | 8 |
| [I. MCP](#i-mcp) | 3 | 0 | 0 | 1 | 4 |
| [J. Local inference — epic F2](#j-local-inference--epic-f2) | 0 | 3 | 0 | 2 | 5 |
| [K. Interfaces and runtime modes](#k-interfaces-and-runtime-modes) | 5 | 2 | 3 | 1 | 11 |
| [L. Testing, coverage and build](#l-testing-coverage-and-build) | 0 | 4 | 0 | 2 | 6 |

Of the 33 `verified` rows, **6** are proved by a committed test that imports the production module —
A8 (`tests/unit/privacy/test_log_sanitiser.tk`), A9 (`tests/integration/test_keychain_e2e.tk`), A12
and D7 (`tests/integration/test_privacy_pipeline_e2e.tk`), E1
(`tests/integration/test_policy_evaluation_e2e.tk`) and K7
(`tests/unit/browser/test_settings_handler.tk`). The other 27 are verified by reading the code;
nothing automated defends them against regression. That gap belongs to epics VM1 and T15, not to
documentation.

Two patterns account for most of the non-`verified` rows. The first is **written but unwired**: a
module compiles, is documented as a feature, and has zero importers — all of section B, plus D6, J1
and K3. The second is **shape without behaviour**: a function with the right signature returning a
fixed value — E5–E9, F1, F2, G2, K2–K4.

Two findings dominate the rest.

**The browser's live request path does not use the privacy pipeline (A13).** The route registered for
`/api/pipeline` calls the sidecar over HTTP and, when the sidecar does not answer, falls through to
five literal column-name checks that increment a counter without altering the text — and then posts
that unaltered text to the provider while reporting an entity count and a sensitivity label. None of
the nine capabilities claimed for that path at `docs/features-loke.md:52` is present on it. This is the
one finding with a live disclosure consequence rather than an evidence consequence, and it invalidates
the unqualified form of A11 and K6.

**The audit trail is never written (E4).** `core.storage.audit::logevent` has no callers anywhere in
the tree, and nothing else inserts into `audit_log`. The claim that the ledger is "wired into every
browser and CLI request path" is `absent`, not merely "not tamper-evident". Every downstream claim —
report generation, compliance evidence, the governance dashboard's request log, the scorecard — rests
on a table that stays empty. See [E. Governance, audit and compliance](#e-governance-audit-and-compliance).

---

## A. Privacy detection and anonymisation

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| A1 | "Regex detector — 10 patterns (email, phone, credit card, TFN, SSN, IP, API key)" | `README.md:119`, `docs/features-loke.md:29` | `verified` | `packages/core/src/privacy/regex.tk:20-31` — `getpatterns()` returns exactly 10 `$patterndef` entries; the pattern strings themselves are in `packages/core/src/privacy/patterns.tk` | **Measured** — the regex-layer recall and precision figures in [metrics-baseline.md](metrics-baseline.md#measured), scored against `tests/fixtures/pii-corpus` (N=74 cases, seed 20260919). Note that measurement's own caveat: the pattern strings are read from the tree but evaluated with Python's regex engine, not toke's. No committed `.tk` test imports the module — `tests/unit/privacy/test_regex_detector.tk` re-declares the patterns. AD1.2, AD1.3 | The count of ten is correct. The measurement found what reading the code did not: four of the claimed entity types have **no detector at all**, two nine-digit patterns have no checksum and collide with each other, and the email pattern is case-sensitive. See metrics-baseline for the detail — this row is verified as a count, not as coverage |
| A2 | Per-pattern confidence "0.60–0.99" | `docs/features-loke.md:29` | `verified` | `packages/core/src/privacy/regex.tk:21-30` — literal confidences from 0.60 (`url`) to 0.99 | No calibration test; the values are hand-assigned. AD1.4 | The range is accurately transcribed from the code. The numbers are declarations, not measured precisions — and the measurement in [metrics-baseline.md](metrics-baseline.md#measured) puts layer precision at well below the lowest declared confidence, so the declared values should not be read as precision estimates |
| A3 | "Local NER — SLM-based entity recognition via Ollama" | `README.md:120`, `docs/features-loke.md:30` | `verified` | `packages/core/src/privacy/ner.tk`; imported by `packages/core/src/privacy/pipeline.tk:10` | No test — requires a running Ollama. AD1.1, AD1.3 | — |
| A4 | "Presidio — 180+ entity types via optional Python sidecar" | `README.md:121`, `docs/features-loke.md:31` | `partial` | `packages/core/src/privacy/presidio.tk`; imported by `pipeline.tk:9` | No test — requires a sidecar loke neither bundles nor starts. AD1.3 | A REST client exists. loke does not bundle, start or detect Presidio (`docs/architecture.md:230` states this). "180+" is Presidio's own published count, not loke's measurement |
| A5 | "Privacy Filter sidecar — OpenAI Privacy Filter model (1.5B params)" | `README.md:122` | `verified` | `packages/privacy-filter/server.py:31-36` loads `openai/privacy-filter` via `transformers.pipeline`; `/detect` and `/anonymise` at `:53`, `:98` | No test. AD1.3 | The sidecar is real and runs a real published model. Whether loke can *reach* it is a separate claim — see B9 |
| A6 | "Generates `[ENTITY_TYPE_N]` tokens … Restores placeholders in LLM responses to original values" | `docs/features-loke.md:54` | `partial` | `packages/core/src/privacy/placeholder.tk:26` (`makeplaceholder`), `:42` (`restore`) | No test importing the module. PL1.2 | Restore works, but the loop bound at `placeholder.tk:46` is `i>len` where valid indices end at `len-1`, so it iterates one index past the end of the entry array. Live off-by-one, tracked as PL1.2 |
| A7 | "guardian prompt injection" | `README.md:112`, `docs/features-loke.md:52` | `verified` | `packages/core/src/privacy/guardian.tk:10-27` (prompt text), `:29` (`buildsystemprompt`), `:38` (`isguardianpresent`); imported by `pipeline.tk:13` | No test importing the module. AD1.5 would measure whether the prompt resists anything | The prompt exists and is injected. Its effectiveness against injection has never been measured |
| A8 | "Log redaction — all log output auto-redacted for PII before writing" | `README.md:124`, `docs/features-loke.md:115` | `verified` | `packages/core/src/privacy/logsanitiser.tk:6` (`sanitise`), called at `packages/shared/src/log.tk:27,39,51,63` — all four levels | `tests/unit/privacy/test_log_sanitiser.tk` imports the production module | Redaction is regex-only, so it inherits regex's recall — it will not redact a name |
| A9 | "OS keychain — API keys stored in macOS Keychain, never in plaintext" | `README.md:123`, `docs/features-loke.md:111` | `verified` | `packages/core/src/storage/keychain.tk:6-40`, `packages/core/src/config/keychain.tk` | `tests/integration/test_keychain_e2e.tk` imports the production module | — |
| A10 | "Database encryption … Database encryption is **not** currently active" | `README.md:125-129`, `docs/features-loke.md:101-107` | `absent` | `packages/core/src/storage/db.tk:37-43` issues `PRAGMA key`; the toolchain links plain SQLite, which ignores it and returns success | `packages/core/src/governance/compliance.tk:91-95` already reports this honestly. X8 | Already stated accurately in both documents and in [metrics-baseline.md](metrics-baseline.md). The database is plaintext on disk |
| A11 | "Every code path in this repository that sends a prompt to an external provider routes it through the filter first" | `README.md:114-117`, `docs/architecture.md:214-219` | `absent` | `packages/core/src/privacy/pipeline.tk` is imported by the CLI proxy, the MCP broker, the MCP server, the agent executor and the response scanner — **not by the browser's live request path**. See A13 | `tests/integration/test_privacy_pipeline_e2e.tk` exercises the core pipeline in isolation, not the browser route. AD1.6 | Already qualified in both files as a review-enforced invariant rather than a host property — but the invariant **does not currently hold**. The browser `/api/pipeline` route sends the user's text onward without invoking the filter whenever the sidecar is unavailable (A13) |
| A12 | Sensitivity escalation "PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED" | `docs/features-loke.md:52` | `verified` | `packages/core/src/privacy/regex.tk:35` (`ishighersensitivity`), `packages/core/src/privacy/pipeline.tk` | `tests/integration/test_privacy_pipeline_e2e.tk` | Verified in the core pipeline. The browser route computes its own two-threshold approximation instead (A13) |
| A13 | "The browser handler now calls the core privacy pipeline directly (GA1.1-GA1.8 completed) — all browser traffic flows through the full detection stack, response restoration, kill switch check, audit logging, token optimisation, semantic cache, intelligent routing, and governance policy evaluation" | `docs/features-loke.md:52`; implied by `README.md:225`, `docs/architecture.md:96-133` | `partial` | At **HEAD**, `packages/browser/pages/api/pipeline.tk` imports thirteen modules including `core.privacy.pipeline`, `core.privacy.placeholder`, `core.governance.killswitch`, `core.storage.audit` and `core.governance.policy`, and calls `pipe.run()` (`:125`), `ph.restore()` (`:195`), `ks.isengaged()` (`:116`), `policy.evaluate()` (`:138`) and `audit.logevent()` (`:217`). Five of the nine clauses hold. **Four do not:** there is no call to any optimiser, no semantic-cache lookup, and no `selector.select()` — the provider is chosen by an if/else on whether an Anthropic key is longer than twenty characters (`:152-159`) | `tests/unit/browser/test_pipeline_handler.tk` imports the handler but asserts on its JSON shape, not on whether anonymisation occurred. GA1.5, GA1.6 and GA1.7 need reopening; NC1.3, AD1.6, X8.6 | **Corrected 2026-09-19.** This row previously read `absent` and described a four-import handler that posted raw text. That described the **uncommitted working-tree copy** of `pipeline.tk`, not the repository: the earlier audit read the working tree as if it were the committed state. At HEAD the wiring is real but incomplete. Two things follow. First, the working-tree copy is a **regression that strips all nine core imports** and must not be committed (F10.13, X8.5). Second, the fail-open is a **core** defect rather than a browser one: `packages/core/src/privacy/pipeline.tk:568-582` initialises `anonymisedtext` to the raw input and reassigns it from `anonymisetext(text; deduped)`, so when both detection layers are unreachable — logged as degraded mode at `:392`, `:523`, `:540` and not failed — `deduped` is empty and the raw text is what gets sent (NC1.9) |

## B. Multi-layer composition — epic F3b

Epic F3b is marked **Done** across all eleven stories in
[epics-and-stories.md](epics-and-stories.md) (Epic F3b, stories F3b.1–F3b.11). Ten of its modules have **zero importers**: they
compile, they are documented as features, and no code path reaches them. The pipeline orchestrator
uses its own de-duplication instead. Tracked as AD1.7 — wire them or withdraw the claim.

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| B1 | Four consensus strategies: `most-restrictive` (default), `first-match`, `unanimous`, `majority` | `docs/features-loke.md:39-46`; strategy names also in the compliance table at `:262-264` | `stub` | `packages/core/src/privacy/consensus.tk:24-38` | No test of behaviour (`tests/unit/privacy/test_consensus.tk` re-declares the module). AD1.7 | `resolveoverlaps()` accepts a `strategy` argument and ignores it, marking every detection `action:"mask"` — one behaviour, not four. `strategyname()` at `:42` returns the four names as display strings. The module has no importers |
| B2 | "Entity Routing … Different entity types assigned to the layer that handles them best" | `docs/features-loke.md:48` | `absent` | `packages/core/src/privacy/entity_routing.tk` exists; zero importers | AD1.7 | No pipeline path reads an entity-routing configuration. All layers run on all text |
| B3 | "Layer Health … System degrades gracefully … Reports HEALTHY or DEGRADED" | `docs/features-loke.md:50` | `absent` | `packages/core/src/privacy/layer_health.tk` exists; zero importers | AD1.7 | Degradation happens by each layer's own `isavailable()` check (e.g. `ner.tk:19`), not by the health module. Nothing aggregates or reports a HEALTHY/DEGRADED status |
| B4 | Layer ordering and trust configuration via `[[privacy.layers]]` | F3b.2 (backlog, **Done**); no claim in the four public files | `absent` | `packages/core/src/privacy/layer_config.tk` exists; zero importers | AD1.7 | The orchestrator runs a fixed layer order hardcoded in `pipeline.tk`. `priority`, `mode` and `veto` are not read |
| B5 | "Evaluation Mode … precision, recall, F1 score per layer" | `docs/features-loke.md:56` | `absent` | `packages/core/src/privacy/evaluation.tk` exists; zero importers. No `privacy evaluate` command in `packages/cli/src/commands.tk` | AD1.3 | There is no way to invoke it and no labelled corpus to invoke it against (AD1.1) |
| B6 | "Metrics … detection count, processing time, average confidence, entity counts per layer" | `docs/features-loke.md:58` | `absent` | `packages/core/src/privacy/filter_metrics.tk` exists; zero importers | DA1.4, AD1.7 | Nothing records per-layer metrics |
| B7 | Filter registry with `register`/`list`/`get`/`remove` | F3b.1 (backlog, **Done**) | `absent` | `packages/core/src/privacy/filter_registry.tk` exists; zero importers | AD1.7 | Layers are wired by direct import in `pipeline.tk:8-13`, not registered |
| B8 | Organisation-managed layer policies overriding user settings | F3b.8 (backlog, **Done**); `packages/privacy-filter/sample-org-policy.json` | `absent` | `packages/core/src/privacy/org_policy.tk` exists; zero importers | AD1.7 | A sample policy file ships; no code enforces it |
| B9 | Sidecar integration — the OpenAI Privacy Filter as a pipeline layer | `docs/features-loke.md:32`, `README.md:122` | `absent` | `packages/core/src/privacy/sidecar_client.tk` exists; zero importers | AD1.4 | The sidecar runs (A5) and nothing in loke calls it. The client also returns unparsed response strings with no timeout or retry |
| B10 | The sidecar's declared operating point | `packages/privacy-filter/models.json:18` | `absent` | No application site. `server.py:57-77` (`/detect`) and `:98-127` (`/anonymise`) return every classifier span regardless of score | AD1.4 | `confidence_threshold` is stored in the registry and in `/models/add` (`server.py:163`) and never applied. There is no operating point to tune and no precision/recall curve to report |

## C. Token optimisation

No combined figure is published. The withdrawn reduction, compression and cache-hit figures are named
in [metrics-baseline.md](metrics-baseline.md#withdrawn-figures) and are **not restated here**.

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| C1 | "TOON format — a token-efficient serialisation for structured data" | `README.md:137-138`, `docs/features-loke.md:70` | `partial` | `packages/core/src/optimiser/toon.tk`; `measuresavings()` at `:282-290` | `tests/integration/test_toon_roundtrip.tk` imports the production module | Already correctly qualified in both files: the saving computed in code is a **character-length** ratio (`str.len` over `str.len`), not a token count. VM1.7 |
| C2 | "LLMLingua compression — client implemented; requires a sidecar service this repository does not bundle" | `README.md:139-140`, `docs/features-loke.md:71` | `partial` | `packages/core/src/optimiser/llmlingua.tk:22-90` | No test — no sidecar to test against | Already correctly qualified. The path is inert out of the box |
| C3 | "Semantic caching — real vector-similarity lookup at a 0.92 threshold" | `README.md:141-142`, `docs/features-loke.md:72` | `verified` | `packages/core/src/optimiser/cache.tk:37` — `threshold:0.92` | No test of hit behaviour. VM1 for any hit-rate figure | The mechanism and the threshold are real. The hit rate is workload-dependent and has never been measured here — see metrics-baseline |
| C4 | "Token budget — Daily/weekly/monthly limits with pre-flight cost estimates" | `docs/features-loke.md:73` | `verified` | `packages/core/src/optimiser/budget.tk`, `budget_types.tk` | No test importing the module | — |
| C5 | Combined token-reduction, compression-ratio and cache-hit figures | Withdrawn; named in [metrics-baseline.md](metrics-baseline.md#withdrawn-figures) | `absent` | None — no harness combines the mechanisms and measures the composite | VM1.1, VM1.7 | Withdrawn. Cite metrics-baseline; do not reinstate from an older document or a slide |
| C6 | "Local routing — a task handled on-device costs nothing in API tokens" | `README.md:143` | `verified` | Tautologically true of any local-inference path; `packages/core/src/router/latency_router.tk:53` restricts the interactive tier to local models | No measurement of what fraction of tasks this covers. CB1.5 | True and uninformative without the local/cloud ratio, which is not measured (F2) |

## D. Routing

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| D1 | "Intent Classification … embedding-based classifier" | `docs/features-loke.md:80` | `stub` | `packages/core/src/router/intent.tk:55-67` (`classifyfast`) | No test importing the module | A cascade of `str.contains` substring checks returning a literal `method:"keyword"`. There is no embedding model. `README.md:157-159` already describes it correctly as a keyword and pattern cascade; features-loke does not |
| D2 | Intent classification latency | Figure withdrawn; named in [metrics-baseline.md](metrics-baseline.md#withdrawn-figures). Restated at `docs/features-loke.md:80,273` | `absent` | None — no timing test exists anywhere in the tree | VM1.1 (no numeric result sink), VM1.3 | Withdrawn. The remaining appearances in features-loke are marked as unmeasured targets under X6.2 |
| D3 | "Strategies: cheapest-adequate, fastest, best-quality, local-first" | `docs/features-loke.md:86`; F5.3 (backlog, **Done**) | `absent` | None. Zero matches for any of the four names across `packages/` and `src/` | — | One fixed selection path exists in `packages/core/src/router/selector.tk`. The four strategies are not implemented, not configurable, and not selectable. `README.md:157-159` already says so |
| D4 | "three inference tiers: Interactive, Considered, Background" | `README.md:155-156` | `verified` | `packages/core/src/router/latency_router.tk:18-49` — `constraintinteractive`, `constraintconsidered`, `constraintbackground`, dispatched by `constraintfor()` | No test importing the module | The tiers and their latency budgets exist as declarations. Whether hardware meets them is unmeasured (F2, J1) |
| D5 | "Latency Tolerance … instant (<2s), patient (<30s), background (minutes-hours)" | `docs/features-loke.md:90` | `partial` | `packages/core/src/router/latency_router.tk:18-49` | No test | The tiers are named `interactive` / `considered` / `background` in code, not `instant` / `patient` / `background`, and their budgets are declarations rather than measurements |
| D6 | "RouteLLM Integration: Cost-signal integration via REST" plus its cost-reduction and quality-retention figures | `docs/features-loke.md:92` | `partial` | `packages/core/src/router/routellm.tk:61` (`query`), `:72` (`isavailable`); **zero importers** | — | A REST client exists and nothing calls it. The two figures are third-party numbers repeated with no citation, workload or quality definition — withdrawn in [metrics-baseline.md](metrics-baseline.md#withdrawn-figures) |
| D7 | "Sensitivity Scoring … Derives PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED" | `docs/features-loke.md:82` | `verified` | `packages/core/src/router/sensitivity.tk`; `packages/core/src/privacy/regex.tk:35` | `tests/integration/test_privacy_pipeline_e2e.tk` | — |
| D8 | "Model registry: Ollama, Anthropic, OpenAI, Google, Mistral, OpenRouter, local inference" | `docs/features-loke.md:87` | `verified` | `packages/core/src/providers/anthropic.tk`, `openai.tk`, `ollama_provider.tk`, `dispatcher.tk`; registry entries in `packages/core/src/router/selector.tk` and `router.tk` | `tests/unit/providers/test_*.tk` re-declare rather than import; no proof. T15 | Only three provider adapters exist as modules — Anthropic, OpenAI and Ollama. Google, Mistral and OpenRouter appear as registry entries in `selector.tk`/`router.tk` with no adapter behind them, so the row overstates the registry. Only the three real adapters are exercised by moke |

## E. Governance, audit and compliance

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| E1 | "risk classification" / "Risk classification (low/medium/high) based on sensitivity × use case risk × cost" | `README.md:161`, `docs/features-loke.md:121` | `verified` | `packages/core/src/governance/policy.tk:16` (`classifyrisk`), `:43-74` (`evaluate*`), `:76` (`controlsforrisk`) | `tests/integration/test_policy_evaluation_e2e.tk` imports the production module | — |
| E2 | "graduated warnings (info/advisory/caution/block)" — four levels | `README.md:162`, `docs/features-moke.md:24` | `verified` | `packages/moke/templates/chat.tkt:376-382` (styles), `:711-733` (`showWarning`), used at `:791`, `:2391`, `:2798-2801` | No automated test; visible in the UI | Implemented in moke's template, not in core. A core consumer would have to re-implement it |
| E3 | "regulatory policy presets (GDPR, HIPAA, AU Privacy Act, CCPA)" | `README.md:162-163`, `docs/features-loke.md:260-264` | `verified` | `packages/core/src/policy/presets/gdpr.tk`, `hipaa.tk`, `au-privacy.tk`, `ccpa.tk`, `remaining.tk` | No test importing the presets | The presets are policy definitions loke ships. `README.md:172-173` already states they do not make a deployment compliant. RG1.4, RG1.5 |
| E4 | "an append-only interaction ledger" / "Append-only log with hash chain for tamper detection … **Now wired into every browser and CLI request path (GA1.4)**" | `README.md:161`, `docs/features-loke.md:109` | `absent` | `packages/core/src/storage/audit.tk:27` (`logevent`) — **no callers anywhere**. `audit_log` (`packages/core/src/storage/migrations.tk:33-51`) is written by nothing. `packages/browser/extensions/core.tk:61` — `getauditstore()` returns `0` | `tests/integration/test_audit_trail_e2e.tk` imports production code but cannot demonstrate a write from a request path, because none exists. GA5, DA1 | **The audit trail is never written.** The only insert statement in the tree is inside `logevent`, and the only importer of the module is `report-engine.tk`. The "wired into every request path" claim is false. Everything downstream — reports, compliance evidence, the governance request log — reads an empty table |
| E5 | "hash chain for tamper detection" | `docs/features-loke.md:109`; `README.md:165-169` already withdraws it | `stub` | `packages/core/src/storage/audit.tk:38` — `str.concat(event.correlationid;event.eventtype)`. `src/core/audit/trail.tk:80` — `chainhash()` returns `str.fromi32(str.len(acc))`; `:92` — `verifychain()` is `<true` | No test. GA5.2, GA5.3, GA5.4 | The stored digest concatenates two non-secret fields, is not a cryptographic hash, and ignores the `prev_hash` column it is written alongside. The duplicate implementation in `src/` returns a string length as a hash and a constant `true` as verification. No verifier exists on either path |
| E6 | Audit records carry a timestamp | `docs/architecture.md:206`, implied by `docs/features-loke.md:109` | `stub` | `packages/core/src/storage/audit.tk:47` — the `created_at` value in the `INSERT` is the **string literal** `'now()'`, not a SQL call | No test. GA5.1 | Every row would carry the six-character text `now()` as its creation time. No row-level ordering or period filtering is possible |
| E7 | "Decision Trace: Captures full pipeline path — original input, PII detected … de-anonymisation" | `docs/features-loke.md:129` | `stub` | `packages/core/src/governance/trace.tk:17` — a 17-field `$decisiontrace` with `newtrace`, `addstep`, `record*`, `tojson`; **no callers**, no table, no insert. Duplicate at `src/governance/trace.tk` | No test. GA5.5 | The type and its serialiser exist. Nothing constructs a trace, nothing persists one, and there is no migration for a trace table |
| E8 | "Compliance Reporting: Generate reports as inline, CSV, or JSON" for GDPR / HIPAA / AU Privacy Act / CCPA | `docs/features-moke.md:296-297`, `docs/features-loke.md:190` | `stub` | `packages/core/src/governance/report-engine.tk:86,104,122,140,158` | No test. GA5.6 | All five report queries `SELECT timestamp, event_type, detail FROM audit_log`. `audit_log` has neither a `timestamp` column nor a `detail` column (`migrations.tk:35-51` — the columns are `created_at` and a fixed metadata set). Every query fails. moke's Governance page uses its own `packages/moke/src/governance.tk:135` (`generatereport`) over in-session events instead, which works but evidences only that session |
| E9 | Compliance checks report control status | `docs/features-moke.md:296`, governance dashboard | `stub` | `packages/core/src/governance/compliance.tk:42-56` (GDPR: three `PASS`), `:82-90` (HIPAA: two `PASS`) | No test. GA5.7 | The privacy and audit controls are hardcoded `PASS` without querying the store. Given E4, the audit control is asserted to pass while the trail is empty. Note that the same file is honest about encryption at `:91-95` |
| E10 | "Kill switch (global/per-provider/per-agent)" / "checked before every AI call" | `README.md:161`, `docs/features-loke.md:123`, `docs/architecture.md:220` | `partial` | `packages/core/src/governance/kill_switch.tk`; imported by `packages/core/src/governance/gateway.tk` and `external.tk` only | `tests/integration/test_kill_switch_e2e.tk` imports the production module | The switch and its scopes are real and tested. "Before every AI call" holds only for calls that go through the governance gateway; no mechanism enforces that every provider dispatch does. Same class of gap as A11 — AD1.6 |
| E11 | "Monitoring … Incident types … Severity levels, post-incident review templates, trend tracking" | `docs/features-loke.md:131` | `verified` | `packages/core/src/governance/monitoring.tk` | No test importing the module | The types and transitions exist. Nothing feeds them, because nothing writes the audit trail (E4) |
| E12 | "Scorecard: Privacy %, compliance violations, risk tier breakdown … Trend charts (7d/30d/90d)" | `docs/features-loke.md:133` | `partial` | `packages/core/src/governance/scorecard.tk` | No test. EM1.4 | The computation exists; its inputs are the audit trail (E4) and the metrics tables (F1, F2), so every figure it produces is zero or empty |
| E13 | Presets "make you compliant" framing | Not asserted in the four files — `README.md:172-173` explicitly disclaims it | `verified` | Disclaimer text at `README.md:172-173`; presets at `packages/core/src/policy/presets/gdpr.tk` and siblings | RG1.4, RG1.5 for remaining instances elsewhere | Correctly stated already — the claim here is the *absence* of a compliance assertion, and the disclaimer is present. Keep it that way |

## F. Metrics and savings

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| F1 | `/api/savings` — "Token savings dashboard data" | `docs/features-loke.md:190` | `stub` | `packages/core/src/audit/metrics.tk:37` (`summary`), `:59` (`byprovider`), `:63` (`tokensavingsseries`), `:67` (`cachestats`), `:85` (`export`) | No test. DA1.6 | Every function returns a zero-filled struct or an empty array; `export()` returns `""`. The endpoint serves zeros |
| F2 | Metrics collection per request | Implied by F1 and by the governance dashboard | `stub` | `packages/core/src/metrics/collector.tk:59` inserts into `metrics_raw`; `:96` selects from it | No test. DA1.2, DA1.3 | No migration creates `metrics_raw`, so both statements would fail. Nothing calls `collector.record` in any case |
| F3 | "Cost tracking — Pre-send token/cost estimation, session stats, savings vs cloud" | `README.md:207`, `docs/features-moke.md:24` | `partial` | `packages/moke/src/cost_comparison.tk:15,62,72,97`, `packages/moke/src/token_optimisation.tk:29,57-58` | No test. CB1.5, VM1.7 | moke computes its own per-session estimates and does not depend on F1/F2, so the UI shows real arithmetic. The "savings" are an estimate against a modelled cloud price using a character-derived token count (`token_optimisation.tk:57-58`), not a measured token saving. No figure from it is publishable — see metrics-baseline |
| F4 | "Privacy score (% of requests with no violations)" | `docs/features-moke.md:287` | `partial` | `packages/moke/templates/governance.tkt`, `packages/moke/src/governance.tk` | No test. EM1 | Computed over in-session events held in the page, not over a persisted ledger. It resets on reload and is not evidence of anything over a period |

## G. Agents

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| G1 | "capability-scoped execution with path, tool and cost limits" | `README.md:176-177` | `verified` | `packages/core/src/agents/sandbox.tk:29` (`newsandbox`), `:40-123` (path, name and permission checks), `:125` (`sandboxreadfile`), `:144` (`sandboxhttpget`), `:162` (`checkcostlimit`) | No test importing the module. T15 | Enforcement is in-process capability checking. `README.md:184` already states it is not process isolation — toke exposes no sandboxing primitive (`process.tki` offers spawn/wait/kill with no jail, resource cap or syscall filter) |
| G2 | "Scheduling & Triggers: Cron schedules" | `docs/features-loke.md:141` | `stub` | `packages/core/src/agents/scheduler.tk:21-30` (`checkcron`) | No test. Backlog: general cron parsing | Three literal strings are matched by exact equality (`"0 * * * *"`, `"0 2 * * *"`, `"0 2 * * 0"`); everything else returns "unrecognised cron pattern". **Worse than a missing parser:** `checkcron` also ignores the current time, and `checkdue` discards its `currenttimeepoch` argument, so a matching literal reports `shouldrun:true` on *every* check rather than at its scheduled time. `README.md:181-182` states the three-schedule limit but not the time-blindness |
| G3 | "webhook triggers, MCP event triggers" | `docs/features-loke.md:141` | `absent` | `packages/core/src/agents/scheduler.tk:36-40` | — | Both branches return a fixed `shouldrun:false` with a "event-driven" reason. No event source exists. `README.md:181-182` already says the scheduler does not fire them |
| G4 | "file change triggers" | `docs/features-loke.md:141` | `absent` | `packages/core/src/agents/scheduler.tk:38` | — | Returns `shouldrun:false` with "file watching handled separately". No file watcher exists |
| G5 | "Chained execution with circular dependency detection" | `docs/features-loke.md:141` | `partial` | `packages/core/src/agents/` | No test | Chain metadata is modelled; no scheduler path executes a chain, because G2–G4 mean nothing fires automatically |
| G6 | "Overnight Batch: Low-power mode 11pm–7am (configurable), full resource allocation, morning digest" | `docs/features-loke.md:147`, `README.md:177` | `partial` | `packages/core/src/agents/overnight.tk`, `packages/core/src/agents/latency.tk` | No test | The queue and window logic exist. Nothing schedules into them (G2), and `loke overnight status` is a fixed string (K4) |
| G7 | "Templates: Daily digest, code review assistant, expense categoriser, meeting prep, documentation updater, security scanner" | `docs/features-loke.md:145` | `verified` | `packages/core/src/agents/templates.tk:12-165` — seven `$agentdef` templates (`daily-digest`, `nightly-code-reviewer`, `doc-freshness-checker`, `weekly-security-scan`, `meeting-prep`, `expense-categoriser`, `documentation-updater`), with `findtemplate` at `:166` and `install` at `:186` | No test importing the module | Seven templates ship, not six, and two of the names differ from the list in features-loke. Definitions and the install path exist. Whether any of them ever runs depends on G2 |

## H. Memory

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| H1 | "Knowledge Graph … Entity extraction, relationship mapping, temporal validity windows, contradiction detection" | `README.md:177-178`, `docs/features-loke.md:159` | `verified` | `packages/core/src/memory/graph.tk:35` (`upsertentity`), `:55` (`addrelation`), `:121` (`neighbours`, depth-bounded traversal), `:227` (`searchentities`), `:246` (`deleteentity`) | No test importing the module. T15 | Traversal and storage are real. "Graph visualisation" is moke's UI, not core |
| H2 | "Memory MCP Server … `memory.search`, `memory.store`, `memory.facts`, `memory.context`, `memory.diary_write/read`, `memory.status`" | `README.md:178`, `docs/features-loke.md:163` | `verified` | `packages/core/src/memory/mcp_server.tk:21` (`memorytools`) plus a handler per tool at `:113`, `:142`, `:167`, `:197`, `:244`, `:253` | No test importing the module | The tool surface is real. `memory.search` inherits H3 |
| H3 | "Semantic Search … Local embeddings only" | `docs/features-loke.md:155` | `stub` | `packages/core/src/memory/search.tk:104-130` (`search`) | No test importing the module | The query is `SELECT drawer_id, SUM(weight) … WHERE keyword LIKE ?` over a `memory_index` table — keyword prefix matching, no embeddings, no vector store. `README.md:182-183` already describes it correctly; features-loke does not |
| H4 | Memory search latency at scale | Figure withdrawn; named in [metrics-baseline.md](metrics-baseline.md#withdrawn-figures). Restated at `docs/features-loke.md:155,276` | `absent` | None — no benchmark, and no hardware specified | VM1.1, VM1.3 | Withdrawn. The figure would not describe the implementation even if measured, because the implementation is keyword matching (H3) |
| H5 | "AAAK Shorthand … Readable by any LLM without decoder. Layered context loading (L0 … L3)" | `docs/features-loke.md:161` | `verified` | `packages/core/src/memory/aaak.tk` | No test importing the module | The encoder and the layer levels exist |
| H6 | AAAK compression ratio | Figure withdrawn; named in [metrics-baseline.md](metrics-baseline.md#withdrawn-figures). Restated at `docs/features-loke.md:161` | `absent` | None | VM1.7 | Withdrawn — a design target, never measured |
| H7 | "Automatic Context Enrichment: Before every LLM call, search palace for relevant memories" | `docs/features-loke.md:157` | `partial` | `packages/core/src/memory/` | No test | The enrichment path exists in moke's flow; no core path guarantees "before every LLM call", the same gap as A11 and E10 |
| H8 | "Palace Structure: Wings → Halls → Rooms → Closets → Drawers → Tunnels" | `docs/features-loke.md:153` | `verified` | `packages/core/src/memory/palace.tk`, `packages/core/src/memory/schema.tk` | No test importing the module | — |

## I. MCP

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| I1 | "broker with per-server permissions (tool allowlist/denylist, max-cost, require-approval)" | `README.md:188`, `docs/features-loke.md:228` | `verified` | `packages/mcp-broker/src/permissions.tk:11` (`$serverpermission`), `:25-56` (checks), `:90` (`parsetomlpermissions`), `:206` (`applypermissions`) | No test importing the module. T15 | — |
| I2 | "privacy pipeline on all tool call data" | `README.md:188`, `docs/features-loke.md:228` | `verified` | `packages/mcp-broker/src/proxy.tk:8` imports `core.privacy.pipeline`; `:62` anonymises outbound args, `:33` restores inbound responses; failure paths at `:57` and `:28` | No test importing the module | Both directions are wired. A privacy failure on the outbound path fails closed (`:58` returns an error); on the inbound restore path it fails open and logs a warning (`:28-29`) |
| I3 | "audit trail on every invocation" | `README.md:188`, `docs/features-loke.md:228` | `absent` | None. No audit import in any file under `packages/mcp-broker/src/` or `packages/mcp-toke/src/` | GA5, DA1 | No broker or MCP-server path writes an audit record. Given E4 there is nothing to write to. This claim appears in both README and features-loke with no caveat and is the one MCP claim that is simply untrue |
| I4 | "MCP Server … Tools: compress, decompress, template, analyse" | `docs/features-loke.md:226` | `verified` | `packages/mcp-toke/src/server.tk` | No test importing the module | — |

## J. Local inference — epic F2

F2.1–F2.9 are all marked **Done** in [epics-and-stories.md](epics-and-stories.md) (Epic F2). **None has
ever run on the target hardware: no Apple Silicon test machine exists.** Every F2 claim is therefore
a code-reading claim at best.

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| J1 | "Local models: Ollama (REST), MLX (Apple Silicon), native inference" | `README.md:258`, `docs/features-loke.md` | `partial` | `packages/core/src/models/mlx.tk` (44 lines, zero importers), `src/core/inference/mlx/backend.tk` (152 lines), `src/core/inference/native/selector.tk` | No test, and no hardware to run one on. VM1.4 | Ollama is exercised by moke. The MLX path has **zero importers** and has never been executed. `packages/core/src/models/mlx.tk:26` (`generate`) also shadows `result` and `found` with fresh `let` bindings inside its loop, so it returns `""` unconditionally — it could not work if it were called |
| J2 | F2.3 "MLX backend for Apple Silicon … 8-9% faster than llama.cpp" | `docs/epics-and-stories.md:68` | `absent` | As J1 | VM1.4 | A third-party figure, not loke's measurement, and unreachable code besides. Not restated in any of the four public files — keep it that way |
| J3 | F2.6 tiered inference engine with per-tier throughput figures | `docs/epics-and-stories.md:71` | `partial` | `packages/core/src/router/latency_router.tk:18-49` (D4) | No measurement on any hardware. VM1.3, VM1.4 | The tiers are declarations. The throughput figures in the backlog entry have never been observed on a target machine and must not migrate into the public files |
| J4 | F2.8 "Hardware-aware model recommendations — profile RAM, GPU VRAM, unified memory, disk type/speed, CPU on first run" | `docs/epics-and-stories.md:73`; surfaced as `loke doctor` | `partial` | `src/core/hardware/profile.tk`, `src/core/hardware/recommender`, `packages/core/src/models/hardware.tk`, `packages/cli/src/health.tk` | No test, no target hardware | `loke doctor` is the one F2 surface that is wired (`packages/cli/src/main.tk:54`). Its profiling has never been validated against real Apple Silicon topology |
| J5 | F2.9 "Disk-streaming inference for extreme offload" | `docs/epics-and-stories.md:74` | `absent` | No match for any disk-streaming symbol across `packages/` or `src/` | — | Marked Done in the backlog with no implementing code found. Not claimed in the four public files |

## K. Interfaces and runtime modes

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| K1 | "HTTP proxy on port 11431 that intercepts outbound requests to cloud LLM APIs" | `README.md:248`, `docs/architecture.md:92`, `docs/features-loke.md:220` | `verified` | `packages/cli/src/proxy.tk:32,40` (default port), `:47-50` (`--port`), `:175` (`net.listen`), `:189` | No test importing the module | The listener and its plumbing exist. "Transparently routes through the full privacy pipeline" depends on the pipeline wiring, which is real (A11) |
| K2 | The seven-stage `loke claude-code` terminal flow | `README.md:229-238` | `stub` | `packages/cli/src/main.tk:16-26` (`handlepipeline`) prints seven stages each labelled "pending" | No test | The block reads as a trace of work performed. It is a static list of stage names; nothing executes |
| K3 | "Direct Prompting: `loke ask <prompt>` with model selection, dry-run, stdin support, streaming" | `docs/features-loke.md:222` | `stub` | `packages/cli/src/main.tk:11-15` (`handleask`) prints the prompt and "Pipeline not yet connected"; dispatched at `:90` | No test | A fully wired implementation exists at `packages/cli/src/ask.tk:114-179` — privacy filter, router, dispatcher, audit stage — and **nothing imports it**. The command the user reaches is the stub |
| K4 | `loke queue list` / `queue cancel` / `memory search` / `agents list` / `overnight status` | `docs/features-loke.md:220-224`, CLI help at `packages/cli/src/commands.tk` | `stub` | `packages/cli/src/main.tk:27` ("No jobs in queue"), `:31`, `:43`, `:47` ("No agents registered"), `:51` ("No overnight jobs scheduled") | No test | All five return fixed strings. Two of them ("No jobs in queue", "No agents registered") are indistinguishable from a real empty result, so the CLI reports success while doing nothing |
| K5 | "`loke doctor` diagnostics" | `docs/features-loke.md:224` | `verified` | `packages/cli/src/main.tk:54-60` calls `packages/cli/src/health.tk` (`checkall`, `formatreport`) | No test importing the module | The one CLI command that does real work |
| K6 | "Browser Mode … All data passes through the local intelligence layer before external transmission" | `README.md:225`, `docs/features-loke.md:216` | `absent` | `packages/browser/src/_handlers.tk:34-35,129` → `packages/browser/pages/api/pipeline.tk` | `tests/unit/browser/test_pipeline_handler.tk` imports the handler but does not assert anonymisation. AD1.6 | See A13. The browser route reaches the sidecar over HTTP or, failing that, sends the raw text on. It does not pass through the local intelligence layer in any sense the phrase implies |
| K7 | "Localhost-only HTTP server … binds to `127.0.0.1` by default" | `docs/architecture.md:221`, `docs/features-loke.md:170` | `verified` | `packages/browser/src/server.tk`, `packages/core/src/config/` | `tests/unit/browser/test_settings_handler.tk` | — |
| K8 | "26-detector type detection engine" | `README.md:221`, `docs/features-moke.md:33,110` | `verified` | `packages/moke/templates/chat.tkt:946-1205` — `TYPE_DETECTORS`, 26 numbered functions | No automated test | Exactly 26, counted |
| K9 | "9 Australian-themed datasets" / category counts "Government & Public Sector (3)", "IT Operations (8)", "Customer Intelligence (1)" | `README.md:213`, `docs/features-moke.md:80,86,98` | `partial` | `packages/moke/templates/index.tkt` — 15 `ds-name` entries | Counted directly | moke ships **15** datasets, not 9. features-moke's category headings say 3 + 8 + 1 = 12 while its own tables list 3 + 6 + 1 = 10, and the shipped set is 6 government, 6 IT, 3 customer. Three separate counts, none of them right. Undercounting is not a credibility risk in the way an overstated capability is, but it shows the feature documents are not regenerated from the tree |
| K10 | "Insight Lab — Client-Side ML … zero data egress. K-Means, Z-Score, IQR, Pearson correlation" | `README.md:208`, `docs/features-moke.md:238-250` | `verified` | `packages/moke/templates/insight.tkt`, `packages/moke/src/ml/` | No automated test; visible in the UI | The algorithms run in the page. "Zero data egress" holds for the Insight Lab specifically — it makes no outbound call |
| K11 | "Phase 2 — Local Computation: Client-side query execution — zero data egress" (dashboard) | `docs/features-moke.md:213-215` | `partial` | `packages/moke/src/compute.tk` (15 operations), `packages/moke/src/ddl.tk` | No test. NC1.2 | The computation is local. Phase 1 sends the schema profile, and `packages/moke/src/hooks.tk::profiletotoon` plus `packages/core/src/optimiser/profiler.tk::totoonschema` embed **three real sample values per column plus real min/max/mean** — so the "schema-first" request currently ships real data. Tracked as NC1.2 |

## L. Testing, coverage and build

| # | Claim as worded | Where | Verdict | Implementing code | Proof | What is actually true |
|---|---|---|---|---|---|---|
| L1 | "Module coverage 35.5%" | `docs/test-coverage.md:15` (corrected under X6.4) | `partial` | `docs/test-coverage.md` | Counted directly | 35.5% counts source modules that have a *file* named after them. Of 86 test files, 54 carry an explicit `(* --- stub … *)` marker and re-declare their subject; 12 import production code, reaching 22 distinct production modules — about **5%** of the 408 the document counts. See test-coverage.md, which now states both |
| L2 | "120 test files" | `README.md:281,311`, and `docs/test-coverage.md:12` before correction | `absent` | `tests/` contains 86 `test_*.tk` files and 86 `.md` companions | Counted directly | The figure is stale by a wide margin and was never a coverage statement. Corrected in both files under X6.4 |
| L3 | "52 test files covering privacy, memory, governance, storage, models, providers, agents, MCP, CLI, optimiser" | `docs/features-loke.md:240` | `absent` | 86 test files | Counted directly | Also stale, and in the opposite direction from L2. Corrected under X6.2 |
| L4 | `scripts/run_tests.sh` "discovers `test_*.tk` files, compiles and runs each" | `docs/features-loke.md:240` | `partial` | `scripts/run_tests.sh:25` | — | Discovery excludes `*/test_harness*`, which silently removes `packages/core/src/privacy/test_harness.tk` — the only harness capable of scoring detection quality — from every run. AD1.8 |
| L5 | "CI: GitHub Actions workflow — builds toke/ooke from source, runs tests, produces structured JSON artefact" | `docs/features-loke.md:242` | `partial` | `.github/workflows/ci.yml` | — | CI publishes pass/fail counts only. It cannot carry a number, so no measurement can reach metrics-baseline through it. VM1.5 |
| L6 | "compiles all toke modules … to a native binary" | `docs/features-loke.md:238` | `partial` | `scripts/build_loke.sh` | — | The toolchain is currently on hold and the build is red, so no claim about the compiled artefact can be verified at this commit. The binary size quoted alongside it is a file size, not a performance figure |

---

## Maintaining this register

1. A new externally-visible claim arrives with its row, or it does not ship.
2. A row moves to `verified` only when the *Implementing code* column names a file and a line, and the
   *Proof* column names a committed test or a metrics-baseline entry. `scripts/check_claims.py`
   enforces the first half of that in CI (X6.3).
3. When a story listed in a *Proof* column lands, the row is re-verdicted in the same change.
4. Figures live in [metrics-baseline.md](metrics-baseline.md). This file points at them and never
   restates them.
