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
`consult`). The one way to add a layer without changing code is a token-classification model registered
with `loke privacy add-model` (F3b.7): it becomes a layer with the id `model:<model-id>` after the four,
in its priority's place (see [Registered models](#registered-models-loke-privacy-add-model-f3b7)).

### What `pipeline.run` does, in order

`core.privacy.pipeline.run(text; basesystemprompt; config)`:

0. **The organisation policy** (`core.privacy.orgpolicy.apply`, F3b.8), if `~/.loke/loke.policy.json`
   exists, is applied over the config: a banned layer is switched off (so it is sent nothing), a weaker
   consensus strategy is raised, thresholds above the maximum are lowered. See
   [Organisation policy](#organisation-policy-lokepolicyjson-f3b8).
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
2. A real layer that the registry does not hold at all is recorded as a skipped stage. The entity
   types only a degraded layer was configured to mask are recorded as `uncovered`, and a governance
   alert is raised for them (see [Health](#health)).
3. **Entity routing** (`entityrouting.apply`, F3b.5) keeps, for each routed type, only the detections
   of the layers its route accepts.
4. A `[[privacy.layers]]` error, or failing that a `[[privacy.entity_routing]]` error, is put on the
   run (`layererror`). What the organisation policy refuses (its own error, a required layer that did
   not scan, too few masking layers) is put on the run as `policyerror`, with a governance alert.
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

The organisation policy (`loke.policy.json`, F3b.8) is not part of that config: `pipeline.run` reads it
on **every run, for every caller above**, including `mcp-broker` and the agent executor, unless the
caller gave the config one (`pipeline.withorgpolicy`, which the tests use). `loke privacy evaluate`
(`core.privacy.comparison`) makes the layer calls itself and does not apply it.

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
| `minimum_layers` | `packages/core/src/privacy/org_policy.tk` | `tests/unit/privacy/test_org_policy.tk` ("minimum_layers 3 is read as 3, not as a constant"); `tests/unit/privacy/test_org_policy_pipeline.tk` ("with Presidio down two do not, and the run is refused") |
| `required_layers` | `packages/core/src/privacy/org_policy.tk` | `test_org_policy_pipeline.tk` ("a required layer that is down refuses the run", "a required layer config.toml switches off refuses", "a required layer set detect-only refuses"); `scripts/smoke_e2e.sh` |
| `locked_consensus` | `packages/core/src/privacy/org_policy.tk` | `test_org_policy_pipeline.tk` ("the policy raises it to most-restrictive: the name, the card and the email are masked"); `scripts/smoke_e2e.sh` |
| `banned_layers` | `packages/core/src/privacy/org_policy.tk` | `test_org_policy_pipeline.tk` ("a banned layer the configuration enables refuses the run, naming it", "config.toml cannot re-enable it: still refused, still sent nothing") |
| `max_confidence_threshold` | `packages/core/src/privacy/org_policy.tk` | `test_org_policy_pipeline.tk` ("max_confidence_threshold 0.9 clamps Presidio's threshold, so its 0.92 detection masks the name", "clamped, it is asked at 0.9 and the name is masked") |
| `max_session_cell_budget` | `packages/core/src/privacy/org_policy.tk` | `tests/unit/nocustody/test_policy_limits.tk` ("config.toml unset: the policy's ceilings are the limits", "a 20-cell result is withheld under a policy cell ceiling of 10", "a policy ceiling above the contract's default is refused, naming the key"); `scripts/smoke_serve.sh` |
| `max_session_predicate_repeat_limit` | `packages/core/src/privacy/org_policy.tk` | `test_policy_limits.tk` ("under a policy ceiling of 3, three probes run and the fourth is refused at 3", "config.toml above the policy's ceiling is refused, naming both keys and values"); `scripts/smoke_serve.sh` |
| `max_installation_cell_budget` | `packages/core/src/privacy/org_policy.tk` | `test_policy_limits.tk` ("an installation ceiling alone lowers only the installation limit", "and an installation ceiling above the default") |
| `max_installation_predicate_repeat_limit` | `packages/core/src/privacy/org_policy.tk` | `test_policy_limits.tk` ("and one above its own installation ceiling", "and a number too long to read") |
| `enforced` | `packages/core/src/privacy/org_policy.tk` | `test_org_policy.tk` ("enforced: false is read as false, and the policy applies nothing"); `test_org_policy_pipeline.tk` ("a policy with enforced: false changes nothing") |
| `description` | `packages/core/src/privacy/org_policy.tk` | `test_org_policy.tk` ("the word enforced in a description does not turn enforcement on") |
| `id` | `packages/core/src/privacy/model_registry.tk` | `tests/unit/privacy/test_model_registry.tk` ("its id and url are read", "an id with a space is refused", "an id registered twice is refused") |
| `url` | `packages/core/src/privacy/model_registry.tk` | `test_model_registry.tk` ("a url off this machine is refused"); `tests/unit/privacy/test_model_registry_pipeline.tk` ("a registered model that is down is degraded; the regex layer still masks") |
| `labels` | `packages/core/src/privacy/model_registry.tk` | `test_model_registry.tk` ("a label mapped to a type loke does not know is refused, naming the label and the type"); `test_model_registry_pipeline.tk` ("the label mapping is applied: PER is masked as PERSON") |
| `confidence_threshold` | `packages/core/src/privacy/model_registry.tk` | `test_model_registry_pipeline.tk` ("the registration's threshold (0.5) keeps the 0.3 detection out") |
| `priority` | `packages/core/src/privacy/model_registry.tk` | `test_model_registry.tk` ("a priority of 0 places it first") |
| `enabled` | `packages/core/src/privacy/model_registry.tk` | `test_model_registry_pipeline.tk` ("a banned model that is registered disabled is not a refusal") |
<!-- privacy-config-keys:end -->

The seven keys from `minimum_layers` to `description` are not `config.toml` keys: they are the keys of the
organisation policy file, `~/.loke/loke.policy.json` (below). The last six are the keys of each model in
`~/.loke/privacy-models.json`, which `loke privacy add-model` writes (see
[Registered models](#registered-models-loke-privacy-add-model-f3b7)).

`scripts/check_privacy_doc_keys.py` (in the quality gate) fails if a key in that table is not a string
literal in the file named beside it, or if `layer_config.tk`, `entity_routing.tk`, `org_policy.tk` or `model_registry.tk` accepts a key, or
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

## Organisation policy (`loke.policy.json`, F3b.8)

An organisation's policy is `~/.loke/loke.policy.json`, a JSON object with the keys in the table above.
`core.privacy.pipeline.run` reads it on every run and applies it **over** `config.toml`
(`core.privacy.orgpolicy`). `packages/privacy-filter/sample-org-policy.json` is an example; it is
accepted as written (test: `test_org_policy.tk`, "the shipped sample policy is accepted").

**A policy can only make privacy stricter than `config.toml`.** Each field either refuses a request,
masks at least what the configuration masks, or stops a layer being sent text:

| Key | What it does | Refusal reason, or note |
|---|---|---|
| `required_layers` | Each named layer must be enabled, not `detect-only`, and complete a scan on this request, or the run is refused. This is the refusal F3b.6 left to this story: a required layer that is down refuses rather than degrades. | `organisation policy loke.policy.json requires the <id> privacy layer, and it did not scan this request: <reason>`; `... and this configuration does not enable it`; `... requires the <id> privacy layer to mask, and this configuration sets it detect-only` |
| `minimum_layers` | 0 to 4. At least this many layers must complete and mask (vote); a detect-only layer does not count. | `organisation policy loke.policy.json requires at least <n> privacy layers to mask each request, and <m> did` |
| `banned_layers` | The layer is switched off before the run, so it is sent nothing. If `config.toml` (or the default, for `ner` and `presidio`) enables it, **every request is refused** until it is switched off in `[[privacy.layers]]`: dropping it quietly would mask less than the configuration asks for. `config.toml` cannot re-enable it. `regex` cannot be banned. | `organisation policy loke.policy.json bans the <id> privacy layer, and this configuration enables it (switch it off in config.toml)` |
| `locked_consensus` | Only `most-restrictive`, a floor: a configured strategy that is anything else is raised to it, never silently. The other strategies are not ordered by strictness, so locking one could mask less than the user's own choice; a policy naming one is refused as malformed. | note `privacy.consensus_strategy <s> is raised to most-restrictive` |
| `max_confidence_threshold` | 0 to 1. **Clamped, not refused**: an enabled layer's `confidence_threshold`, a set `privacy.privacy_filter_threshold` (with the sidecar on) and, under `confidence-weighted`, `privacy.consensus_threshold` above it are lowered to it, so more is accepted and masked. A lower threshold is never raised. The privacy-filter sidecar's own default, used when `privacy_filter_threshold` is unset, is not checked. | note `the <id> layer's confidence_threshold is lowered to <max>` (and the two `privacy.` forms) |
| `max_session_cell_budget`, `max_session_predicate_repeat_limit`, `max_installation_cell_budget`, `max_installation_predicate_repeat_limit` | NC1.14. Ceilings on the no-custody limits `config.toml`'s `[nocustody]` table sets (`docs/specifications/artifact-contract.md` §8.2), applied by `core.nocustody.bound` to every artifact run, not by the privacy pipeline. Each is a whole number from 0 to the contract's default (50 000 cells, 20 repeats); a ceiling above it is malformed and refuses the file. The limit in force is the lowest of the default, `config.toml` and the policy; an unset `config.toml` key takes the ceiling (an override). **A `config.toml` value above a ceiling is refused, not clamped** (unlike `max_confidence_threshold`): `core.nocustody.limits` already refuses a value above the contract's default rather than clamping it (NC1.10), and a ceiling is treated the same whoever sets it, so `config.toml` never says one budget while another is enforced. Every artifact run is then refused 503 `org_policy_violation`. | `nocustody.<key> = <n> in config.toml is above the ceiling of <m> that organisation policy loke.policy.json sets (<policy key>): ...`; note `nocustody.<key> is lowered from <n> to <m> by <policy key>` |
| `enforced` | `false` leaves `config.toml` alone (the file must still be valid). Absent means `true`. | |
| `description` | Ignored. | |

Test of the rule: `test_org_policy_pipeline.tk` ("under every policy field and five user configurations,
each run is refused or masks every value the user's configuration masks").

**Fail closed.** A policy file that is present and cannot be read, is not a JSON object, is not valid
JSON, names a key it does not know (a misspelling is not ignored) or a key twice, or gives a value it
cannot use refuses **every** request, naming the fault: `organisation policy loke.policy.json cannot be
applied: <fault>`. That holds even for a file that says `enforced: false`. Tests: `test_org_policy.tk`
(twenty malformed files by their exact fault, and a file that cannot be read);
`test_org_policy_pipeline.tk` ("a malformed policy refuses a request with no PII", "one that cannot be
read refuses too"). A **missing** file is no policy: nothing changes, byte for byte
(`test_org_policy_pipeline.tk`, "and masks byte for byte what the pipeline masks with no policy at all").

**Surfaced.** Every run the policy refuses raises a governance alert (`core.governance.alert`, kind
`privacy_org_policy`, severity `critical`, logged as `governance alert: privacy organisation policy:
<reason>; the request is refused`), and every run whose configuration it overrode raises one at `warn`
naming each override. Both name layers, settings and policy values, never text. On `POST
/api/pipeline` a refused request is audited as `org_policy_violation` as well as `privacy_refused`, and an
overridden one as `org_policy_override`; the reply's `consensus` object carries `configured_strategy` and
`raised_by` when the floor raised the strategy, and `org_policy_overrides` lists the overrides. With no
policy, none of these appears. For the no-custody ceilings (NC1.14), `POST /api/artifact` surfaces the
same way: a refusal raises the same `privacy_org_policy` alert at `critical` (`...; the artifact run is
refused`) and a run whose limits a ceiling lowered one at `warn` (`organisation policy loke.policy.json
overrode the no-custody limits in config.toml: <notes>`), and each writes a row to the artifact ledger
that route writes, `nc_artifact_runs`: verdict `refused` with code `org_policy_violation`, or verdict
`org_policy_override`, with no op, fingerprint or probe key and nothing released (`test_policy_limits.tk`,
`scripts/smoke_serve.sh`). Measured by `scripts/smoke_e2e.sh` against the built binary:

```
organisation policy loke.policy.json requires the openai-privacy-filter privacy layer, and it did not scan this request: privacy-filter sidecar unreachable
organisation policy loke.policy.json cannot be applied: minimum_layers must be a whole number from 0 to 4
```

**Not built.** The file is in the user's own loke directory, which the user can edit or delete: nothing
makes it tamper-proof. It is not distributed by the compliance engine (A3), and the governance dashboard
(G4) does not show violations; they are in the alert log, the audit trail and the reply. The alerts are not
de-duplicated across runs. The CLI proxy, `loke ask` and `mcp-broker` refuse with the policy's reason
like any other refusal, but write no `org_policy_*` audit row: only `POST /api/pipeline` does.

## Registered models (`loke privacy add-model`, F3b.7)

A HuggingFace-compatible token-classification model can be added as a privacy layer without a code
change:

    loke privacy add-model dslim/bert-base-NER --url http://127.0.0.1:11436 \
        --label PER=PERSON --label LOC=LOCATION --label ORG=ORGANIZATION --threshold 0.5 --priority 5
    LOKE_PF_MODEL=dslim/bert-base-NER python3 packages/privacy-filter/server.py 11436
    loke privacy list-models
    loke privacy remove-model dslim/bert-base-NER

`add-model` (`cli.privacymodels`) writes the registration to `~/.loke/privacy-models.json`, whose keys
are in the table above, and `core.privacy.pipeline.withlokeconfig` registers each model in it as a layer
`model:<model-id>` (`core.privacy.modelregistry`) **before** `[[privacy.layers]]` and
`[[privacy.entity_routing]]` are applied, so both can name it. So the registered models reach exactly the
callers that read `config.toml` (see [Which callers read config.toml](#which-callers-read-configtoml)),
read when their config is built; `mcp-broker` and the agent executor do not run them. That
`withlokeconfig` reads the file is tested (`test_model_registry_pipeline.tk`), and that the built loke's
`POST /api/pipeline` runs a registered model is tested over HTTP by `scripts/lib/model_layer_smoke.py`
in `scripts/smoke_privacy_harness.sh`: the model is registered through `POST /api/privacymodels`, and
the request is judged on what the Ollama stand-in received (neither value the model found, a
`LOCATION` and a `WIDGET` placeholder in their place), on the reply's `privacy_layers` (the layer
completed with 2 detections) and on `loke.db` (below); with the registration removed, the same request
reaches the stand-in with the value in it.
The model is served by the existing sidecar, one process per model:
`LOKE_PF_MODEL` names the `models.json` entry or hub id it loads, and its `/health` names the model and
its task. Tests: `tests/unit/privacy/test_model_registry.tk`, `tests/unit/privacy/test_model_registry_pipeline.tk`,
`tests/unit/cli/test_privacy_models.tk`, `scripts/smoke_privacy_evaluate.sh`. The model and its sidecar
are a recording stand-in in every test (`scripts/lib/http_recorder.py`, mode `tokenmodel`): no model is
loaded by any test, so how well a real model detects anything is not measured here.

### Adding a custom model, step by step

Each `loke` command below was run on 2026-11-09 with the built `loke-cli` under a throwaway `HOME`, with
`scripts/lib/http_recorder.py` in `tokenmodel` mode standing in for the sidecar (it answers `/health` as
`recorder/token-model` and reports fixed spans on `/detect`); the output quoted is what it printed. Step 2
was not run with a real model: no test or check here downloads or loads one, so step 2 is described from
`packages/privacy-filter/server.py` only, apart from its `.onnx` refusal, which was run.

1. **Choose a token-classification model and write its label mapping.** Note each label the model
   reports (for `dslim/bert-base-NER`: `PER`, `LOC`, `ORG`, `MISC`) and the loke type each one is. A type
   must be one a built-in layer reports (the list is in the refusal below); there is no type for `MISC`,
   so leave it out: an unmapped label is still masked, under the label upper-cased.
2. **Start a sidecar serving it**, one process per model, on a loopback port:

       LOKE_PF_MODEL=dslim/bert-base-NER python3 packages/privacy-filter/server.py 11436

   `LOKE_PF_MODEL` is an `id` in `packages/privacy-filter/models.json` or, if none matches, a hub id or
   local directory loaded as given (through `transformers`, PyTorch or SafeTensors weights; a hub id is
   downloaded by `transformers` on first start). `LOKE_PF_REVISION` pins the hub revision; unpinned, the
   sidecar warns that results are not reproducible. Its `/health` then names the model (`model_id`) and
   the task `token-classification`. An `.onnx` path is refused at start (`ERROR: ... is an ONNX model;
   this sidecar loads only transformers token-classification models`, exit 2; run offline with
   `HF_HUB_OFFLINE=1`).
3. **Register it.** The id must be the one the sidecar's `/health` names, and the url its address:

       $ loke privacy add-model dslim/bert-base-NER --url http://127.0.0.1:11436 \
             --label PER=PERSON --label LOC=LOCATION --label ORG=ORGANIZATION --threshold 0.5 --priority 5
       registered model:dslim/bert-base-NER: it is a privacy layer from the next request.

   (Run as `recorder/token-model` with `PER=PERSON`, `LOC=LOCATION`, exit 0.) It writes
   `~/.loke/privacy-models.json`:

       {"models":[
         {"id":"recorder/token-model","url":"http://127.0.0.1:49369","labels":["PER=PERSON","LOC=LOCATION"],"confidence_threshold":0.5,"priority":5,"enabled":true}
       ]}

   Nothing is contacted when you register: the model is probed before the first text it is sent.
   Refused, exit 1, nothing written: a label mapped to an unknown type (`the label mapping
   MISC=MISCELLANEOUS maps MISC to MISCELLANEOUS, which is not an entity type loke knows; a label must
   map to a type a built-in layer reports (email, ..., PERSON, ORGANIZATION, LOCATION, ...)`) and a url
   off this machine (`the url http://192.168.1.4:11436 is not an http:// address on this machine
   (127.0.0.1, localhost or [::1]); the text is sent to it in clear`). Registering an id that is
   registered **replaces** it, and an option left out takes its default (`--threshold` 0, `--priority`
   5, enabled), not its earlier value. `--disabled` registers it switched off. The settings page's
   **Registered Privacy Models** panel does the same through `POST /api/privacymodels`.
4. **Check it.** `loke privacy list-models` prints each registration
   (`model:recorder/token-model  http://127.0.0.1:49369  labels=PER=PERSON,LOC=LOCATION
   confidence_threshold=0.5  priority=5  enabled`). `loke privacy evaluate "<text>"` runs it beside the
   other layers and shows what it found, values hidden:

       model:recorder/token-model (detect-and-mask): completed, 3 detections
         (1 detection below the layer's threshold or outside its entity filter, not counted)
         [PERSON] 0-12 confidence 0.91
         [LOCATION] 18-26 confidence 0.88
         [WIDGET] 31-38 confidence 0.7

   A sidecar that is down or answers as another model shows as unavailable, and the run goes on
   without it (degraded, F3b.6). `GET /api/health`'s `privacy_layers` lists it too.
5. **Optionally, tune it in `config.toml`** like any layer, by its layer id:

       [[privacy.layers]]
       id = "model:recorder/token-model"
       mode = "detect-only"

   `loke privacy evaluate` then shows `model:recorder/token-model (detect-only): completed, 2
   detections ... detect-only: these are reported, not masked, and the layer does not vote`.
   `[[privacy.entity_routing]]` and an organisation policy's `required_layers`/`banned_layers` take the
   same id.
6. **Remove it** with `loke privacy remove-model recorder/token-model` (`removed
   model:recorder/token-model`; then `list-models` prints `no registered privacy models`), or **Remove**
   in the panel.

If `privacy-models.json` cannot be applied (for example an entry with no url), every request is refused
and the CLI will not write over it: `add-model` and `remove-model` exit 1 with `registered privacy models
privacy-models.json cannot be applied: model m has no url; fix or remove it first`, and `list-models`
names the same fault. Edit or delete the file.

What a registered model is, as a layer:

- **Its detections are masked under the loke type its label mapping gives** (`PER=PERSON`): rated,
  routed and matched by the presets as the same type from any other layer. A label the mapping does not
  name is masked all the same, under the label upper-cased. Test: `test_model_registry_pipeline.tk`
  ("the label mapping is applied: PER is masked as PERSON", "a label the mapping does not name is masked
  all the same, upper-cased").
- **A mapping to a type loke does not know is refused.** Each label must map to a type a built-in layer
  reports (`core.privacy.entityvocab`). `add-model` refuses such a registration and writes nothing; a
  `privacy-models.json` holding one (or any other fault: an unknown key, a url that is not loopback, a
  threshold outside 0..1) refuses **every** request, naming the file, the model and the fault, as a
  malformed `[[privacy.layers]]` does, and nothing is sent to the model. A missing file is no model.
  Test: `test_model_registry_pipeline.tk` ("a registration mapping a label to a type loke does not know
  refuses the request", "and nothing is sent to the model"); `test_privacy_models.tk` ("a refused
  registration exits 1 and writes nothing").
- **Its threshold** is the layer's `confidence_threshold`: the sidecar is asked for every span
  (threshold 0) and loke drops those below it. `[[privacy.layers]]` can override it, and the organisation
  policy's `max_confidence_threshold` clamps it, as for any layer.
- **It is sent text only after its `/health` has answered as that model** (`ok`, its `model_id`, task
  `token-classification`), on a loopback address. A sidecar that is down, or answers as another model, is
  a degraded layer (F3b.6): the run continues with the layers that answered, and a type only it masks is
  reported uncovered. Test: `test_model_registry_pipeline.tk` ("the model was probed on /health before
  it was sent any text", "a sidecar answering as another model is a degraded layer, and the run goes on
  (F3b.6)", "and it is never sent the text").
- **It only adds.** It votes in consensus like any layer, so under `unanimous`, `majority`,
  `confidence-weighted` or `first-match` one more voter could otherwise mask less. When a registered model
  voted, `pipeline.addonly` applies the run's routing and consensus again to the other layers' detections
  with only those layers as voters, and masks that too. It cannot weaken the regex layer. Test:
  `test_model_registry_pipeline.tk` ("under unanimous, the email only the regex layer found is still
  masked"). A route in `[[privacy.entity_routing]]` that prefers the model for a type is the user's own
  choice, and is applied to the other layers as any route is.
- **An organisation policy** can name it in `banned_layers` or `required_layers` as `model:<model-id>`,
  registered or not. Banned while registered enabled, every request is refused and the model is sent
  nothing. Test: `test_model_registry_pipeline.tk` ("an organisation policy that bans the model refuses a
  configuration that enables it", "and the banned model is never sent the text", "a policy that requires
  the model forwards when it scans").
- **`loke privacy evaluate`** reports it as a layer with its detections. Test:
  `test_model_registry_pipeline.tk` ("loke privacy evaluate shows the model as a layer, with what it
  found"); `scripts/smoke_privacy_evaluate.sh`.
- **It has a stage of its own in the pipeline trace** (`$modelscan`, carrying its layer id), scanned
  with what it found or skipped with the reason, so `detection_layers` in the decision trace and the
  disclosure record names it beside the built-in layers:
  `scanned=regex,model:recorder/token-model;skipped=ner,presidio,privacy_filter`. Its counts are also in
  the run's layer metrics (`privacy_layer_metrics`). Test: `test_model_registry_pipeline.tk` ("the model
  leaves one scan stage in the run's trace...", "the decision trace's detection_layers names the model
  among the layers that scanned", "a model that answers as another, or is down, leaves a skipped stage,
  not a scan"); `model_layer_smoke.py` reads both columns from `loke.db`.

## Settings UI (F3b.2, F3b.7)

moke's settings page (`/settings`) has two panels that talk to loke directly (`window.LOKE_DIRECT`, as
`/api/settings` does; loke guards both routes against foreign origins and hosts):

- **Privacy Layers** reads `GET /api/privacylayers` (each layer's `enabled`, `priority`, `mode`,
  `confidence_threshold`, `entity_filter` and reported types as `config.toml` sets them, the policy's
  floor, and why the layers config refuses requests if it does) and saves with
  `POST /api/privacylayers {"layers":[...]}`. A save replaces only the `[[privacy.layers]]` entries of
  `config.toml`: every other line is kept in place. It is refused, and nothing is written, when the text
  it would write cannot be applied (400, the pipeline's own reason), when it turns the regex layer down
  (400: the pipeline does not apply that, and whether a user may switch regex off is an open decision,
  F3b.2), when it falls below the organisation policy (409: a banned layer enabled, a required layer off
  or detect-only, a threshold above `max_confidence_threshold`, fewer masking layers than
  `minimum_layers`; `orgpolicy.floorerror`), when the policy cannot be applied (409), and when
  `config.toml` exists and cannot be read (500). The page locks the switches the server would refuse and
  shows the server's refusal as it answers it.
- **Registered Privacy Models** lists `GET /api/privacymodels` and registers with
  `POST /api/privacymodels {"id","url","labels":[...],"confidence_threshold","priority","enabled"}`
  through `modelregistry.register`, the call `loke privacy add-model` makes. **Edit** puts a row's values
  in the form; registering an id that is registered replaces it in place. **Remove** asks again ("Confirm
  remove") and then sends `POST /api/privacymodels {"remove":"<model-id>"}` through
  `modelregistry.unregister`, the call `loke privacy remove-model` makes (404 when the id is not
  registered; a broken `privacy-models.json` is not rewritten, 409). The policy refuses a model it bans
  registered enabled, one with a threshold above its ceiling, and a model it requires registered
  switched off or removed (409): the pipeline would then refuse every request.

Evidence: `tests/unit/privacy/test_layer_view.tk`, `tests/unit/privacy/test_privacy_models_api.tk`,
`scripts/lib/privacy_settings_check.py` in `scripts/smoke_serve.sh`, and
`tests/ui/privacysettings_f3b2.json` in `scripts/smoke_ui.sh`.

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
| The organisation policy refuses it (F3b.8): it cannot be applied, a required layer did not scan, too few masking layers, a banned layer is enabled | `organisation policy loke.policy.json ...` (above) | `test_org_policy_pipeline.tk`; `scripts/smoke_e2e.sh` |

- **A system prompt does not drop a refusal (F3b.15).** `core.privacy.systemprompt.run` rebuilds the run
  and once dropped `vetoedby` and `layererror`, so a request with a `system_prompt` that a veto or a
  malformed layers config should have refused was forwarded. Both are copied now, and so is the
  organisation policy's `policyerror` (F3b.8; test: `test_org_policy_pipeline.tk`, "a run with a system
  prompt is refused by the policy too"). Test:
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
`GET /api/health` (no background monitor, no stored history). A probe is the layer's own health check
(Presidio's and the sidecar's `GET /health`, Ollama's model list); no user text is sent to a layer that
has not answered it. `/api/health` carries `privacy_layers`:
`{"state","summary","layers":[{"id","enabled","state","reason"}],"uncovered_types":[...]}` for the
layers `/api/pipeline` runs, **with the organisation policy applied** as `pipeline.run` applies it
(F3b.8; `core.privacy.layerview.healthjson`). Each layer also carries `priority`, `mode`,
`confidence_threshold` and `policy_changed`, the fields the policy changed (`enabled` for a banned
layer, `confidence_threshold` for a clamped one, `privacy_filter_threshold`); `consensus` gives the
configured and effective strategy, `org_policy` whether a policy is present and enforced, its error and
its overrides, and `refused` why every request is refused, if one is (a `[[privacy.layers]]` that cannot
be applied, or a policy that cannot be, or that bans an enabled layer). While anything is refused the
state is `unhealthy` and the summary begins `REFUSED: every request is refused:`. The overall state is `healthy`, `degraded` (at least one enabled layer is
unavailable) or `unhealthy` (none available, or none enabled). `formathealthstatus` gives
`HEALTHY: all N layers available`, `DEGRADED: a/N layers available` or
`UNHEALTHY: no detection layer available (0/N)`.

**Degradation is continued, and shown, never silent.** A layer that is down is skipped: it counts
towards `layers_degraded`, is logged with its id and reason, and leaves a skipped stage carrying the
reason. The run goes on with the layers that answered, and is refused only when none completed
([Fail-closed rules](#fail-closed-rules)).

**Uncovered entity types and the governance alert (G1).** `layerhealth.uncoveredtypes` lists each
entity type that a degraded layer was configured to mask (it reports the type, is not `detect-only`,
and its `entity_filter` does not exclude it) and that no layer that answered masks. Types are the same
when their names match without regard to case, or when `core.privacy.entityvocab.presettypes` gives
them the same non-empty set of preset types: Presidio's `EMAIL_ADDRESS` is the regex layer's `email`,
and the sidecar's `ADDRESS` is NER's `LOCATION`, but the sidecar's `SECRET` (a password or a key) is not
the regex layer's `api_key`. With the default layers and the sidecar down, that leaves `SECRET`.
`pipeline.run` records the list on the run (`uncovered`) and, when it is not empty, raises a governance
alert through `core.governance.alert` (kind `privacy_layer_coverage`, severity `warn`; logged as
`governance alert: privacy layer coverage: no available detection layer masks <types>; the layers
configured for them are down: <id> (<reason>), ...`). The alert is raised in `run`, so the CLI proxy,
`loke ask` and the MCP broker, which call `run` themselves, raise it too. It names types, layers and
reasons, never text. It is raised once per run that has a gap; there is no de-duplication across runs
and no webhook (the alert config is the log-only default). The reply to `POST /api/pipeline` carries
`uncovered_entity_types`, and `/api/health` `uncovered_types` from the probe.

An uncovered type does **not** refuse the request: a request whose only gap is that a sidecar is down
is forwarded, as the degraded rule says, with the gap alerted and in the reply. Refusing when a
particular layer is down is an organisation policy (`required_layers`, `minimum_layers`), which is
F3b.8 and not built. Entity routing (F3b.5) is unchanged: a route with no available layer accepts the
type from every layer that ran, which never masks less than no route.

**Dashboard.** moke's dashboard (`/dashboard`) has a *Privacy layers* panel that reads `privacy_layers`
from `/api/health` (moke's own `/api/health` returns loke's body) every 15 seconds: the overall state,
each layer with its state and reason, and the uncovered types. When loke does not answer, or answers
without `privacy_layers`, it reads `unknown`, never healthy.

Tests: `tests/unit/privacy/test_layer_coverage.tk` (two `http_recorder.py` stand-ins killed between
runs: degraded counts, skip reasons, forwardable, the uncovered types, the alert in `loke.log` with no
text in it, the health report, and refusal with every layer down), `test_layer_health.tk`,
`test_layer_registry_pipeline.tk`, `tests/unit/browser/test_health_handler.tk`, `scripts/smoke_e2e.sh`
(the sidecar killed: `/api/health` and the reply name `SECRET`, and the alert is in `loke.log`), and
`tests/ui/layerhealth_f3b6.json` in `scripts/smoke_ui.sh` (the panel against the live `/api/health`, and
against a degraded and an unreachable answer).

Not built: a cached last-checked state or health history; each run and each `/api/health` call probes.

## `loke privacy evaluate` (F3b.9)

```
loke privacy evaluate "<text>" [--show-values]
loke privacy evaluate --file <labelled.jsonl | labelled.json>
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
- **With `--file`:** one of two formats, told apart by the file's content (a first non-blank `[` is the
  array). The JSONL of `tests/fixtures/pii-corpus` (entities with `expected_detected:true` count towards
  recall; a line that is not an object is skipped). Or a JSON array
  `[{"text": "...", "entities": [{"start": 0, "end": 4, "type": "PERSON"}]}]`, whose offsets count
  characters (code points) and are converted to byte offsets; every entity counts except one typed
  `NOT_PII`. A malformed array (not JSON, empty, an entry without `text` or `entities`, an entity
  without `type` or with offsets outside `0 <= start < end <= length`) is refused whole, on stderr with
  exit 1, naming the entry and entity at fault and quoting no text. Per layer and for the consensus outcome: precision, recall, F1 and tp/fp/fn,
  scored by `core.privacy.evaluation`. A layer is scored only on texts it scanned; one that scanned none
  is "not scored", not a recall of zero. No text or value is printed.
- **Exit status** 1 when no layer scanned, the layer or routing config is refused, or the file has no
  readable text; 0 otherwise.

Tests: `tests/unit/privacy/test_privacy_comparison.tk`, `tests/unit/privacy/test_privacy_comparison_routing.tk`
(`pipeline.run` and `compare` must make the same decisions under eight configs),
`tests/unit/cli/test_commands.tk`, `scripts/smoke_privacy_evaluate.sh` (the built CLI, in the gate).

**In the browser:** loke's `/evaluate` page posts a text to `POST /api/evaluate`
(`packages/browser/pages/api/evaluate.tk`), which runs `compare` over `pipeline.served()` (the layers
`/api/pipeline` filters with) and answers per layer its state, reason and each detection as type,
placeholder (`[TYPE]`), byte spans and confidence, then the consensus decisions and summary. It never
returns a detected value (there is no `--show-values` equivalent). A layer that did not scan has
`"detections":null`, never 0, and the page shows "did not scan". The text goes only to the detection
layers; nothing routes, dispatches or records. Origin-guarded (GA2.6, GA2.7). Tests:
`tests/unit/browser/test_evaluate_handler.tk` (a stand-in for the local model provider receives nothing),
`scripts/smoke_serve.sh` (`scripts/lib/evaluate_check.py`, over HTTP, and a foreign Origin refused),
`tests/ui/evaluate_f3b9.json` in `scripts/smoke_ui.sh`.

**A labelled file in the browser:** the same page has a file input; the file's contents go to
`POST /api/evaluate` as `{"labelled": "..."}` (at most 65536 bytes: 413 above; 400 for a file that
cannot be read, with the reason), scored by the same `comparison.scorelabelled` as the CLI's `--file`, in
either format. The reply gives per layer, and for the consensus outcome last, the texts scanned of the
texts read and recall, precision, F1, tp, fp and fn; a layer that scanned none is `"scored":false` with
null figures. No text and no value is returned.

**Entity routing:** the reply's `not_accepted` lists each detection a masking layer made that
`[[privacy.entity_routing]]` did not accept (type, placeholder, spans, layer; never the value), as the
CLI's "not accepted by routing" lines do, and the page shows them under the consensus table.

No figure from it is published; published figures are only in
[metrics-baseline.md](metrics-baseline.md).

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
- **Per resolved detection** (rows of kind `entity`, after the consensus row): its entity type, the ids
  of the layers that found it, the action taken (`mask` or `pass`), how many layers found it, the
  group's confidence in thousandths, and whether every voter found it. Not its value, its offsets or
  its length, and no hash of any of them.

Where it goes:

- `POST /api/pipeline` replies (answered, held for approval, policy-denied, and refused) carry
  `privacy_layers`, `consensus`, `vetoed_by` and `entity_routing_notes`. Test: `scripts/smoke_e2e.sh`,
  `test_layer_metrics_audit.tk` ("the reply's fields carry the per-layer summary").
- The `/api/pipeline` handler writes the rows to the `privacy_layer_metrics` table (migration 41; 42 indexes it),
  once per request id, before the request's first audit row. Every `audit_log` row on that request id
  binds their digest (`layer_digest`, migration 43), and so does every row of a fallback hop after the
  first, sent under `<request id>-h<n>` (`core.storage.audit.requestof`), so `loke audit verify` fails on
  an edited, added or deleted metrics row. Tests: `test_layer_metrics_audit.tk` ("the hop's row binds
  the request's metrics"), `tests/integration/test_browser_fallback.tk` ("every audit row of the second
  hop binds the run's layer metrics digest"). A write failure is logged, not refused. Test: `test_layer_metrics_audit.tk` ("the
  chain breaks at the request's audit row", "a metrics row is added", "no metrics row holds a planted
  value or its sha256"); `scripts/smoke_e2e.sh` (rows bound, no planted value or its sha256 in the
  database).
- `core.audit.layermetrics` aggregates the rows: detections by layer per UTC day, by entity type, and
  the agreement rate between layers over runs with two or more voters, the number of requests
  recorded, and per layer the p50, p95 and p99 of its scan time (`latencybylayer`: nearest rank over
  the rows where the layer completed and was timed, so an unavailable layer's probe is not a scan;
  formatted to text, in integer milliseconds, inside the module). Each takes the start of a time
  window (`windowsince`: `24h`, `7d`, `30d` or `all`). Tests: `test_layer_metrics_audit.tk`,
  `tests/unit/browser/test_layermetrics_handler.tk`.
- `GET /api/layermetrics[?window=24h|7d|30d|all]` (`packages/browser/pages/api/layermetrics.tk`,
  origin-guarded) answers those aggregates over the window (default `all`), with `period` and
  `since_ms`, or `"recorded":false` with no figure when no request in the window recorded metrics; an
  unknown window is refused with 400. moke relays it (`packages/moke/pages/api/layermetrics.tk`) to the governance page's "Privacy
  Layer Metrics" section, which shows the request count, the agreement rate, detections by layer per
  day and by layer and entity type, scan latency percentiles by layer, and "No requests recorded" for
  an empty table, over the window its selector names (last 24 hours, 7 days, 30 days, or all time).
  moke passes the window on only when it is letters and digits, and refuses anything else with 400. Tests:
  `tests/unit/browser/test_layermetrics_handler.tk`, `scripts/smoke_serve.sh` (judged against the
  database file), `tests/ui/layermetrics_f3b10_empty.json` and `tests/ui/layermetrics_f3b10.json` (rows
  seeded from `tests/ui/layermetrics_f3b10_seed.sql`) in `scripts/smoke_ui.sh`.
- loke's MCP server (`packages/mcp-toke`, `mcptoke.server`) offers a `layer_metrics` tool
  (`mcptoke.metricstool`) with an optional `window` argument; it answers exactly the body
  `GET /api/layermetrics` answers (both are built by `core.audit.layermetricsreport`), and an unknown
  window as a tool error. Test: `tests/unit/mcp_toke/test_layer_metrics_tool.tk`.

Not built: a running MCP endpoint. No loke process serves `mcp-toke` (its binary is not linked; MK6.20
holds that decision), so the tool is reached today only through the server's request handler, as the
test drives it.

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

- **Parts of custom model registration (F3b.7).** Registration, its settings panel (add, edit,
  remove) and its trace stage are built (above); not built are: ONNX models (the sidecar refuses a
  `.onnx` path at start); an Ollama-served model as a registered layer (Ollama serves generative models,
  not token classifiers; the NER layer is the Ollama layer); a sidecar process serving more than one
  model (one per model, `LOKE_PF_MODEL`); `add-model` writing the sidecar's own `models.json` (not
  built by design: `LOKE_PF_MODEL` already loads a hub id or local directory that `models.json` does
  not list, `LOKE_PF_REVISION` pins its revision, and `models.json` sits beside `server.py` with its
  own label mapping, to placeholder prefixes rather than loke types, so a second copy of each
  registration there could only drift from `privacy-models.json`, which is the one the pipeline
  enforces); and a check of the model's output beyond its `/health` naming the task.
- **Organisation policy distribution and display (F3b.8).** The policy is enforced (above), but it is
  not distributed by the compliance engine (A3), not protected from the user editing it, and not shown
  on the governance dashboard (G4).
- **Settings UI** for routing or consensus: they are set in `config.toml` only. The layers and the
  registered models have one (see [Settings UI](#settings-ui-f3b2-f3b7)).
- **Privacy-layer settings in the policy presets.** The GDPR, HIPAA, Australian Privacy Act and other
  presets in `packages/core/src/policy/presets` set anonymisation rules, blocked entity types and
  retention; none sets a consensus strategy, a layer, a threshold or a route, and
  `pipeline.applypreset` returns its argument unchanged.
- **The per-layer confidence of each detection.** The audit trail records each resolved detection's
  type, the ids of the layers that found it, the action taken and the group's confidence (entity rows,
  F3b.10); each layer's own confidence for it stays on the in-memory run (`$pipelinerun.resolved`).

## Configurations for compliance regimes

loke ships no privacy-layer configuration per regulation, and no detection quality has been measured that
would justify one setting over another for a regime (see [metrics-baseline.md](metrics-baseline.md)). What
the code does guarantee is directional:

- The defaults (`most-restrictive`, every layer detect-and-mask with no threshold or filter, no routes)
  mask the union of what every layer that ran found. Test: `test_consensus_pipeline.tk` ("every value any
  single layer masks is masked by the default three-layer run").
- Settings that can only **add** to that: enabling the privacy-filter sidecar
  (`privacy.privacy_filter = true`), running Presidio and Ollama so those layers complete, registering a
  model with `loke privacy add-model` (`pipeline.addonly`), and `veto` mode, which refuses rather than
  masks.
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
| No `loke.policy.json` masks byte for byte what the pipeline masks with no policy at all (F3b.8) | `test_org_policy_pipeline.tk` ("and masks byte for byte what the pipeline masks with no policy at all", "with the file gone, the run masks byte for byte as before") |

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

`mcp-broker` and the agent executor do not read any of these settings. They do apply an organisation
policy (`loke.policy.json`), which every run reads.

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
