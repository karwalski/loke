# Privacy Filters — Multi-Layer Architecture

The privacy filter is a configurable, multi-layer detection and masking system applied to text before it
reaches an external LLM. This document covers its architecture, configuration, regulatory presets and
operational guidance.

Two scoping notes, so the rest of the document is read correctly:

- **This is the fallback path, not the primary one.** loke's primary path sends a schema profile and the
  user's intent and executes the returned artifact locally, so no entity values are transmitted at all.
  Redact-and-forward is kept for work that genuinely needs prose, and selecting it is meant to be an
  explicit, recorded decision (NC1.8). See [architecture.md](architecture.md) §4.
- **"All outbound data passes through the filter" is a contributor invariant, not a machine property.**
  loke sees only traffic addressed to it, applications must be configured to route through it, and a flag
  exists to disable the pipeline. Six classes of bypass are enumerated and testable (AD1.6). The
  supportable claim is that *when traffic is in path*, filtering is ordered, recorded and inspectable.

## Architecture Overview

The privacy filter is a composable pipeline of detection layers. Each layer independently scans text for sensitive entities (PII, PHI, financial data, etc.) and produces detection results. A consensus strategy then merges all layer outputs into a final set of resolved entities, which are masked before the text leaves the device.

```
User Input
    │
    ▼
┌──────────────────────────────────┐
│  Layer 1: Regex Pattern Matcher  │  (fast, deterministic)
│  Layer 2: Local NER Model        │  (contextual, on-device)
│  Layer 3: Presidio (optional)    │  (enterprise, REST API)
│  Layer N: Custom Model (future)  │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│  Consensus Resolution            │
│  (merge, deduplicate, resolve)   │
└──────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│  Placeholder Masking & Storage   │
│  (reversible on response return) │
└──────────────────────────────────┘
    │
    ▼
  Anonymised text → Router → LLM
```

Each layer operates independently and can fail without bringing down the system. The pipeline degrades
gracefully — if a layer is unavailable, remaining layers continue processing.

> **Masking is reversible per request, and is not currently collision-free.** The placeholder store is
> scoped `WHERE request_id=?` with a 24-hour expiry, so a mapping is usable only by the request that
> created it — there is no restoration across sessions and no cross-prompt reuse. Placeholder indices are
> ordinal within a single request and shared across entity types, so the same value gets a different token
> in a different prompt; choosing that scoping policy deliberately is story **PL1.3**. Separately, both NER
> layers emit a hardcoded constant token per entity type, so several same-type entities in one prompt
> collapse to a single placeholder and restoration substitutes whichever original it meets first — a
> response can return person A's name where person B was referenced. That is story **PL1.1**, and it is a
> live correctness and disclosure defect, not a design trade-off.

## Core Modules

| Module | File | Purpose |
|--------|------|---------|
| Regex patterns | `privacy/regex.tk` | Deterministic pattern matching for structured PII (emails, phone numbers, credit cards, etc.) |
| NER (local) | `privacy/ner_local.tk` | On-device named entity recognition for contextual detection |
| NER (remote) | `privacy/ner.tk` | Remote NER service integration |
| Presidio | `privacy/presidio.tk` | Microsoft Presidio integration via REST API |
| Layer config | `privacy/layer_config.tk` | Layer definitions, priorities, and enable/disable |
| Consensus | `privacy/consensus.tk` | Overlap resolution and multi-layer agreement |
| Entity routing | `privacy/entity_routing.tk` | Per-entity-type layer assignment |
| Pipeline | `privacy/pipeline.tk` | End-to-end orchestration |
| Placeholders | `privacy/placeholder.tk`, `placeholder_store.tk` | Reversible masking and restoration |
| Health | `privacy/layer_health.tk` | Availability monitoring and degradation |
| Evaluation | `privacy/evaluation.tk` | Precision/recall/F1 scoring for layer comparison |
| Metrics | `privacy/filter_metrics.tk` | Detection counts, processing time, confidence tracking |
| Test harness | `privacy/test_harness.tk` | Automated testing with labelled datasets |

## Configuring Layers

Layer configuration is managed through `layer_config.tk`. Each layer entry specifies:

- **id** — Unique identifier (e.g., `"regex"`, `"ner"`, `"presidio"`)
- **enabled** — Whether the layer participates in detection
- **priority** — Lower number = higher priority (used by `first-match` strategy)
- **mode** — `"detect-and-mask"` (full pipeline) or `"detect-only"` (reporting without masking)
- **confidencethreshold** — Minimum confidence score to accept a detection (0.0 to 1.0)
- **entityfilter** — Comma-separated entity types to restrict detection scope (empty = all)

### Default Configuration

```
Layer 1: regex     — enabled, priority 1, detect-and-mask, threshold 0.80
Layer 2: ner       — enabled, priority 2, detect-and-mask, threshold 0.75
Layer 3: presidio  — disabled, priority 3, detect-only,     threshold 0.70
```

The default setup uses two on-device layers (regex + NER) for zero-network-dependency operation. Presidio is disabled by default because it requires a separate service.

### Enabling Presidio

To enable Presidio:

1. Install and start the Presidio analyser service (default: `http://localhost:5001`)
2. Set the Presidio layer to `enabled: true` in your configuration
3. Optionally change its mode from `"detect-only"` to `"detect-and-mask"`

## Consensus Strategies

When multiple layers detect entities, overlaps and disagreements must be resolved. The consensus strategy is
the mechanism specified to do that, and the four strategies below are what it specifies.

> **None of the four is implemented.** `consensus.tk`'s `resolveoverlaps(detections, strategy)` ignores its
> `strategy` argument entirely: it marks every detection `action: "mask"` and returns them, with no overlap
> resolution and no deduplication. `strategyname()` returns a display string and nothing more. Neither
> `consensus.tk` nor `layer_config.tk` has an importer outside the test tree, so the configured strategy and
> the configured confidence thresholds are not read on any request path. The effective behaviour today is
> closest to `most-restrictive` — everything any layer flags gets masked — but it is that by omission, not by
> selection, and selecting `unanimous`, `first-match` or `majority` changes nothing. Read this section as the
> specification. Recorded as B1 and E3 in [claims.md](claims.md).

### most-restrictive (default)

**Union of all detections.** If any layer flags something as sensitive, it gets masked. This is the safest option and the recommended default.

- Best for: regulatory compliance, maximum privacy protection
- Trade-off: higher false positive rate

### first-match

**Highest priority layer wins.** When detections overlap, the layer with the lowest priority number takes precedence. Other layers' detections for the same span are discarded.

- Best for: performance-sensitive deployments where one layer is trusted
- Trade-off: misses from the primary layer are not caught by others

### unanimous

**All layers must agree.** Only entities detected by every enabled layer are masked. This produces the highest precision but may miss entities.

- Best for: minimising false positives when over-masking disrupts workflows
- Trade-off: higher false negative rate

### majority

**More than 50% of layers must agree.** A middle ground between most-restrictive and unanimous.

- Best for: balanced deployments with three or more layers
- Trade-off: requires an odd number of layers for clean tie-breaking

## Per-Entity-Type Routing

The entity routing module (`entity_routing.tk`) allows different entity types to be processed by different layers. For example:

- Email addresses and phone numbers route to the regex layer (high-precision patterns)
- Person names and organisations route to the NER layer (contextual understanding)
- Medical record numbers route to Presidio (domain-specific models)

This allows each layer to focus on what it does best, reducing false positives while maintaining coverage.

### Configuring Routes

Entity routes are defined as mappings from entity type to layer ID. When a route is defined for an entity type, only the specified layer processes that type. Unrouted entity types are processed by all enabled layers and resolved via the consensus strategy.

## Health Monitoring and Graceful Degradation

The health system (`layer_health.tk`) continuously tracks layer availability:

- **HEALTHY** — All enabled layers are responding
- **DEGRADED** — At least one layer is unavailable, but the system continues with remaining layers

### Degradation Behaviour

When a layer becomes unavailable:

1. The health monitor marks it as unavailable with a reason
2. The pipeline skips the unavailable layer during processing
3. Remaining layers continue to provide protection
4. The system reports degraded status through the health endpoint

The system remains operational as long as at least one layer is available. A zero-layer state is reported as unhealthy.

> **Graceful degradation is not the same as failing safe, and one path currently fails open.** In
> `packages/browser/pages/api/pipeline.tk`, when the detection sidecar is unavailable the handler falls back
> to five `str.contains` checks that only *count* occurrences — the outbound text is left unmodified — and
> the request is transmitted anyway. A filter that fails open is worse than one that fails closed, because
> the caller is told a filter ran. Returning 503 and never dispatching when no detection layer is healthy is
> story **NC1.9**.

### Monitoring

Use `formathealthstatus` to get a human-readable health summary:

- `"HEALTHY: all 3 layers available"`
- `"DEGRADED: 2/3 layers available"`

## Evaluation Mode (F3b.9)

The evaluation module (`evaluation.tk`) supports measuring layer quality against labelled datasets. For each layer, it computes:

- **Precision** — Of all detections, how many were correct? `TP / (TP + FP)`
- **Recall** — Of all actual sensitive items, how many were found? `TP / (TP + FN)`
- **F1 Score** — Harmonic mean of precision and recall

### Usage

1. Prepare a labelled dataset with known sensitive entities
2. Run each layer against the dataset and record: detections made, labels in ground truth, matches between detections and labels
3. Call `evaluatelayer(layerid, detected, labelled, matched)` for each layer
4. Compare results using `formatresult` for human-readable output

### Comparison Matrix

The `$comparisonmatrix` type aggregates evaluation results across all layers, tracking total labelled entities and total texts processed. This supports side-by-side layer comparison and informed tuning decisions.

## Metrics (F3b.10)

The metrics module (`filter_metrics.tk`) tracks operational statistics per layer:

- **Detection count** — Total entities detected
- **Processing time** — Cumulative milliseconds spent in detection
- **Average confidence** — Mean confidence score of detections
- **Entity counts** — Breakdown by entity type (JSON string)

### Aggregate Metrics

The `$metricsaggregate` type rolls up per-layer metrics into system-wide totals:

- Total requests processed
- Total detections across all layers
- Average processing time per request

Use `formatmetric` for human-readable per-layer summaries.

## What a Disclosure Measure Cannot Capture (EM1.5)

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
[metrics-baseline.md](metrics-baseline.md) — which currently publishes none.

## Adding Custom Models (Future: F3b.7)

The filter registry (`filter_registry.tk`) is designed to support pluggable detection layers. To add a custom model:

1. Implement a detection function that accepts text and returns an array of detections with entity type, value, position, and confidence
2. Register the layer with a unique ID in the filter registry
3. Add a layer entry in `layer_config.tk` with appropriate priority and threshold
4. Optionally configure entity routing to direct specific entity types to the new layer

Custom models can be:

- Local inference models (ONNX, CoreML on macOS)
- REST API endpoints (like Presidio)
- Rule-based systems (like the regex layer)

The only requirement is that the layer produces detections in the standard `$layerdetection` format used by the consensus module.

## Regulatory Presets

> **These are policy presets, not compliance.** Each block below is a set of defaults chosen as a
> defensible opening position under the named regulation. Selecting one does not make a deployment
> compliant with it: compliance is a property of an organisation's processing as a whole and is determined
> by that organisation and its assessor. The full preset specification, with the same caveat stated at
> greater length, is [specifications/regulatory-defaults.md](specifications/regulatory-defaults.md).

### GDPR (EU General Data Protection Regulation)

Settings the GDPR preset ships:

- **Consensus strategy:** `most-restrictive` — the widest-coverage setting: everything any layer flags is
  masked. It maximises what is caught; it does not ensure that everything sensitive is found (see
  [threat-model.md](threat-model.md) §10.6). Note that the setting is not currently read by any code — see
  the note under Consensus Strategies above
- **All layers enabled** — maximum coverage
- **Confidence thresholds:** lower (0.6-0.7) to catch edge cases
- **Entity types:** EMAIL, PHONE, PERSON, ADDRESS, DATE_OF_BIRTH, IBAN, NATIONAL_ID
- **Mode:** `detect-and-mask` on all layers
- **Presidio:** enable if available, for multilingual European name detection

Key GDPR considerations:
- Article 5(1)(c) requires data minimisation — mask everything not essential
- Article 25 requires data protection by design. A pipeline-first architecture is evidence toward that, not a determination of compliance — which is a matter for the deployment and its assessor, not for loke
- Deleting the local mapping makes the *local* placeholder-to-original association unrecoverable. It does **not** reach data already transmitted to and retained by a provider, so it is not on its own an Article 17 mechanism

### HIPAA (US Health Insurance Portability and Accountability Act)

Settings the HIPAA preset ships:

- **Consensus strategy:** `most-restrictive`
- **All layers enabled** with Presidio configured for healthcare
- **Entity types:** PERSON, DATE_OF_BIRTH, MEDICAL_RECORD, SSN, PHONE, EMAIL, ADDRESS, DEVICE_ID, HEALTH_PLAN_ID
- **Confidence thresholds:** conservative (0.6) — HIPAA penalties are severe
- **Mode:** `detect-and-mask` on all layers
- **Additional:** enable audit logging for all detection events

HIPAA requires protection of 18 specific PHI identifiers. Configure entity routing so each identifier type
is routed to at least one layer. Routing determines which layer *attempts* detection; it does not establish
that detection succeeds — see `specifications/regulatory-defaults.md` §4.4 on why this preset does not
support a Safe Harbor determination.

### Australian Privacy Act (Privacy Act 1988 + 2024 Amendments)

Settings the Australian Privacy Act preset ships:

- **Consensus strategy:** `most-restrictive`
- **Regex + NER layers enabled** (Presidio optional)
- **Entity types:** PERSON, TFN (Tax File Number), MEDICARE, PHONE, EMAIL, ADDRESS, DATE_OF_BIRTH, DRIVERS_LICENCE, PASSPORT
- **Confidence thresholds:** moderate (0.7)
- **Mode:** `detect-and-mask` on all layers

Key considerations:
- APP 6 restricts use and disclosure of personal information — mask before sending to external LLMs
- APP 11 requires reasonable security. Multi-layer detection is one input to that assessment, not a
  determination of it — the same distinction the Article 25 note above draws
- The 2024 amendments introduce a statutory tort for serious privacy invasions — defence-in-depth via multiple layers provides evidence of reasonable precautions

### Custom Preset Profiles

For organisations with specific requirements:

1. Start with the `most-restrictive` consensus strategy
2. Enable all available layers
3. Define entity routing for domain-specific identifiers
4. Set confidence thresholds based on your risk tolerance (lower = more cautious)
5. Use evaluation mode to measure detection quality against your own labelled data
6. Monitor metrics to identify gaps and tune accordingly

## Migration Guide for Existing Deployments

### From Single-Layer to Multi-Layer

If you are running an earlier version of loke with a single privacy filter:

1. **No data migration required** — the placeholder store format is unchanged
2. **Update configuration** — your existing regex patterns continue to work as Layer 1
3. **Enable NER** — add the NER layer as Layer 2 for contextual detection
4. **Set consensus strategy** — start with `most-restrictive` for maximum safety
5. **Monitor** — use the metrics module to compare detection rates before and after

### Enabling Evaluation Mode

1. Collect a sample of texts with manually labelled sensitive entities
2. Run each layer independently against the sample
3. Use `evaluatelayer` to compute precision, recall, and F1 for each layer
4. Adjust confidence thresholds based on results
5. Re-evaluate after threshold changes to confirm improvement

### Performance Considerations

- The regex layer is the fastest (microseconds per text) — always keep it enabled
- The NER layer adds milliseconds per text but catches entities regex misses
- Presidio adds network latency (tens of milliseconds) — consider `detect-only` mode for monitoring without blocking
- Use metrics to track processing time and set appropriate timeouts
