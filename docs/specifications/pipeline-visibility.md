# Pipeline Visibility Panel Specification

**Story:** A4.2 — Pipeline visibility panel
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

The pipeline visibility panel provides real-time, stage-by-stage insight into what loke does with every request and response. It is the primary mechanism through which users understand what happened to their data — which PII was detected, how tokens were optimised, why a particular model was selected, and how long each step took.

This specification defines:

- The pipeline stage model and stage status lifecycle
- Browser mode panel (dockable, collapsible, real-time stage progression)
- Terminal mode output (`--verbose` flag, structured logging, colour coding)
- Per-stage detail views and the data surfaced at each stage
- Timing, streaming behaviour, history, accessibility, and configuration

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Feedback is first-class.** The visibility panel is not a debug tool — it is a core product feature that reinforces trust by showing users exactly what happened.
- **Complexity is available, not imposed.** The panel follows the four-layer visibility model: Layer 0 (summary), Layer 1 (one click deeper), Layer 2 (full pipeline view), Layer 3 (expert/raw data). Users choose their depth.
- **The user is the authority.** Every decision loke makes is visible and explainable. The panel is the "show your working" surface.
- **Default: transparent.** The pipeline is never hidden behind a loading spinner. Users always have access to what is happening, even during streaming.
- **Speed is a feature.** The panel itself must not degrade pipeline performance. All visibility data is collected as a side effect of pipeline execution, not via additional computation.

---

## 2. Pipeline Stage Model

### 2.1 Enumerated Stages

Every request passing through loke traverses a fixed sequence of stages. Some stages may be skipped based on configuration or request characteristics, but the model always contains all stages.

| Stage ID | Display Name | Direction | Description |
|----------|-------------|-----------|-------------|
| `input` | Input | Request | User prompt received, pre-processing begun |
| `privacy_scan` | Privacy Scan | Request | PII detection across all configured layers |
| `anonymisation` | Anonymisation | Request | PII replacement with reversible placeholders |
| `token_optimisation` | Token Optimisation | Request | Compression, format conversion, cache check |
| `routing` | Routing | Request | Model selection based on intent, sensitivity, cost, policy |
| `llm_call` | LLM Call | Request/Response | Request sent to selected model, response streamed back |
| `response_scan` | Response Scan | Response | Compliance check on LLM response content |
| `deanonymisation` | De-anonymisation | Response | Placeholder restoration to original values |
| `output` | Output | Response | Final response delivered to user |

### 2.2 Stage Status Lifecycle

Each stage progresses through a defined set of statuses:

| Status | Meaning | Visual Indicator (Browser) | Terminal Indicator |
|--------|---------|----------------------------|-------------------|
| `pending` | Not yet reached | Grey circle | `[ ]` |
| `active` | Currently executing | Blue pulsing circle | `[>]` with spinner |
| `complete` | Finished successfully | Green filled circle | `[✓]` |
| `skipped` | Intentionally bypassed | Grey dash | `[-]` |
| `error` | Failed (pipeline may continue or halt) | Red filled circle | `[✗]` |

Status transitions follow a strict order: `pending` -> `active` -> `complete` | `skipped` | `error`. A stage cannot return to a previous status. The `skipped` status is set directly from `pending` without passing through `active`.

### 2.3 Stage Event Model

Each stage emits structured events as it executes. These events drive both the browser panel and terminal output.

```typescript
interface PipelineStageEvent {
  request_id: string;            // Unique identifier for this pipeline run
  stage_id: StageId;             // One of the enumerated stage IDs
  status: StageStatus;           // pending | active | complete | skipped | error
  timestamp: number;             // Unix timestamp in milliseconds
  duration_ms?: number;          // Set on complete/error — time spent in this stage
  summary?: string;              // One-line human-readable summary
  detail?: StageDetail;          // Stage-specific structured data (section 4)
  error?: {
    code: string;                // Machine-readable error code
    message: string;             // Human-readable error message
    recoverable: boolean;        // Whether the pipeline continued
  };
}
```

Events are emitted via an internal event bus. The browser panel and terminal output are both consumers of this bus — they do not poll or query the pipeline.

---

## 3. Browser Mode Panel

### 3.1 Panel Placement and Docking

The pipeline visibility panel is a dockable panel within the browser mode workspace. It supports the following positions:

| Position | Description |
|----------|-------------|
| **Bottom** (default) | Horizontal panel below the main content area, similar to a browser DevTools panel |
| **Right** | Vertical panel to the right of the main content area |
| **Detached** | Floating window, independently positionable and resizable |

The panel position is persisted across sessions. The user can drag the panel between positions or use the panel menu to select a position.

### 3.2 Panel States

| State | Description | Default |
|-------|-------------|---------|
| **Collapsed** | Single-line summary bar showing the most recent pipeline result (e.g. "3 PII anonymised, 42% token savings, routed to Claude Sonnet") | No |
| **Compact** | Stage progression bar with icons and one-line summaries per stage | Yes |
| **Expanded** | Full panel with expandable detail sections per stage | No |

The panel state is persisted across sessions. A keyboard shortcut toggles between collapsed and the last-used expanded state (compact or expanded).

### 3.3 Stage Progression Display

In compact and expanded modes, the panel displays a horizontal (bottom dock) or vertical (right dock) progression of all nine stages.

Each stage is rendered as:

```
[status icon] Stage Name ── summary text ── duration
```

Stages transition visually in real time as the pipeline executes:

- **Pending** stages are dimmed.
- The **active** stage has a pulsing indicator and may show a progress description (e.g. "Scanning with NLP layer...").
- **Complete** stages show their one-line summary and duration.
- **Skipped** stages are visually de-emphasised (greyed out, reduced height) but still present to maintain positional consistency.
- **Error** stages are highlighted in red with the error message visible.

### 3.4 Expandable Stage Details

In expanded mode, each complete stage is clickable to reveal its detail view. Detail views are stage-specific (defined in section 4). Only one stage detail can be expanded at a time by default, though a user preference allows multiple simultaneous expansions.

The detail view slides open below (bottom dock) or beside (right dock) the stage row. It contains:

1. **Summary section** — key metrics in a scannable grid
2. **Detail section** — full structured data, collapsible sub-sections
3. **Feedback control** — thumbs up/down on the stage result (per design principle 3)

### 3.5 Visibility Layers

The panel implements the four-layer visibility model from the design principles:

| Layer | What Is Shown | Where |
|-------|---------------|-------|
| **Layer 0** | Transparency bar in chat panel: "3 PII anonymised, 42% savings, Claude Sonnet, 1.2s" | Always visible in chat interface |
| **Layer 1** | Collapsed pipeline panel: one-line per stage | One click from Layer 0 |
| **Layer 2** | Expanded pipeline panel with per-stage details | Click any stage in Layer 1 |
| **Layer 3** | Raw request/response payloads, full timing breakdown, model confidence scores, cache state | "Show raw data" toggle within Layer 2 |

Layer 3 data is rendered in a monospace font with syntax highlighting. Payloads are truncatable with a "show full" toggle for large content. PII values are never shown in Layer 3 — only placeholders and metadata.

---

## 4. Per-Stage Detail Views

Each pipeline stage exposes structured detail data. This section defines the data model and display for each stage.

### 4.1 Input

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Where the input came from: `chat`, `cli`, `mcp_tool`, `proxy` |
| `content_type` | string | `text`, `text+image`, `text+file`, `tool_call` |
| `character_count` | integer | Length of the input content |
| `estimated_tokens` | integer | Pre-pipeline token estimate |
| `has_attachments` | boolean | Whether files or images are attached |
| `mcp_tool_name` | string or null | If this is an MCP tool call, which tool |

This stage is informational. It is typically shown in compact form without an expandable detail view.

### 4.2 Privacy Scan

The privacy scan detail view shows what PII was detected and by which detection layer.

| Field | Type | Description |
|-------|------|-------------|
| `entities_found` | integer | Total PII entities detected |
| `entity_types` | list of `EntityTypeSummary` | Breakdown by type |
| `layers_used` | list of string | Detection layers that ran (e.g. `["regex", "nlp", "slm_ner"]`) |
| `scan_duration_ms` | integer | Time spent scanning |

**`EntityTypeSummary`:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | PII type identifier (e.g. `email_address`, `person_name`) |
| `display_name` | string | Human-readable name (e.g. "Email address", "Person name") |
| `count` | integer | Number of entities of this type found |
| `highest_confidence` | float (0.0–1.0) | Highest confidence score among entities of this type |
| `detected_by` | list of string | Layers that contributed to detection (e.g. `["regex"]`, `["nlp", "slm_ner"]`) |

**Browser display:**

- Summary line: "Found 7 PII entities across 4 types"
- Expandable table showing entity types, counts, confidence, and detecting layer
- No actual PII values are ever displayed in the panel — only types and counts
- Colour-coded confidence: green (> 0.9), amber (0.7–0.9), red (< 0.7)
- Each row indicates which detection layer(s) identified that type

**Terminal display:**

```
[✓] Privacy Scan         7 entities (3 email, 2 name, 1 phone, 1 address)  12ms
```

With `--verbose`:

```
[✓] Privacy Scan                                                           12ms
    ├─ email_address     ×3  confidence: 0.99  layer: regex
    ├─ person_name       ×2  confidence: 0.87  layer: nlp, slm_ner
    ├─ phone_number      ×1  confidence: 0.95  layer: regex
    └─ street_address    ×1  confidence: 0.72  layer: slm_ner
```

### 4.3 Anonymisation

| Field | Type | Description |
|-------|------|-------------|
| `entities_anonymised` | integer | Total entities replaced with placeholders |
| `entities_skipped` | integer | Entities detected but not anonymised (below threshold or policy-excluded) |
| `anonymisation_actions` | list of `AnonymisationActionSummary` | Breakdown by action type |
| `placeholder_types_used` | list of string | Types of placeholders generated (e.g. `$e`, `$p`, `$l`) |

**`AnonymisationActionSummary`:**

| Field | Type | Description |
|-------|------|-------------|
| `entity_type` | string | PII type identifier |
| `action` | string | `anonymise`, `redact`, `hash`, or `mask` |
| `count` | integer | Number of entities handled with this action |

**Browser display:**

- Summary line: "Anonymised 6 entities, skipped 1 (below threshold)"
- Table: entity type, action taken, count
- Visual legend of placeholder types used

**Terminal display:**

```
[✓] Anonymisation        6 anonymised, 1 skipped                           3ms
```

With `--verbose`:

```
[✓] Anonymisation                                                           3ms
    ├─ email_address     ×3  action: anonymise  → $e1, $e2, $e3
    ├─ person_name       ×2  action: anonymise  → $p1, $p2
    ├─ phone_number      ×1  action: redact     → [PHONE]
    └─ street_address    ×1  action: skipped    (confidence 0.72 < threshold 0.80)
```

### 4.4 Token Optimisation

| Field | Type | Description |
|-------|------|-------------|
| `original_tokens` | integer | Token count before optimisation |
| `optimised_tokens` | integer | Token count after optimisation |
| `savings_percentage` | float | Percentage reduction |
| `methods_applied` | list of `OptimisationMethod` | Methods used and their individual contributions |
| `cache_hit` | boolean | Whether a semantic cache hit was found |
| `cache_similarity` | float or null | Similarity score if cache was checked (0.0–1.0) |

**`OptimisationMethod`:**

| Field | Type | Description |
|-------|------|-------------|
| `method` | string | `toon`, `llmlingua`, `semantic_cache`, `deduplication` |
| `display_name` | string | Human-readable name (e.g. "TOON format conversion", "LLMLingua compression") |
| `tokens_before` | integer | Tokens entering this method |
| `tokens_after` | integer | Tokens leaving this method |
| `savings_percentage` | float | This method's contribution to savings |

**Browser display:**

- Summary line: "1,240 → 720 tokens (42% saved)"
- Bar chart showing original vs optimised token count
- Breakdown table: method, tokens saved, percentage
- Cache hit/miss indicator with similarity score

**Terminal display:**

```
[✓] Token Optimisation   1,240 → 720 tokens (42% saved)                    8ms
```

With `--verbose`:

```
[✓] Token Optimisation   1,240 → 720 tokens (42% saved)                    8ms
    ├─ TOON conversion   1,240 → 980 tokens (21%)
    ├─ LLMLingua         980 → 720 tokens (27%)
    └─ Cache             miss (similarity: 0.62, threshold: 0.85)
```

### 4.5 Routing

| Field | Type | Description |
|-------|------|-------------|
| `selected_model` | string | Model ID selected (e.g. `claude-sonnet-4-20250514`) |
| `selected_provider` | string | Provider ID (e.g. `anthropic`, `ollama`) |
| `routing_strategy` | string | Active strategy: `cheapest_adequate`, `fastest`, `best_quality`, `local_first` |
| `selection_reason` | string | Human-readable explanation of why this model was chosen |
| `sensitivity_level` | string | Classification level of this request (`public`, `internal`, `confidential`, `restricted`) |
| `intent_category` | string | Classified intent (e.g. `code_generation`, `analysis`, `creative_writing`, `conversation`) |
| `intent_confidence` | float | Confidence of intent classification (0.0–1.0) |
| `fallback_chain` | list of string | Ordered list of models that would be tried if the selected model fails |
| `candidates_considered` | list of `ModelCandidate` | Models evaluated during selection |
| `policy_constraints` | list of string | Policy rules that influenced the decision |

**`ModelCandidate`:**

| Field | Type | Description |
|-------|------|-------------|
| `model_id` | string | Model identifier |
| `provider` | string | Provider identifier |
| `score` | float | Composite selection score |
| `eliminated_reason` | string or null | Why this candidate was not selected (null for the winner) |

**Browser display:**

- Summary line: "Claude Sonnet via Anthropic (cheapest-adequate, confidential)"
- Decision explanation card: plain-language sentence explaining the routing choice
- Candidate comparison table (Layer 2): all models considered, their scores, and elimination reasons
- Sensitivity badge with colour matching the classification level
- Policy constraints listed if any influenced the decision

**Terminal display:**

```
[✓] Routing              claude-sonnet-4 via anthropic (cheapest-adequate)  2ms
```

With `--verbose`:

```
[✓] Routing              claude-sonnet-4 via anthropic                      2ms
    ├─ Strategy          cheapest-adequate
    ├─ Sensitivity       confidential
    ├─ Intent            code_generation (0.94)
    ├─ Reason            Meets capability threshold; lowest cost for task type
    ├─ Fallback          → qwen3-32b (ollama) → gpt-4o-mini (openai)
    └─ Policy            provider allowed for confidential data
```

### 4.6 LLM Call

| Field | Type | Description |
|-------|------|-------------|
| `provider` | string | Provider used |
| `model` | string | Model used |
| `is_local` | boolean | Whether the model ran locally |
| `latency_ms` | integer | Time from request sent to last token received |
| `time_to_first_token_ms` | integer | Time from request sent to first response token |
| `tokens_sent` | integer | Prompt tokens consumed |
| `tokens_received` | integer | Completion tokens generated |
| `total_tokens` | integer | Sum of sent and received |
| `estimated_cost` | float | Estimated cost in configured currency |
| `currency` | string | Currency code (ISO 4217) |
| `streaming` | boolean | Whether the response was streamed |
| `tool_calls` | integer | Number of tool calls made by the model (if any) |
| `stop_reason` | string | Why generation stopped: `end_turn`, `max_tokens`, `tool_use`, `content_filter` |

**Browser display:**

- Summary line: "Claude Sonnet, 1.8s, 720 in / 340 out, ~$0.004"
- Latency timeline showing time-to-first-token and total duration
- Token usage bar (sent vs received)
- Cost displayed with currency symbol
- Local/cloud badge

**Terminal display:**

```
[✓] LLM Call             claude-sonnet-4 (anthropic) 720→340 tokens  $0.004  1.8s
```

With `--verbose`:

```
[✓] LLM Call             claude-sonnet-4 (anthropic)                       1.8s
    ├─ Tokens            720 sent, 340 received (1,060 total)
    ├─ First token       210ms
    ├─ Cost              $0.004 USD
    ├─ Streaming         yes
    ├─ Tool calls        0
    └─ Stop reason       end_turn
```

### 4.7 Response Scan

| Field | Type | Description |
|-------|------|-------------|
| `violations_found` | integer | Number of compliance violations detected |
| `violations` | list of `Violation` | Details of each violation |
| `checks_performed` | list of string | Compliance checks that ran |
| `clean` | boolean | True if no violations found |

**`Violation`:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Violation type (e.g. `pii_in_response`, `policy_breach`, `content_filter`) |
| `severity` | string | `info`, `advisory`, `warning`, `block` |
| `description` | string | Human-readable description |
| `action_taken` | string | What loke did about it (e.g. `flagged`, `redacted`, `blocked`) |

**Browser display:**

- Summary line: "Clean — no violations" or "2 violations found"
- If violations present: severity-coloured list with descriptions and actions taken
- If clean: green checkmark, no expansion needed

**Terminal display:**

```
[✓] Response Scan        clean                                              1ms
```

With violations:

```
[✓] Response Scan        2 violations found                                 1ms
    ├─ WARNING  pii_in_response    Model returned email address → redacted
    └─ INFO     content_filter     Mildly sensitive content flagged
```

### 4.8 De-anonymisation

| Field | Type | Description |
|-------|------|-------------|
| `placeholders_restored` | integer | Number of placeholders replaced with original values |
| `placeholders_unmatched` | integer | Placeholders in response that had no mapping (model hallucinated a placeholder) |
| `restoration_types` | list of `RestorationSummary` | Breakdown by entity type |

**`RestorationSummary`:**

| Field | Type | Description |
|-------|------|-------------|
| `entity_type` | string | PII type identifier |
| `count` | integer | Number of placeholders of this type restored |

**Browser display:**

- Summary line: "5 placeholders restored"
- If unmatched placeholders exist: warning indicator with count
- Type breakdown table

**Terminal display:**

```
[✓] De-anonymisation     5 restored, 0 unmatched                           1ms
```

With `--verbose`:

```
[✓] De-anonymisation     5 restored, 0 unmatched                           1ms
    ├─ email_address     ×3 restored
    └─ person_name       ×2 restored
```

### 4.9 Output

| Field | Type | Description |
|-------|------|-------------|
| `character_count` | integer | Length of the final output |
| `token_count` | integer | Estimated tokens in the output |
| `total_pipeline_time_ms` | integer | End-to-end pipeline duration |
| `total_pipeline_overhead_ms` | integer | Pipeline time minus LLM call time |

This stage primarily serves as the pipeline timing summary. It is shown inline rather than as an expandable detail.

---

## 5. Timing Information

### 5.1 Per-Stage Latency

Every stage records its start time and end time. The duration is computed as `end - start` in milliseconds. Timing is collected via `performance.now()` (or equivalent high-resolution timer) to avoid wall-clock drift.

### 5.2 Pipeline Timing Summary

The output stage aggregates timing into a summary:

| Metric | Calculation | Target |
|--------|-------------|--------|
| **Total pipeline time** | Input start to output end | Varies by LLM latency |
| **Pipeline overhead** | Total time minus LLM call duration | < 1 second for typical prompts |
| **Privacy processing** | Privacy scan + anonymisation | < 200ms typical |
| **Optimisation** | Token optimisation duration | < 500ms typical |
| **Routing** | Routing stage duration | < 50ms typical |
| **Response processing** | Response scan + de-anonymisation | < 100ms typical |

### 5.3 Browser Timing Display

In expanded mode, a timing waterfall chart shows all stages as horizontal bars on a shared timeline. This is similar to a network waterfall in browser DevTools. Stages are stacked vertically in pipeline order, with bar length proportional to duration. The LLM call stage is visually distinct (different colour) since it typically dominates total time.

### 5.4 Terminal Timing Display

The `--verbose` flag appends duration to every stage line (as shown in section 4 examples). A summary line is printed after the pipeline completes:

```
Pipeline complete: 1,847ms total (overhead: 27ms)
```

With `--verbose --timing` (or `--timing` alone for timing-only output):

```
Timing breakdown:
  Input               1ms
  Privacy Scan       12ms
  Anonymisation       3ms
  Token Optimisation   8ms
  Routing              2ms
  LLM Call         1,820ms  ████████████████████████████████████████  (98.5%)
  Response Scan       1ms
  De-anonymisation    1ms
  Output              0ms
  ─────────────────────────
  Total            1,847ms
  Overhead            27ms
```

---

## 6. Streaming Behaviour

### 6.1 Stage Updates During Streaming

During a streaming LLM response, the pipeline visibility panel must handle the fact that some stages are complete (request-side), one is actively streaming (LLM call), and others are pending (response-side).

**Update sequence:**

1. Input through routing stages update in real time as they complete (typically sub-second total).
2. The LLM call stage enters `active` status and displays a streaming indicator.
3. During streaming, the LLM call detail view updates incrementally:
   - `tokens_received` increments as tokens arrive
   - `latency_ms` updates as a running timer
   - `time_to_first_token_ms` is set when the first token arrives
   - `estimated_cost` updates in real time
4. When streaming completes, the LLM call stage transitions to `complete`.
5. Response-side stages (response scan, de-anonymisation, output) execute and update.

### 6.2 Browser Streaming Display

- The active stage pulses during streaming.
- Token count and cost update live (throttled to 4 updates per second to avoid excessive rendering).
- The user can expand the LLM call detail view during streaming to watch metrics accumulate.
- Response-side stages remain in `pending` status during streaming; they do not appear to "jump" when they execute rapidly after streaming completes.

### 6.3 Terminal Streaming Display

In terminal mode, the stage progression is printed line by line as each stage completes. During the LLM call stage, the response is streamed to stdout as normal. The stage completion line for `llm_call` is printed after the response finishes streaming.

With `--verbose`, a spinner or progress indicator shows the LLM call is active:

```
[✓] Routing              claude-sonnet-4 via anthropic (cheapest-adequate)  2ms
[>] LLM Call             streaming... (340 tokens, 1.2s)
```

After completion:

```
[✓] LLM Call             claude-sonnet-4 (anthropic) 720→340 tokens  $0.004  1.8s
```

### 6.4 De-anonymisation During Streaming

De-anonymisation of streamed response tokens happens in real time. As each chunk arrives, placeholders within the chunk are restored before the chunk is displayed to the user. The de-anonymisation stage's running count updates accordingly, but the stage is not marked `complete` until the full response has been processed. In the terminal, the user sees restored text — never raw placeholders.

---

## 7. History

### 7.1 Pipeline Run Persistence

Every pipeline run is persisted to the local database alongside the conversation it belongs to. The stored record includes:

- All stage events with timestamps, statuses, and durations
- All per-stage detail data as defined in section 4
- The pipeline timing summary
- The active policy hash at time of execution

Pipeline records are retained for the same duration as conversation history (governed by the retention policy, default 90 days).

### 7.2 Accessing Historical Pipeline Views

**Browser mode:**

- Each message in the conversation history has a small pipeline indicator icon. Clicking it opens the pipeline visibility panel populated with that message's pipeline data.
- The panel renders identically to a live pipeline view, but with all stages in their final state (no animations).
- A "Replay" mode animates the stage progression using the recorded timestamps, for understanding the sequence of events.

**Terminal mode:**

- `loke history <session-id>` lists past requests with pipeline summaries.
- `loke history <session-id> --request <n>` shows the full pipeline detail for a specific request.
- `loke history <session-id> --request <n> --verbose` shows the same level of detail as live `--verbose` output.

### 7.3 Pipeline Comparison

Users can select two historical pipeline runs and compare them side by side. This is useful for understanding why the same prompt was routed differently on different occasions, or for verifying that a configuration change had the intended effect.

In browser mode, this is a split view within the panel. In terminal mode, `loke history diff <session-id>:<n> <session-id>:<m>` outputs a diff.

---

## 8. Accessibility

### 8.1 Screen Reader Support

The pipeline visibility panel is fully accessible via screen reader:

- Each stage transition is announced as a live region update (ARIA `role="log"` with `aria-live="polite"`).
- Stage status changes are announced: "Privacy Scan complete: 7 entities found across 4 types, 12 milliseconds."
- Error states use `aria-live="assertive"` for immediate announcement.
- During streaming, updates are throttled to avoid overwhelming the screen reader — a summary announcement is made every 5 seconds: "LLM call in progress: 200 tokens received, 1.5 seconds elapsed."
- On pipeline completion, a summary announcement is made: "Pipeline complete. 6 entities anonymised, 42% token savings, Claude Sonnet, 1.8 seconds total."

### 8.2 Keyboard Navigation

| Key | Action |
|-----|--------|
| `Ctrl+Shift+P` (configurable) | Toggle pipeline panel visibility |
| `Tab` / `Shift+Tab` | Move between stages |
| `Enter` / `Space` | Expand/collapse stage detail |
| `Escape` | Collapse current stage detail, or close panel if no detail is open |
| `Home` / `End` | Jump to first/last stage |
| `1`–`9` | Jump to stage by number (when panel is focused) |

### 8.3 Colour Independence

All status information is conveyed through both colour and shape/icon/text. The panel does not rely on colour alone to communicate stage status:

- Complete: green circle **and** checkmark icon **and** "complete" text
- Error: red circle **and** cross icon **and** "error" text
- Skipped: grey dash **and** "skipped" text

High-contrast mode is supported, using the system high-contrast preference.

---

## 9. Configuration

### 9.1 Verbosity Level

The default verbosity determines how much pipeline information is shown without user intervention.

```yaml
# In loke application settings
pipeline_visibility:
  # Default verbosity layer (0-3)
  default_layer: 1

  # Whether the panel is shown by default in browser mode
  panel_visible: true

  # Default panel state: collapsed | compact | expanded
  panel_state: "compact"

  # Default panel position: bottom | right | detached
  panel_position: "bottom"
```

### 9.2 Stage Visibility

Users can configure which stages are shown in the panel. Hidden stages still execute — they are simply not displayed.

```yaml
pipeline_visibility:
  stages:
    input:
      visible: true
    privacy_scan:
      visible: true
    anonymisation:
      visible: true
    token_optimisation:
      visible: true
    routing:
      visible: true
    llm_call:
      visible: true
    response_scan:
      visible: true
    deanonymisation:
      visible: true
    output:
      visible: true
```

Hiding a stage in the panel does not affect logging or audit trail recording. All stages are always recorded regardless of visibility settings.

### 9.3 Terminal Verbosity Flags

| Flag | Effect |
|------|--------|
| (none) | No pipeline output. Response only. |
| `--verbose` or `-v` | Print stage progression with one-line summaries |
| `-vv` | Print stage progression with expanded details (equivalent to Layer 2) |
| `-vvv` | Print stage progression with full raw data (equivalent to Layer 3) |
| `--timing` | Print timing summary only (no stage details) |
| `--quiet` or `-q` | Suppress all output except the response itself |
| `--json` | Output pipeline data as structured JSON (for scripting and piping) |

The `--verbose` flag can also be set as a default in configuration:

```yaml
cli:
  default_verbosity: 0          # 0 = none, 1 = -v, 2 = -vv, 3 = -vvv
```

### 9.4 JSON Output Format

When `--json` is used, the pipeline output is a single JSON object written to stderr (so stdout remains clean for the response text):

```json
{
  "request_id": "req_abc123",
  "total_duration_ms": 1847,
  "overhead_ms": 27,
  "stages": [
    {
      "stage_id": "privacy_scan",
      "status": "complete",
      "duration_ms": 12,
      "summary": "7 entities found across 4 types",
      "detail": { ... }
    }
  ]
}
```

This enables integration with external tools, dashboards, and scripts.

---

## 10. Security Considerations

### 10.1 No PII in Visibility Data

The pipeline visibility panel never displays actual PII values. All detail views show types, counts, confidence scores, and placeholder identifiers — never the original sensitive data. This applies to all layers including Layer 3 (expert/raw data).

Raw request payloads shown in Layer 3 display the anonymised version of the prompt, not the original. The original is accessible only through the secure PII mapping store, subject to deanonymisation policy and authentication requirements.

### 10.2 Terminal Output Safety

Terminal `--verbose` and `--json` output follows the same no-PII rule. Placeholder identifiers (e.g. `$e1`, `$p2`) may appear in verbose output, but never the values they map to. This ensures that terminal output can be safely included in bug reports, shared in team chats, or piped to logging systems without leaking sensitive data.

### 10.3 History Data Protection

Historical pipeline data is stored in the same encrypted SQLite database as conversation history and is subject to the same retention and deletion policies. When a conversation is deleted, its associated pipeline records are deleted as well.

---

## 11. Performance Requirements

| Requirement | Target |
|-------------|--------|
| Event bus overhead per stage | < 1ms |
| Browser panel render (compact mode) | < 16ms (60fps) |
| Browser panel render (expanded mode) | < 50ms |
| Streaming update throttle | 4 updates/second maximum |
| Terminal verbose output overhead | < 5ms per stage line |
| History retrieval for a single pipeline run | < 50ms |
| Pipeline data storage per request | < 5KB typical (without Layer 3 raw payloads) |

The visibility system must not measurably increase pipeline latency. All data collection is performed inline with pipeline execution (timestamps, counts, identifiers) — no additional computation is introduced for visibility purposes.
