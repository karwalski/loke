# Privacy Filters — Multi-Layer Architecture

The privacy filter is the set of detection layers loke runs over text before any of it is sent to a
model, and the rules that decide what is masked and when a request is refused. This document says what
the code does today (verified against the source on 2026-10-06, F3b.11). Every configuration key and
behaviour below names the test that shows it, or says **not tested**.

Two scoping notes, so the rest of the document is read correctly:

- **This is the fallback path, not the primary one.** loke's primary path sends a schema profile and the
  user's intent and executes the returned artifact locally, so no entity values are transmitted at all.
  Redact-and-forward is kept for work that genuinely needs prose, and selecting it is meant to be an
  explicit, recorded decision (NC1.8). See [architecture.md](architecture.md) §4.
- **"All outbound data passes through the filter" is a contributor invariant, not a machine property.**
  loke sees only traffic addressed to it, applications must be configured to route through it, and a flag
  exists to disable the pipeline. Six classes of bypass are enumerated and testable (AD1.6). The
  supportable claim is that *when traffic is in path*, filtering is ordered, recorded and inspectable.

## Architecture

There are four detection layers, held in a filter registry (`core.privacy.filterregistry`, F3b.1). Each
entry has an id, whether it is enabled, its address, one parameter, a priority, a mode, a confidence
threshold and an entity filter.

| Order | Id | What it is | Default |
|---|---|---|---|
| 1 | `regex` | In-process patterns (`core.privacy.regex`) | enabled |
| 2 | `ner` | A model served by Ollama, asked for PERSON, ORGANIZATION, LOCATION, DATE, MEDICAL, FINANCIAL (`core.privacy.ner`) | enabled; `http://127.0.0.1:11434`, model `qwen2.5:7b` |
| 3 | `presidio` | A Presidio analyser over REST (`core.privacy.presidio`) | enabled; `http://127.0.0.1:5000` |
| 4 | `openai-privacy-filter` | The privacy-filter sidecar (`core.privacy.sidecarclient`, `packages/privacy-filter/server.py`) | **disabled** unless `privacy.privacy_filter = true` |

NER and Presidio are enabled by default so that a missing service shows up as a *degraded* layer rather
than as one silently absent. Test: `tests/unit/privacy/test_filter_registry.tk`,
`tests/unit/privacy/test_layer_registry_pipeline.tk`.

Each layer's availability check and scan is a branch on its id in `core.privacy.layerhealth` (`probe`,
`consult`). There is no plug-in interface: adding a fifth layer means changing that module (see
[What is not built](#what-is-not-built)).

### What `pipeline.run` does, in order

`core.privacy.pipeline.run(text; basesystemprompt; config)`:

1. **Every registry entry, in registry order** (the order `[[privacy.layers]]` priorities give, below):
   1. `layerhealth.consult`: a disabled entry is sent nothing and recorded as a skipped stage; an
      enabled one is probed and scanned only if it answers. The call is timed in milliseconds,
      probe included.
   2. `layerconfig.accepted`: only detections at or above the layer's `confidence_threshold`, and of a
      type its `entity_filter` names, count.
   3. The layer's metrics row is built (`filtermetrics.forlayer`).
   4. If the layer **completed**: it counts towards `layerscompleted`. Unless it is `detect-only`, it
      becomes a *voter* and its accepted detections go forward. If it is in `veto` mode and accepted
      anything, the run is marked vetoed by it. Any span it reported that could not be placed in the
      text exactly is counted as *unplaced* (MK6.16).
   5. If the layer was enabled and unavailable, or its scan failed: it counts towards
      `layersdegraded` and is logged with its id and reason.
2. A real layer that the registry does not hold at all is recorded as a skipped stage.
3. **Entity routing** (`entityrouting.apply`, F3b.5) keeps, for each routed type, only the detections
   of the layers its route accepts.
4. A `[[privacy.layers]]` error, or failing that a `[[privacy.entity_routing]]` error, is put on the
   run (`layererror`).
5. **Consensus** (`consensus.apply`, F3b.4) groups overlapping detections and decides mask or pass
   for each under `privacy.consensus_strategy`. Under first-match, if a group's most sensitive
   detection is not the one masked, the masked one carries that type (`consensus.applyranked`, RG1.7c).
6. **Dedup** of what consensus kept (`dedupentities`). Of equal values, the most sensitive detection
   is kept, whatever the layer or pattern order; a covering span (a URL, an email address) only drops
   a span inside it that ranks no higher (`strictlyshadows`), so a card number or TFN inside a URL
   is kept (RG1.7c).
   The request's **sensitivity** is the higher of what dedup kept and every detection a masking layer
   accepted before routing, consensus and dedup (`requestsensitivity`, RG1.7c), so no strategy or
   route can lower it. Test: `test_dedup_sensitivity.tk`. Detections from a detect-only layer do not
   count towards it.
7. **Placeholders** are assigned, salted with the run's request id (PL1.1).
8. **Anonymisation** replaces each value with its placeholder (skipped on a dry run).
9. The **guardian** system prompt is built over the base system prompt.

`run` always returns a run. Whether it may be sent anywhere is the separate gate
`pipeline.issafetoforward` (see [Fail-closed rules](#fail-closed-rules)). `runforward` runs and logs why a
run was refused.

On `POST /api/pipeline` the run is `core.privacy.systemprompt.runforward`: when the request carries a
`system_prompt`, it is joined to the text and the two are scanned as one, then each part is anonymised
with the same entity list (F3.9b). Tests: `tests/integration/test_system_prompt_disclosure.tk`,
`scripts/smoke_privacy_harness.sh`.

### Which callers read `config.toml`

The settings below take effect only where the pipeline config is built with
`pipeline.withlokeconfig`:

| Caller | Config |
|---|---|
| `POST /api/pipeline`, `GET /api/health` | `pipeline.served()`: Presidio at `privacy.presidio_url`, Ollama at `127.0.0.1:11434`, and every privacy setting below |
| `loke ask`, `loke proxy`, `loke privacy evaluate`, the browser extension | `withlokeconfig` with `privacy.presidio_url` and `providers.ollama_url` |
| `mcp-broker`, the agent executor (`core.agents.executor`) | `pipeline.newconfig`: the default registry; **none** of the settings below is read |

The config is read when it is built: per request for `/api/pipeline`, at start-up for the others.

## Configuration

`config.toml` is `~/.loke/config.toml`. Every key in this section is optional; with none of them the
pipeline behaves as described under [Migration](#migration-guide-for-existing-deployments).

<!-- privacy-config-keys:start -->
| Key | Read by | Test |
|---|---|---|
| `privacy.consensus_strategy` | `packages/shared/src/config.tk` | `tests/unit/privacy/test_consensus_pipeline.tk` ("privacy.consensus_strategy is read from config.toml") |
| `privacy.consensus_threshold` | `packages/shared/src/config.tk` | `tests/unit/privacy/test_consensus_pipeline.tk` ("privacy.consensus_threshold reaches confidence-weighted", "an unquoted privacy.consensus_threshold = 0.99 reaches confidence-weighted as 0.99", "an out-of-range privacy.consensus_threshold refuses the run"); `tests/unit/shared/test_config_numbers.tk` (each form, F3b.16) |
| `privacy.privacy_filter` | `packages/shared/src/config.tk` | `tests/unit/privacy/test_privacy_filter_layer.tk`; `scripts/smoke_e2e.sh` |
| `privacy.privacy_filter_url` | `packages/shared/src/config.tk` | `tests/unit/privacy/test_privacy_filter_layer.tk`; `scripts/smoke_e2e.sh` |
| `privacy.privacy_filter_threshold` | `packages/shared/src/config.tk` | `tests/unit/privacy/test_sidecar_threshold.tk`; `tests/unit/shared/test_config_numbers.tk` ("an unquoted float privacy_filter_threshold is read"); `tests/unit/privacy/test_consensus_pipeline.tk` ("a privacy_filter_threshold of the wrong type refuses the run"); `scripts/smoke_e2e.sh` |
| `privacy.presidio_url` | `packages/shared/src/config.tk` | `tests/unit/shared/test_config_loaded.tk` (read from config.toml); that `pipeline.served()` passes it to `/api/pipeline`'s registry: not tested |
| `[[privacy.layers]]` | `packages/core/src/privacy/layer_config.tk` | `tests/unit/privacy/test_layer_config.tk`, `tests/unit/privacy/test_layer_config_pipeline.tk`, `scripts/smoke_e2e.sh` |
| `id` | `packages/core/src/privacy/layer_config.tk` | `test_layer_config.tk` ("an unknown id", "an entry with no id") |
| `enabled` | `packages/core/src/privacy/layer_config.tk` | `test_layer_config.tk` ("enabled = false switches a model layer off") |
| `priority` | `packages/core/src/privacy/layer_config.tk` | `test_layer_config.tk` ("presidio at priority 0 runs first"); `test_layer_config_pipeline.tk` ("presidio at priority 0 is consulted first") |
| `mode` | `packages/core/src/privacy/layer_config.tk` | `test_layer_config_pipeline.tk` ("detect-only NER and Presidio do not mask the name", "a veto layer that finds PII is recorded on the run") |
| `confidence_threshold` | `packages/core/src/privacy/layer_config.tk` | `test_layer_config_pipeline.tk` ("Presidio's 0.92 detection does not count at a 0.95 threshold") |
| `entity_filter` | `packages/core/src/privacy/layer_config.tk` | `test_layer_config_pipeline.tk` ("NER filtered to LOCATION and Presidio to CREDIT_CARD do not mask a PERSON") |
| `[[privacy.entity_routing]]` | `packages/core/src/privacy/entity_routing.tk` | `tests/unit/privacy/test_entity_routing.tk`, `tests/unit/privacy/test_entity_routing_pipeline.tk`, `scripts/smoke_e2e.sh` |
| `entity_type` | `packages/core/src/privacy/entity_routing.tk` | `test_entity_routing.tk` ("the type is matched without regard to case", "a type no layer reports") |
| `preferred_layers` | `packages/core/src/privacy/entity_routing.tk` | `test_entity_routing_pipeline.tk` ("PERSON preferring Presidio is credited to Presidio alone") |
| `fallback_layers` | `packages/core/src/privacy/entity_routing.tk` | `test_entity_routing_pipeline.tk` ("the sidecar switched off gives way to the fallback, NER") |
<!-- privacy-config-keys:end -->

`scripts/check_privacy_doc_keys.py` (in the quality gate) fails if a key in that table is not a string
literal in the file named beside it, or if `layer_config.tk` or `entity_routing.tk` accepts a key, or
`consensus.tk` a strategy, that this document does not list. It checks that each key is *read*, not
what is done with it; the tests named do that.

### `privacy.consensus_strategy` and `privacy.consensus_threshold` (F3b.4)

```toml
[privacy]
consensus_strategy = "most-restrictive"   # the default
consensus_threshold = 0.5                 # confidence-weighted only; 0.5 or "0.5"
```

Detections are grouped: two belong to one group when their spans overlap, or when their values are
equal (which is how a layer that reports a value without a span joins a group); membership is
transitive. The **voters** are the layers that completed a scan and are not `detect-only`, in registry
order. A layer that did not scan does not vote.

| Strategy | A group is masked when | Test |
|---|---|---|
| `most-restrictive` (default) | always: every detection any voter accepted | `test_consensus.tk` ("most-restrictive masks every detection: the union") |
| `first-match` | only the detections of the group's highest-priority layer are masked; the others are dropped | `test_consensus.tk` ("first-match keeps regex's email over presidio's, and ner's name") |
| `unanimous` | every voter found it | `test_consensus.tk`; `test_consensus_pipeline.tk` ("unanimous masks neither") |
| `majority` | more than half of the voters found it | `test_consensus.tk`; `test_consensus_pipeline.tk` ("majority masks the name (2 of 3) and not the email (1 of 3)") |
| `confidence-weighted` | the mean over the voters of each voter's highest confidence in the group (0 for a voter that did not find it) is at least `consensus_threshold` | `test_consensus.tk` ("confidence-weighted at 0.5", "and at 0.7 the email no longer meets the threshold") |

- An empty, unknown or **mis-cased** strategy name is applied as `most-restrictive`, and the run records
  that it was. Tests: `test_consensus.tk` ("an UNKNOWN strategy is most-restrictive", "a MIS-CASED
  strategy is most-restrictive"); `test_consensus_pipeline.tk` ("and a mis-cased one").
- `consensus_threshold` unset is 0.5. Test: `test_consensus.tk` ("an unset threshold is 0.5").
- **Quoted or not** (F3b.16). `consensus_threshold` and `privacy_filter_threshold` are read as a TOML
  string (`"0.7"`), an unquoted float (`0.7`) or an integer (`0` or `1`); `shared.config` keeps the text
  as written. std.toml has no float accessor, so an unquoted float is read from its line of the file:
  `consensus_threshold = v` under `[privacy]`, or `privacy.consensus_threshold = v` before any table.
  Tests: `tests/unit/shared/test_config_numbers.tk` (each form); `test_consensus_pipeline.tk` ("an
  unquoted privacy.consensus_threshold = 0.99 reaches confidence-weighted as 0.99"). Until F3b.16 an
  unquoted value read as unset and the default applied with no warning.
- **A threshold that is set and cannot be used refuses every run** (F3b.16), as a malformed
  `[[privacy.layers]]` does: see [Malformed configuration](#malformed-configuration-refuses-every-request).
  It is never replaced by the default. `consensus.tk` still clamps a value outside 0 to 1
  (`test_consensus.tk`, "and clamped to 0..1"), but no such value reaches it from `config.toml` now.
- **Every strategy except `most-restrictive` can leave a detected value in the clear, including one only
  the regex layer found.** Consensus has no regex guard: under `unanimous` or `majority`, an email only
  the regex layer found is passed and sent unmasked. Test: `test_consensus_pipeline.tk` ("majority masks
  the name (2 of 3) and not the email (1 of 3)", "unanimous masks neither"). Whether that should be
  allowed is an open decision (see [Open decisions](#open-decisions)).

### `[[privacy.layers]]` (F3b.2)

```toml
[[privacy.layers]]
id = "presidio"                           # regex, ner, presidio or openai-privacy-filter
enabled = true
priority = 0                              # lower runs first; unlisted layers keep 1, 2, 3, 4
mode = "veto"                             # detect-and-mask (default), detect-only or veto
confidence_threshold = 0.9                # 0 to 1, default 0; a number or "0.9"
entity_filter = ["PERSON", "CREDIT_CARD"] # types the layer reports; empty means all
```

Every key but `id` is optional; a key left out keeps the registry's value.

- **priority** orders the registry, lower first, stably (equal priorities keep registry order). It is
  the order `pipeline.run` consults the layers in and first-match's precedence. Tests:
  `test_layer_config.tk` ("an equal priority keeps registry order"), `test_layer_config_pipeline.tk`.
- **enabled = false** switches a model layer off: it is sent nothing. Test: `test_layer_config.tk`.
- **confidence_threshold** (inclusive) and **entity_filter** narrow which of a layer's detections count.
  A detection below the threshold, or of a type not named, is not masked by that layer and does not
  vote. The names in `entity_filter` must be types that layer reports
  (`core.privacy.entityvocab.layertypes`) and are matched **with** regard to case. Tests:
  `test_layer_config.tk` ("a detection AT the threshold is kept", "an entity type the layer does not
  report"), `test_layer_config_pipeline.tk`.
- **detect-only**: the layer scans and its stage reports what it found, but nothing it found is masked
  and it does not vote. Test: `test_layer_config_pipeline.tk` ("detect-only NER and Presidio do not
  mask the name", "but their stages report what they found").
- **veto**: the layer's accepted detections are masked, and if it accepted any, the run is refused. A
  veto layer whose detections are all below its threshold, or outside its filter, does not refuse.
  Tests: `test_layer_config_pipeline.tk` ("and the run is refused", "a veto layer whose detections are
  below its threshold does not refuse", "nor one whose filter excludes what it found");
  `scripts/smoke_e2e.sh` (the regex layer in veto mode: 503, the model receives nothing).
- `std.toml` has no array-of-tables accessor at this toolchain, so the entries are read from the file
  text (`core.privacy.layerconfig.parse`): one `key = value` per line, strings in double or single quotes
  without escapes, `entity_filter` on one line, `#` comments. Test: `test_layer_config.tk` ("a full
  entry, with a comment and a trailing comma, is accepted", "single quotes and spaces inside the header
  are read").
- A `config.toml` that `std.toml` cannot parse loses every other setting to its default, but its
  `[[privacy.layers]]` are still read. Test: `test_layer_config_pipeline.tk` ("a file std.toml rejects
  is still read for its layers").

### `[[privacy.entity_routing]]` (F3b.5)

```toml
[[privacy.entity_routing]]
entity_type = "PERSON"
preferred_layers = ["openai-privacy-filter"]
fallback_layers = ["presidio", "ner"]
```

Routing decides **whose detections** of a type are accepted. It does not stop any layer scanning: every
enabled layer still scans all of the text. It runs after the layers and before consensus.

- `entity_type` must be a type some layer reports, matched without regard to case, so `CREDIT_CARD`
  names both Presidio's `CREDIT_CARD` and the regex layer's `credit_card`. `preferred_layers` is
  required and not empty; `fallback_layers` is optional. Every layer named must be in the registry and
  must report the type. Tests: `test_entity_routing.tk`.
- A routed type is accepted from its preferred layers that are **available**: completed this scan, not
  `detect-only`, and not filtering the type out with `entity_filter`. If none is, from its available
  fallback layers. Tests: `test_entity_routing.tk` ("a preferred layer that did not run gives way to the
  fallback", "so does a preferred layer that failed", "and a preferred layer whose entity_filter
  excludes the type"); `test_entity_routing_pipeline.tk` (sidecar off, Presidio switched off, Presidio
  down).
- **Neither available:** the type is accepted from every layer that ran, as with no route, and a note
  is logged and returned in `entity_routing_notes`. Tests: `test_entity_routing.tk` ("with neither a
  preferred nor a fallback layer available, every layer that ran is accepted");
  `test_entity_routing_pipeline.tk`; `tests/unit/audit/test_layer_metrics_audit.tk` ("the reply carries
  it").
- Unrouted types are accepted from every layer. There is no default route.
- A veto is decided on what a layer accepted before routing, so routing cannot suppress one. Not
  tested as a combination.
- With a consensus strategy other than `most-restrictive`, a detection routing dropped does not vote,
  so routing plus `unanimous` or `majority` can mask less than either alone. Not tested.

### The regex guards

The regex layer is the in-process detector and the one layer that cannot be unavailable. Two guards keep
configuration from turning it down:

1. **`[[privacy.layers]]` cannot turn it down.** For `id = "regex"`, `enabled = false`,
   `mode = "detect-only"`, a `confidence_threshold` above 0 and an `entity_filter` are each logged as a
   warning and **not applied**. Its `priority` and `mode = "veto"` are applied, since neither masks less.
   Tests: `test_layer_config.tk` ("enabled = false is not applied to regex", "nor is detect-only", "nor
   a threshold or an entity filter", "its priority IS applied", "and so is veto");
   `test_layer_config_pipeline.tk` ("regex disabled, detect-only, at 1.0 and filtered to cards in
   config.toml still masks the email").
2. **Routing never drops a regex detection.** A route for a type the regex layer reports that does not
   prefer the regex layer applies to the other layers only, and is warned about when it is loaded.
   Tests: `test_entity_routing.tk` ("CREDIT_CARD routed to Presidio keeps the regex layer's
   credit_card", "even when Presidio found no card at all"); `test_entity_routing_pipeline.tk`;
   `scripts/smoke_e2e.sh` (a card request is still held for approval).

There is **no** regex guard in consensus: see `privacy.consensus_strategy` above.

### Malformed configuration refuses every request

A `[[privacy.layers]]` or `[[privacy.entity_routing]]` that cannot be applied is not partly applied and
does not fall back to the defaults: none of it is applied, and **every run made with the config is
refused**, including text with no PII. A config the user believes is in force, and is not, would
silently change what is masked.

`[[privacy.layers]]` is refused for: an unknown or missing id, an unquoted id, an unknown key, a key
given twice, a key with no value, a line that is not `key = value`, two entries for one layer, `enabled`
not `true`/`false`, a priority that is not a whole number, an unknown or unquoted mode, a threshold
outside 0 to 1 or not a number, an `entity_filter` that is not a one-line array of quoted types the layer
reports, `[privacy.layers]` written as a table, and `layers = ...` written inline. Test:
`test_layer_config.tk` (each case; "the valid entry before it is not applied either").

`[[privacy.entity_routing]]` is refused for: an unknown key, a key given twice or with no value, a line
that is not `key = value`, no or an unquoted `entity_type`, a type no layer reports, a missing, empty or
non-array `preferred_layers`, a non-array `fallback_layers`, an unquoted or unknown layer id, a layer
that does not report the type, a layer named twice (including both preferred and fallback), two routes
for one type in any case, the table form and the inline forms. Test: `test_entity_routing.tk` (each
case; "one good route and one bad: none is applied").

The refusal says why and names no value. Measured strings, from `scripts/smoke_e2e.sh` against the
built binary (`POST /api/pipeline` answers 503 with `"refused":true`, and the model receives nothing):

```
privacy.layers in config.toml cannot be applied: config.toml line 1: mode must be detect-and-mask, detect-only or veto
privacy.entity_routing in config.toml cannot be applied: config.toml line 1: entity_type private_person is not a type any layer reports
```

`privacy.consensus_threshold` and `privacy.privacy_filter_threshold` are refused (F3b.16) when set and
not usable: a number outside 0 to 1, a negative, an exponent (`7e-1`), a word, an empty string, a
boolean, a form the reader does not take (an inline table such as `privacy = { consensus_threshold = 0.7 }`,
a quoted key), or any value in a file that is not valid TOML. A usable value is `0`, `1`, or `0.` or `1.`
followed by digits and at most 1, quoted or not. `shared.config.privacyerror` says why, and
`core.privacy.layerconfig.resolve` returns that as its error under its own `[privacy]` prefix (F3b.17),
not the `privacy.layers` one. The reason names the key and the value as written, which is
configuration, not user data. Tests: `tests/unit/shared/test_config_numbers.tk` (each case, by its
exact reason); `test_consensus_pipeline.tk` ("an out-of-range privacy.consensus_threshold refuses the
run and says why", "a privacy_filter_threshold of the wrong type refuses the run");
`tests/unit/privacy/test_config_refusal_source.tk` (each of the three sources' refusal, asserted whole).
Measured by `scripts/smoke_e2e.sh` against the built binary, as above:

```
[privacy] in config.toml cannot be applied: privacy.consensus_threshold = 1.5 is not a number from 0 to 1
```

When both are malformed, the layers error is the one reported. Test: `test_entity_routing_pipeline.tk`
("with both malformed, the layers error is the one reported").

## Fail-closed rules

`pipeline.issafetoforward(run)` is a plain bool (not a result type, because of toke trap T-18 at the time
it was written). It is false, and the run must not be sent, when any of these holds:

| Rule | Refusal reason | Test |
|---|---|---|
| No layer completed a scan (NC1.9) | `no privacy detection layer is available` | `tests/unit/privacy/test_fail_closed.tk` ("a run with zero completed layers is refused"); `test_layer_registry_pipeline.tk` |
| A completed layer reported a span that could not be placed in the text exactly (MK6.16) | `a privacy detection layer reported an entity that could not be located in the text exactly` | `tests/unit/privacy/test_presidio_offsets.tk`; `test_privacy_filter_layer.tk` |
| A veto layer accepted a detection (F3b.2) | `the <id> privacy layer is in veto mode and found PII above its threshold` | `test_layer_config_pipeline.tk`; `scripts/smoke_e2e.sh` |
| `[[privacy.layers]]` cannot be applied (F3b.2) | `privacy.layers in config.toml cannot be applied: ...` | `test_layer_config_pipeline.tk`; `scripts/smoke_e2e.sh` |
| `[[privacy.entity_routing]]` cannot be applied (F3b.5) | `privacy.entity_routing in config.toml cannot be applied: ...` | `test_entity_routing_pipeline.tk`; `scripts/smoke_e2e.sh` |
| A `[privacy]` threshold is set and cannot be used (F3b.16, F3b.17) | `[privacy] in config.toml cannot be applied: ...` | `test_config_refusal_source.tk`; `test_consensus_pipeline.tk`; `scripts/smoke_e2e.sh` |

- **A system prompt does not drop a refusal (F3b.15).** `core.privacy.systemprompt.run` rebuilds the run
  and once dropped `vetoedby` and `layererror`, so a request with a `system_prompt` that a veto or a
  malformed layers config should have refused was forwarded. Both are copied now. Test:
  `tests/unit/audit/test_layer_metrics_audit.tk` ("a veto is not lost when the request carries a system
  prompt: the run is refused").
- **An unknown consensus strategy is the union** (`most-restrictive`), above.
- **A degraded run is allowed on purpose.** With at least one layer completed, a layer that is down
  does not refuse the request: the run is forwarded with `layers_degraded` above 0, and that is logged.
  An optional Presidio or sidecar being down must not take a local-first product offline. Test:
  `test_fail_closed.tk` ("a degraded run with one completed layer is still forwardable"). Because the
  regex layer cannot be disabled from config and runs in-process, in practice it is the layer that
  completes.
- `POST /api/pipeline` answers a refused run with 503, `"refused":true`, the reason and the per-layer
  summary below, and audits it as `privacy_refused`. Test: `scripts/smoke_e2e.sh`,
  `test_layer_metrics_audit.tk`.

## Health

`core.privacy.layerhealth` probes each enabled layer with its own client, before every run and on every
`GET /api/health` (no background monitor, no stored history). `/api/health` carries `privacy_layers`:
`{"state","summary","layers":[{"id","enabled","state","reason"}]}` for the layers `/api/pipeline` runs.
The overall state is `healthy`, `degraded` (at least one enabled layer is unavailable) or `unhealthy`
(none available, or none enabled). `formathealthstatus` gives `HEALTHY: all N layers available`,
`DEGRADED: a/N layers available` or `UNHEALTHY: no detection layer available (0/N)`. Tests:
`tests/unit/privacy/test_layer_health.tk`, `test_layer_registry_pipeline.tk`,
`tests/unit/browser/test_health_handler.tk`, `scripts/smoke_e2e.sh`.

Not built: the governance alert when the only layer for a type is down, and a dashboard widget (F3b.6).

## `loke privacy evaluate` (F3b.9)

```
loke privacy evaluate "<text>" [--show-values]
loke privacy evaluate --file <labelled.jsonl>
```

It runs the same registry `loke ask` builds (`withlokeconfig`: Presidio and Ollama URLs, the privacy
filter, `consensus_strategy`, `[[privacy.layers]]`, `[[privacy.entity_routing]]`) and makes the calls
`pipeline.run` makes, but keeps each layer's list (`core.privacy.comparison`).

- **With text:** per layer, its state and each accepted detection as `[TYPE] start-end confidence c`,
  detections dropped by threshold or filter, detect-only, veto and unplaced spans. A layer that did not
  scan is printed with its state and reason and the words "did not scan this text; that is not the same
  as finding nothing", never as zero detections. Then each consensus decision: the reporting layer, the
  layers that found the group with their confidences, the voters that did not (DISAGREEMENT), routing,
  and mask or pass. No detected value is printed unless `--show-values` is given.
- **With `--file`:** the JSONL of `tests/fixtures/pii-corpus` (entities with `expected_detected:true`
  count towards recall). Per layer and for the consensus outcome: precision, recall, F1 and tp/fp/fn,
  scored by `core.privacy.evaluation`. A layer is scored only on texts it scanned; one that scanned none
  is "not scored", not a recall of zero. No text or value is printed.
- **Exit status** 1 when no layer scanned, the layer or routing config is refused, or the file has no
  readable text; 0 otherwise.

Tests: `tests/unit/privacy/test_privacy_comparison.tk`, `tests/unit/privacy/test_privacy_comparison_routing.tk`
(`pipeline.run` and `compare` must make the same decisions under eight configs),
`tests/unit/cli/test_commands.tk`, `scripts/smoke_privacy_evaluate.sh` (the built CLI, in the gate).

Not built: the UI panel, and the `[{text, entities}]` JSON-array import the F3b.9 row names. No figure
from it is published; published figures are only in [metrics-baseline.md](metrics-baseline.md).

## Audit metrics (F3b.10)

For every run, `pipeline.run` records what each registry layer did (`core.privacy.filtermetrics`), as
names, counts, confidences and milliseconds. Nothing reads a detected value into it, and no hash of one
is stored (a name or phone number is low-entropy, so its hash is reversible by trying them).

- **Per layer:** state (completed, disabled, unavailable, failed), mode, milliseconds around the layer
  call (probe included; the clock has millisecond resolution, so a regex scan usually reads 0),
  detections reported, accepted by its threshold and filter, and kept by routing.
- **Per layer and entity type:** the same counts, and minimum, maximum and mean confidence (stored as
  integer thousandths).
- **Consensus:** the strategy applied, the voters, how many detections were resolved, masked and passed,
  how many every voter found, the vetoing layer if any, and routing's notes.

Where it goes:

- `POST /api/pipeline` replies (answered, held for approval, policy-denied, and refused) carry
  `privacy_layers`, `consensus`, `vetoed_by` and `entity_routing_notes`. Test: `scripts/smoke_e2e.sh`,
  `test_layer_metrics_audit.tk` ("the reply's fields carry the per-layer summary").
- The `/api/pipeline` handler writes the rows to the `privacy_layer_metrics` table (migration 41; 42 indexes it),
  once per request id, before the request's first audit row. Every `audit_log` row on that request id
  binds their digest (`layer_digest`, migration 43), so `loke audit verify` fails on an edited, added or
  deleted metrics row. A write failure is logged, not refused. Test: `test_layer_metrics_audit.tk` ("the
  chain breaks at the request's audit row", "a metrics row is added", "no metrics row holds a planted
  value or its sha256"); `scripts/smoke_e2e.sh` (rows bound, no planted value or its sha256 in the
  database).
- `core.audit.layermetrics` aggregates the rows: detections by layer per UTC day, by entity type, and
  the agreement rate between layers over runs with two or more voters. Test: `test_layer_metrics_audit.tk`.
  **Nothing calls these aggregates**: no dashboard, no CLI, no MCP tool. The CLI and the other callers
  do not write metrics rows; only `/api/pipeline` does.

Not built: a dashboard, latency percentiles, and exposure through MCP.

## What a disclosure measure cannot capture (EM1.5)

The measures in this document — detection counts, precision, recall, F1, and the per-request disclosure
accounting specified in epic DA1 — describe what crossed the boundary on a request. Three things they do not
reach, stated here so they are not read as covered:

- **Inference from surrounding context.** A prompt with every entity masked can still support inference of
  the attributes those entities carried, from the text that remains. Published work shows pretrained models
  inferring personal attributes from free text at high accuracy. Masking reduces what is stated; it does not
  control what can be worked out.
- **Provider-side retention and training.** Once a request reaches a provider, what is retained, for how
  long, and whether it informs training are governed by that provider's terms and configuration, not by
  anything measurable here.
- **Correlation across accounts or sessions.** A measure computed per request cannot see what an observer
  holding several requests, or several accounts' requests, could join. The account identifier already links
  prompts; an exposure figure for one request says nothing about that.

**The measure bounds disclosure, not consequence.** A low number means less crossed the boundary on that
request, not that no harm follows. Definitions, and the only figures this project publishes, are in
[metrics-baseline.md](metrics-baseline.md).

## What is not built

- **Custom model registration (F3b.7).** There is no `loke privacy add-model`, no settings panel and no
  registration interface. A layer is a branch on its id in `core.privacy.layerhealth`; adding one is a
  code change. The sidecar reads its own model list from `packages/privacy-filter/models.json`; loke does
  not.
- **Organisation-managed layer policies (F3b.8).** `core.privacy.orgpolicy` and
  `packages/privacy-filter/sample-org-policy.json` exist; nothing reads them on any request path, so no
  organisation setting overrides `config.toml`.
- **Settings UI** for layers, routing or consensus. They are set in `config.toml` only.
- **Privacy-layer settings in the policy presets.** The GDPR, HIPAA, Australian Privacy Act and other
  presets in `packages/core/src/policy/presets` set anonymisation rules, blocked entity types and
  retention; none sets a consensus strategy, a layer, a threshold or a route, and
  `pipeline.applypreset` returns its argument unchanged.
- **The per-entity provenance** (which layers found each value, with what confidence) is on the
  in-memory run (`$pipelinerun.resolved`); only its counts reach the reply and the audit trail.

## Configurations for compliance regimes

loke ships no privacy-layer configuration per regulation, and no detection quality has been measured that
would justify one setting over another for a regime (see [metrics-baseline.md](metrics-baseline.md)). What
the code does guarantee is directional:

- The defaults (`most-restrictive`, every layer detect-and-mask with no threshold or filter, no routes)
  mask the union of what every layer that ran found. Test: `test_consensus_pipeline.tk` ("every value any
  single layer masks is masked by the default three-layer run").
- Settings that can only **add** to that: enabling the privacy-filter sidecar
  (`privacy.privacy_filter = true`), running Presidio and Ollama so those layers complete, and `veto`
  mode, which refuses rather than masks.
- Settings that can **mask less**: any other consensus strategy, a `confidence_threshold`, an
  `entity_filter`, `detect-only`, `enabled = false` on a model layer, and routes.

Policy presets are policy definitions, not compliance: selecting one does not make a deployment
compliant with the named regulation. See [specifications/regulatory-defaults.md](specifications/regulatory-defaults.md).

## Migration guide for existing deployments

### A deployment with no new configuration behaves as before

With no `[[privacy.layers]]`, no `[[privacy.entity_routing]]` and no `privacy.consensus_strategy`, every
layer is detect-and-mask with threshold 0 and no filter, the strategy is `most-restrictive`, and nothing is
routed. The tests that compare a run built from such a config with the pipeline built without reading
config at all:

| What | Test |
|---|---|
| A config.toml with other settings and no layers changes nothing in the registry | `test_layer_config.tk` ("a config.toml with other settings and no layers changes nothing") |
| An empty config.toml, and one with settings but no `[[privacy.layers]]`, mask the same values, count and order | `test_layer_config_pipeline.tk` ("an empty config.toml masks exactly the same values", "so does a config.toml with settings but no [[privacy.layers]]") |
| No routing is byte for byte unchanged (anonymised text, entities with spans and confidences, consensus records) | `test_entity_routing_pipeline.tk` ("an empty config.toml masks byte for byte the same", "and one with no [[privacy.entity_routing]] masks byte for byte what the default does") |
| A config.toml that does not mention consensus masks what the default does, and the default masks as many entities as the pre-consensus dedup did | `test_consensus_pipeline.tk` ("a config.toml that does not mention consensus masks what the default does", "and it masks as many entities as the pre-consensus pipeline did") |

These compare against the current pipeline without config, and in one case against the pre-consensus
dedup rule; no test runs an older loke binary.

What **does** change for an existing deployment, with no configuration:

- `POST /api/pipeline` replies carry four more fields (`privacy_layers`, `consensus`, `vetoed_by`,
  `entity_routing_notes`). A client that rejects unknown fields would notice.
- The database gains the `privacy_layer_metrics` table and `audit_log.layer_digest` (migrations 41 to 43,
  applied when the store is opened), and a refused request is now audited as `privacy_refused`.

### Opting in

1. **The privacy-filter sidecar** (adds a layer): run `packages/privacy-filter/server.py`, then

   ```toml
   [privacy]
   privacy_filter = true
   privacy_filter_url = "http://127.0.0.1:11435"   # the default
   privacy_filter_threshold = 0.0                  # quoted or not; the sidecar's score threshold (AD1.4)
   ```

   With it on and down, it is a degraded layer, not a refusal.
2. **Check what each layer finds** before changing anything: `loke privacy evaluate "<sample text>"`,
   or `--file` with a labelled JSONL.
3. **Then, if you decide to,** add `[[privacy.layers]]`, `[[privacy.entity_routing]]` or a consensus
   strategy as above. Each entry is checked when the config is built; a mistake refuses every request
   with a reason naming the line, so test a change with `loke privacy evaluate` (exit status 1 on a
   refused config) or one request before relying on it.
4. **To undo**, delete the entries: with none, the behaviour above returns.

`mcp-broker` and the agent executor do not read any of these settings.

## Open decisions

Recorded neutrally; none is decided here.

- **Consensus strategies that mask less than the union.** `first-match`, `unanimous`, `majority` and
  `confidence-weighted` can pass a value a layer found, including one only the regex layer found, and
  routing combined with them can pass more. They are opt-in and logged as the strategy applied. Whether
  they should be available, guarded for the regex layer, or removed is open (F3b.4, F3b.5).
- **`enabled = false` for the regex layer.** The F3b.2 row specifies `enabled` per layer; the code
  refuses it for regex with a warning. Whether a user may switch the regex layer off is open (F3b.2).
- **The destination an approval covers (F5.3a).** A request held for approval and approved is read as
  approved for the destination it was first routed to only; a fallback hop to another destination is
  refused (`approval_destination`) rather than sent. That reading was taken because the approval
  records no destination; whether approval should name or offer a destination is open.
