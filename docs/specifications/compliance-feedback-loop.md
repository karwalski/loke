# Compliance Feedback Loop — Specification

**Story:** A3.3 — Compliance feedback loop (response scanning, warning UI, require-confirmation mode)
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke's privacy pipeline anonymises outbound prompts before they reach an LLM. But the LLM's *response* may itself contain policy-relevant content: PII that was not in the original prompt (hallucinated or inferred), data at a higher classification than expected, or content that violates regulatory constraints. The compliance feedback loop closes this gap by scanning every LLM response before it is displayed to the user, flagging violations, and optionally requiring explicit acknowledgement before the content is shown.

This specification defines:

- The response scanning pipeline (what is scanned, when, and how)
- Violation types and severity levels
- Warning UI for browser mode and terminal mode
- Require-confirmation mode (block display until user acknowledges)
- Suppression rules ("don't warn again")
- Audit trail integration
- Policy-level configuration for all of the above
- Edge cases: streaming responses, partial matches, MCP tool output

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Warnings must be earned.** The feedback loop uses graduated severity. Low-confidence detections are logged silently rather than interrupting the user. False positives erode trust faster than missed detections erode safety.
- **The user is the authority.** loke advises, the user decides. Even at the highest severity, the default is to warn and require confirmation — not to silently censor. Enterprise hard blocks are the sole exception.
- **Privacy is the foundation.** Response scanning is always on. It cannot be disabled entirely, though its actions (warn vs. block vs. log-only) are configurable.
- **Do the right thing by default.** Out-of-box behaviour catches genuine violations without crying wolf. Sensitivity is tuned conservatively; enterprises can tighten it.

---

## 2. Response Scanning Pipeline

### 2.1 What Gets Scanned

Every piece of content that arrives from an LLM provider or MCP server is scanned before it is presented to the user. Specifically:

| Content type | Scanned | Notes |
|-------------|---------|-------|
| LLM text responses | Yes | Includes both streaming chunks and complete responses |
| LLM tool-call results | Yes | The arguments and return values of tool calls |
| MCP tool output | Yes | Output from any MCP server, local or remote |
| MCP resource content | Yes | Content retrieved via MCP resource URIs |
| Restored (de-anonymised) text | No | Already contains the user's own PII — scanning it would flag the user's own data |
| loke-generated UI text | No | Warnings, status messages, and pipeline metadata are not scanned |

Restored text is exempt because the compliance feedback loop is concerned with *new* policy-relevant content introduced by external systems, not with the user's own data being returned to them.

### 2.2 When Scanning Occurs

Scanning runs at two points in the response lifecycle:

1. **Pre-restoration scan.** The raw LLM response (still containing placeholders like `$c1`, `$l2`) is scanned. This catches content the LLM generated independently of the user's PII — for example, hallucinated names, addresses, or sensitive data categories the LLM introduced on its own.

2. **Post-restoration scan (differential).** After placeholder restoration, a differential scan compares the restored text against the pre-restoration findings. Any *new* detections that were not present in the raw response and do not correspond to a restored placeholder are flagged. This catches cases where the combination of restored PII and LLM-generated context creates a new violation (e.g., the LLM generated "the patient at $l1 was diagnosed with..." and restoration fills in a real address, creating a health-data-plus-location combination that may exceed the original classification).

The differential scan is lightweight — it only re-examines regions around restored placeholders and any new detections, not the entire response.

### 2.3 Detection Layers

Response scanning reuses the same 4-layer PII detection pipeline used for outbound anonymisation (regex, NLP/compromise.js, SLM NER, Presidio), but with two differences:

1. **Confidence threshold is higher.** Outbound scanning errs on the side of caution (anonymise if in doubt). Response scanning errs on the side of not crying wolf (warn only if confident). The default minimum confidence for a response violation is 0.80, versus 0.50 for outbound detection.

2. **Classification-aware scanning.** Response detections are cross-referenced against the active policy's data classification rules. A detected email address is only a violation if the response's effective classification level prohibits email addresses. Detection alone is not a violation — detection *plus policy rule* is.

### 2.4 Violation Assessment

Each detection is assessed against the active policy to determine whether it constitutes a violation:

```
detection + policy rule + context -> violation (or not)
```

The assessment considers:

- **Entity type detected** (e.g., `person_name`, `email_address`, `medical_record`)
- **Detection confidence** (0.0 to 1.0)
- **Data classification level** assigned to the entity type by the active policy
- **Response context classification** — the overall sensitivity of the conversation as determined by the outbound scan
- **Provider trust level** — whether the response came from a local model (higher trust) or cloud provider (lower trust, since the provider already saw the prompt)

---

## 3. Violation Types and Severity Levels

### 3.1 Violation Types

| Violation type | ID | Description |
|---------------|-----|-------------|
| **PII leakage** | `pii_leakage` | The LLM response contains PII that was not in the original prompt. The LLM hallucinated or inferred personal data. |
| **Classification escalation** | `classification_escalation` | The response contains data at a higher classification level than the conversation's established level. |
| **Regulatory entity** | `regulatory_entity` | The response contains an entity type that the active regulatory preset specifically flags (e.g., Art. 9 special category data under EU GDPR). |
| **Policy rule match** | `policy_rule_match` | The response matches a custom policy rule (e.g., enterprise-defined patterns like internal project codes, customer identifiers). |
| **Cross-border inference** | `cross_border_inference` | The response references data subjects in a jurisdiction whose regulatory preset would prohibit this type of processing (e.g., a response about an EU resident's health data when the conversation was classified as low-sensitivity). |
| **Restoration anomaly** | `restoration_anomaly` | The post-restoration differential scan found a new violation created by combining restored PII with LLM-generated context. |

### 3.2 Severity Levels

Violations are assigned one of four severity levels, aligned with the graduated response model established in the policy format spec (A3.1):

| Severity | ID | Default action | Description |
|----------|-----|---------------|-------------|
| **Info** | `info` | Log only | Low-confidence detection or minor policy note. No user interruption. Recorded in audit trail. |
| **Advisory** | `advisory` | Inline indicator | Medium-confidence detection. A subtle visual indicator is shown but the response is not blocked. User can inspect details. |
| **Warning** | `warning` | Warning banner | High-confidence detection of a genuine policy violation. A prominent warning is shown. Response is displayed but flagged. |
| **Block** | `block` | Require confirmation | High-confidence detection of a serious violation. Response is hidden until the user explicitly acknowledges and chooses to reveal it. Enterprise policies can make blocks non-overridable. |

### 3.3 Severity Assignment

Severity is determined by a matrix of violation type, detection confidence, and data classification level:

| | Confidence >= 0.95 | Confidence 0.85-0.94 | Confidence 0.80-0.84 |
|---|---|---|---|
| **RESTRICTED / PROHIBITED** | Block | Warning | Advisory |
| **CONFIDENTIAL** | Warning | Advisory | Info |
| **INTERNAL** | Advisory | Info | Info |
| **PUBLIC** | Info | Info | — (not flagged) |

Enterprise policies can override this matrix entirely (see Section 8).

---

## 4. Warning UI

### 4.1 Browser Mode (Electron/Chromium)

#### 4.1.1 Info Severity

- **No visible interruption.** The response displays normally.
- A small counter badge on the pipeline visibility panel increments (e.g., "3 info" in muted text).
- Clicking the badge opens the violation details panel.

#### 4.1.2 Advisory Severity

- **Inline annotation.** The flagged span of text is given a subtle underline (dotted, amber colour `#f59e0b`).
- Hovering over the underline shows a tooltip: entity type, confidence, and the relevant policy rule.
- The pipeline visibility panel shows an amber indicator.
- The response is fully visible and interactive.

#### 4.1.3 Warning Severity

- **Warning banner.** A persistent banner appears above the response:
  - Amber background (`#f59e0b` at 10% opacity, amber border).
  - Icon: warning triangle.
  - Text: concise description of the violation (e.g., "This response contains a detected medical record reference (confidence: 92%). Your policy classifies medical records as RESTRICTED.").
  - Actions: **Dismiss** (hides banner, logs acknowledgement), **Details** (expands to show all detections), **Report false positive** (logs feedback for model tuning).
- The flagged text spans are highlighted with an amber background.
- The response is fully visible.

#### 4.1.4 Block Severity

- **Response hidden.** The response area shows a blocking overlay:
  - Red background (`#ef4444` at 10% opacity, red border).
  - Icon: shield with exclamation mark.
  - Text: description of the violation and why the response is blocked.
  - Actions: **Reveal and acknowledge** (shows response, logs explicit user confirmation), **Discard** (deletes the response from the conversation), **Details** (shows all detections without revealing the response text).
- If the enterprise policy sets `allow_user_override: false` for this severity, the **Reveal and acknowledge** button is replaced with "Blocked by enterprise policy" (non-interactive). The response is permanently hidden and can only be viewed in the audit log by an administrator.

#### 4.1.5 Transparency Bar Integration

The transparency bar (A1.3) always shows the current compliance status:

- Green: no violations in the current response.
- Amber: advisory or warning violations present.
- Red: block-level violations present.

Clicking the compliance indicator opens the full violation details panel.

### 4.2 Terminal Mode (CLI)

#### 4.2.1 Info Severity

- No visible output. Logged to the audit trail only.
- Visible in `--verbose` mode as a dim line: `[info] Response scan: 1 detection (person_name, confidence 0.82, level INTERNAL)`.

#### 4.2.2 Advisory Severity

- A single line printed after the response, in dim/grey text:
  ```
  ℹ Advisory: 1 detection in response (person_name, confidence 0.88). Run `loke scan --details` for more.
  ```
- The response is printed in full, unmodified.

#### 4.2.3 Warning Severity

- A bordered warning block printed immediately before the response:
  ```
  ┌─ ⚠ Compliance Warning ─────────────────────────────────────────┐
  │ This response contains detected PII: medical_record             │
  │ (confidence: 0.93). Policy classifies medical records as        │
  │ RESTRICTED.                                                     │
  │                                                                 │
  │ Press Enter to continue, or 'd' to discard.                     │
  └─────────────────────────────────────────────────────────────────┘
  ```
- In non-interactive mode (piped output, `--no-interactive`), the warning is printed to stderr and the response is printed to stdout without pausing. The exit code is set to 2 (warning).

#### 4.2.4 Block Severity

- The response is withheld. A bordered block is printed:
  ```
  ┌─ ✖ Compliance Block ───────────────────────────────────────────┐
  │ Response blocked: detected medical_record (confidence: 0.96)    │
  │ combined with person_name. Policy classifies this combination   │
  │ as RESTRICTED — confirmation required.                          │
  │                                                                 │
  │ Press 'y' to reveal, 'd' to discard, or '?' for details.       │
  └─────────────────────────────────────────────────────────────────┘
  ```
- The user must press `y` to reveal the response. Pressing `d` discards it.
- In non-interactive mode, the response is suppressed entirely. A JSON violation report is printed to stderr. Exit code is 3 (blocked).
- Enterprise hard blocks (`allow_user_override: false`) print "Blocked by enterprise policy" and suppress the response unconditionally. Exit code 4.

### 4.3 Proxy Mode Considerations

When loke operates as a coding LLM proxy (`loke proxy claude-code`), warning and block UI must integrate with the proxied tool's expectations:

- **Warning severity:** The response is passed through to the proxied tool with an `X-Loke-Compliance-Warning` HTTP header containing a JSON summary of violations. The proxied tool can choose to display this or ignore it. The violation is logged regardless.
- **Block severity:** The response is withheld. loke returns an HTTP 451 (Unavailable For Legal Reasons) status to the proxied tool, with a JSON body describing the violation. The proxied tool receives no response content until the user acknowledges via loke's terminal UI or the loke dashboard.
- **Non-interactive proxy mode:** If `--no-interactive` is set, block-severity violations cause the proxy to return HTTP 451 with full violation details. The proxied tool must handle this gracefully. This is documented in the proxy mode integration guide.

---

## 5. Require-Confirmation Mode

### 5.1 Overview

Require-confirmation mode forces the user to explicitly acknowledge every response before it is displayed, regardless of whether violations were found. This is separate from block-severity violation handling (which is triggered by specific detections). Require-confirmation mode is a blanket safeguard for high-risk contexts.

### 5.2 When It Activates

Require-confirmation mode activates when any of the following conditions are met:

1. **Policy setting:** `compliance.require_confirmation_mode: always` is set in the active policy.
2. **Classification threshold:** The conversation's sensitivity classification meets or exceeds the level specified by `compliance.require_confirmation_above`.
3. **Provider trigger:** The response came from a provider listed in `compliance.require_confirmation_providers`.
4. **Regulatory trigger:** The active regulatory preset mandates confirmation for certain processing types (e.g., HIPAA preset requires confirmation for responses in conversations that contained PHI).

### 5.3 Behaviour

When require-confirmation mode is active:

- **Browser mode:** Every response is initially collapsed behind a "Review before displaying" panel. The panel shows a summary: provider name, token count, number of compliance detections (if any), and classification level. The user clicks **Display response** to reveal it. This is logged as an explicit acknowledgement.
- **Terminal mode:** Every response is preceded by a confirmation prompt. The summary line shows provider, tokens, and detection count. The user presses Enter to display.
- **Proxy mode:** Every response is held. The proxy returns HTTP 202 (Accepted) with a `X-Loke-Confirmation-Required: true` header. The response is released only after the user confirms via loke's UI.

### 5.4 Bypass for Local Models

When `compliance.require_confirmation_local_bypass: true` (the default), responses from local models (Ollama, MLX, @electron/llm) skip require-confirmation mode. The rationale is that local model responses never left the device and therefore pose no cross-boundary compliance risk.

Enterprise policies can set this to `false` to enforce confirmation even for local responses.

---

## 6. Suppression Rules

### 6.1 "Don't Warn Again"

When a user dismisses a warning or acknowledges a block, they may choose **Don't warn again for this type**. This creates a suppression rule.

### 6.2 Suppression Rule Structure

```yaml
# Stored in user preferences, not in policy files
suppression_rules:
  - id: "sup_20260405_001"
    created: "2026-04-05T10:30:00Z"
    violation_type: "pii_leakage"           # Which violation type to suppress
    entity_type: "person_name"              # Specific entity type (optional — omit to suppress all entities of this violation type)
    scope: "conversation"                   # conversation | session | permanent
    max_confidence: 0.90                    # Only suppress detections at or below this confidence
    expires: "2026-04-12T10:30:00Z"         # Auto-expiry (null for permanent until revoked)
```

### 6.3 Scope

| Scope | Duration | Description |
|-------|----------|-------------|
| `conversation` | Current conversation only | Suppression expires when the conversation is closed or a new conversation starts. |
| `session` | Current application session | Suppression expires when loke is restarted. |
| `permanent` | Until manually revoked | Suppression persists across sessions. Stored in user preferences. |

### 6.4 Constraints

- **Enterprise floor.** Enterprise policies can set `compliance.min_severity_for_suppression` to prevent users from suppressing violations at or above a given severity. The default is `block` — users can suppress info, advisory, and warning, but not block-level violations (unless the enterprise explicitly permits it).
- **Suppression audit.** Every suppression rule creation is logged in the audit trail, including the user's identity (if known), the violation details, and the chosen scope.
- **Suppression review.** Users can view and revoke their active suppression rules via the settings panel (browser mode) or `loke compliance suppressions list` (terminal mode).
- **Maximum suppression count.** A safety limit of 100 active permanent suppression rules prevents runaway suppression. Beyond this limit, the oldest rule is evicted. This limit is configurable via `compliance.max_permanent_suppressions`.

### 6.5 Suppression Does Not Affect Audit Logging

Suppressed violations are still logged in the audit trail. Suppression only affects the UI — it prevents the warning from being shown to the user. The audit record includes a `suppressed: true` flag and a reference to the suppression rule ID.

---

## 7. Audit Trail Integration

### 7.1 Violation Audit Record

Every detected violation (regardless of severity, including suppressed violations) produces an audit record. The record conforms to the audit trail schema defined in F6.2.

```yaml
# Example audit record for a compliance violation
audit_entry:
  id: "aud_20260405_143022_a7b3"
  timestamp: "2026-04-05T14:30:22.417Z"
  type: "compliance_violation"
  interaction_id: "int_20260405_142955_f1e2"
  session_id: "ses_20260405_140000_d4c5"

  violation:
    type: "pii_leakage"
    entity_type: "medical_record"
    confidence: 0.93
    severity: "warning"
    classification_level: "restricted"
    scan_phase: "pre_restoration"          # pre_restoration | post_restoration_differential

  context:
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
    conversation_classification: "confidential"
    token_position:                        # Approximate position, not actual content
      start_offset: 1247
      end_offset: 1302

  action:
    displayed: true                        # Was the response shown to the user?
    user_acknowledged: true                # Did the user explicitly acknowledge?
    suppressed: false                      # Was the warning suppressed by a rule?
    suppression_rule_id: null
    user_action: "dismiss"                 # dismiss | reveal | discard | auto (for info)
    action_timestamp: "2026-04-05T14:30:28.103Z"

  # PII values are NEVER logged — only entity types and metadata
```

### 7.2 What Is Never Logged

Consistent with loke's core constraint that PII must never appear in logs:

- The actual detected text is not logged. Only the entity type, confidence score, and approximate character offset are recorded.
- The response content is not logged. Only metadata (token count, provider, model) is recorded.
- Suppression rules reference violation types and entity types, never specific values.

### 7.3 Audit Aggregation

The audit system maintains running aggregates for the compliance dashboard:

| Metric | Granularity | Retention |
|--------|-------------|-----------|
| Violations by type | Hourly, daily, weekly, monthly | Per audit retention policy |
| Violations by severity | Hourly, daily, weekly, monthly | Per audit retention policy |
| Violations by provider | Daily, weekly, monthly | Per audit retention policy |
| Suppression rule usage | Daily | Per audit retention policy |
| User acknowledgement rate | Weekly, monthly | Per audit retention policy |
| False positive reports | Weekly, monthly | Per audit retention policy |

These aggregates feed into the audit reporting and export system (A3.4).

### 7.4 SIEM Forwarding

When SIEM forwarding is enabled (F6.2), compliance violations at warning and block severity are forwarded in real time. Info and advisory violations are forwarded only in batch (hourly digest) to avoid overwhelming the SIEM with low-severity events. Enterprise policies can override this to forward all severities in real time.

---

## 8. Configuration

### 8.1 Policy Schema: `compliance` Section

The `compliance` section is a new top-level section in the policy document schema (extending the schema defined in A3.1).

```yaml
compliance:
  # Response scanning configuration
  response_scanning:
    enabled: true                          # Cannot be set to false at user level if enterprise sets true
    confidence_threshold: 0.80             # Minimum confidence for a detection to be considered (0.0-1.0)
    detection_layers: [regex, nlp, slm, presidio]  # Which layers to use for response scanning
    scan_restored: true                    # Whether to run the post-restoration differential scan
    max_scan_time_ms: 2000                 # Maximum time for response scanning before falling back to partial results

  # Severity matrix overrides
  severity_matrix:
    # Override the default severity for specific combinations
    overrides:
      - entity_type: "person_name"
        classification: "internal"
        min_confidence: 0.80
        severity: "info"                   # Downgrade person_name at INTERNAL to info (common in business responses)

      - entity_type: "medical_record"
        classification: "*"                # Any classification
        min_confidence: 0.80
        severity: "block"                  # Always block medical records regardless of classification

      - violation_type: "restoration_anomaly"
        classification: "*"
        min_confidence: 0.80
        severity: "warning"                # Restoration anomalies are always at least a warning

  # Require-confirmation mode
  require_confirmation:
    mode: "on_violation"                   # never | on_violation | above_classification | always
    above_classification: "restricted"     # Used when mode is "above_classification"
    providers: []                          # Provider IDs that always trigger confirmation
    local_bypass: true                     # Skip confirmation for local model responses
    regulatory_triggers: true              # Allow regulatory presets to activate confirmation

  # Suppression controls
  suppression:
    allowed: true                          # Whether users can create suppression rules
    min_severity_for_suppression: "block"  # Users cannot suppress violations at this severity or above
    max_permanent_suppressions: 100        # Safety limit on permanent rules
    allow_permanent: true                  # Whether permanent suppressions are permitted

  # Block behaviour
  blocking:
    allow_user_override: true              # Can users reveal blocked responses?
    enterprise_hard_block: false           # If true, block is absolute — no override possible
    discard_on_block: false                # If true, blocked responses are immediately discarded (not stored)

  # Audit integration
  audit:
    log_all_severities: true               # Log info and advisory as well as warning and block
    siem_realtime_min_severity: "warning"  # Minimum severity for real-time SIEM forwarding
    aggregate_metrics: true                # Maintain running aggregates for dashboard

  # UI behaviour
  ui:
    show_confidence: true                  # Show confidence scores in violation details
    show_entity_type: true                 # Show detected entity types in warnings
    show_policy_rule: true                 # Show which policy rule triggered the violation
    inline_annotations: true               # Show inline underlines for advisory severity (browser mode)
    warning_auto_dismiss_seconds: 0        # Auto-dismiss warnings after N seconds (0 = manual dismiss only)
```

### 8.2 Field Reference: `compliance`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `response_scanning.enabled` | boolean | No | `true` | Enable response scanning. Enterprise setting cannot be overridden at lower levels. |
| `response_scanning.confidence_threshold` | float | No | `0.80` | Minimum detection confidence to flag. Range: 0.50-1.00. |
| `response_scanning.detection_layers` | list | No | `[regex, nlp, slm, presidio]` | Detection layers to use. Must be a subset of available layers. |
| `response_scanning.scan_restored` | boolean | No | `true` | Run differential scan after placeholder restoration. |
| `response_scanning.max_scan_time_ms` | integer | No | `2000` | Timeout for response scanning. On timeout, partial results are used and a `scan_timeout` event is logged. |
| `severity_matrix.overrides` | list | No | `[]` | Override default severity assignments. Each entry must specify at least `entity_type` or `violation_type`. |
| `require_confirmation.mode` | enum | No | `"on_violation"` | When to require confirmation. `never`: disabled. `on_violation`: only when block-level violations are detected. `above_classification`: when conversation exceeds the specified level. `always`: every response. |
| `require_confirmation.above_classification` | string | No | `"restricted"` | Classification threshold for `above_classification` mode. |
| `require_confirmation.providers` | list | No | `[]` | Provider IDs that always require confirmation. |
| `require_confirmation.local_bypass` | boolean | No | `true` | Skip confirmation for local model responses. |
| `require_confirmation.regulatory_triggers` | boolean | No | `true` | Allow active regulatory presets to trigger confirmation. |
| `suppression.allowed` | boolean | No | `true` | Whether suppression rules can be created. Enterprise can set to `false` to prevent all suppression. |
| `suppression.min_severity_for_suppression` | enum | No | `"block"` | Lowest severity that cannot be suppressed. |
| `suppression.max_permanent_suppressions` | integer | No | `100` | Maximum permanent suppression rules. Range: 1-1000. |
| `suppression.allow_permanent` | boolean | No | `true` | Whether permanent-scope suppressions are permitted. |
| `blocking.allow_user_override` | boolean | No | `true` | Whether users can reveal blocked responses. |
| `blocking.enterprise_hard_block` | boolean | No | `false` | Absolute block with no override. Only settable at enterprise level. |
| `blocking.discard_on_block` | boolean | No | `false` | Immediately discard blocked responses rather than holding them. |
| `audit.log_all_severities` | boolean | No | `true` | Log all severity levels. If `false`, only warning and block are logged. |
| `audit.siem_realtime_min_severity` | enum | No | `"warning"` | Minimum severity for real-time SIEM forwarding. |
| `audit.aggregate_metrics` | boolean | No | `true` | Maintain running aggregate metrics. |
| `ui.show_confidence` | boolean | No | `true` | Show confidence scores in violation UI. |
| `ui.show_entity_type` | boolean | No | `true` | Show entity types in violation UI. |
| `ui.show_policy_rule` | boolean | No | `true` | Show triggering policy rule in violation UI. |
| `ui.inline_annotations` | boolean | No | `true` | Show inline annotations for advisory severity in browser mode. |
| `ui.warning_auto_dismiss_seconds` | integer | No | `0` | Auto-dismiss warnings after N seconds. 0 = manual only. Enterprise can set a minimum. |

### 8.3 Merge Rules

The `compliance` section follows the same merge semantics defined in the policy format spec (A3.1):

- **Enterprise wins.** Enterprise-level settings for `response_scanning.enabled`, `blocking.enterprise_hard_block`, `suppression.allowed`, and `suppression.min_severity_for_suppression` cannot be overridden at team or user level.
- **Most restrictive wins for security-relevant fields.** `confidence_threshold`: lower value wins (more sensitive). `min_severity_for_suppression`: higher severity wins (less suppressible). `allow_user_override`: `false` wins over `true`.
- **User wins for UI preferences.** Fields under `ui.*` are user-level preferences unless the enterprise explicitly locks them.
- **Additive for overrides.** `severity_matrix.overrides` from all policy layers are merged. If two overrides match the same entity/violation type, the one from the higher-precedence policy layer wins.

---

## 9. Edge Cases

### 9.1 Streaming Responses

LLM responses are often streamed token-by-token. The compliance feedback loop handles streaming as follows:

- **Buffered scanning.** Tokens are accumulated in a buffer. The scanner runs periodically (every 500ms or every 50 tokens, whichever comes first) against the accumulated buffer. This provides near-real-time detection without scanning every individual token.
- **Progressive display.** In the default mode, streamed tokens are displayed as they arrive. If a scan of the accumulated buffer detects a violation:
  - **Advisory/Warning:** An inline annotation or warning banner is inserted at the next natural break (sentence or paragraph boundary). Already-displayed text is retroactively annotated in browser mode (DOM update) or noted in terminal mode (post-hoc warning line).
  - **Block:** Streaming is immediately paused. Already-displayed content remains visible (it has already been seen). The blocking overlay is shown for the remainder of the response. The user can choose to continue streaming or discard the remainder.
- **Require-confirmation mode with streaming.** When require-confirmation mode is active, streaming is buffered entirely — the user sees a progress indicator ("Receiving response... 847 tokens") but no content until the full response has been scanned and the user confirms.
- **Configuration:** `compliance.streaming.mode` can be set to `progressive` (default — display as tokens arrive, retrofit warnings) or `buffered` (hold all content until scan completes). Enterprise policies may mandate `buffered` for high-sensitivity contexts.

```yaml
compliance:
  streaming:
    mode: "progressive"                    # progressive | buffered
    scan_interval_ms: 500                  # Minimum interval between buffer scans
    scan_interval_tokens: 50               # Minimum token count between buffer scans
    pause_on_block: true                   # Pause streaming when a block-level violation is detected
```

### 9.2 Partial Matches

A detection may span a chunk boundary (e.g., a phone number split across two streaming chunks, or a name split across a sentence boundary in a complete response).

- **Cross-chunk detection.** The scanner maintains a sliding context window that overlaps chunks by 100 characters in each direction. This ensures entities spanning boundaries are detected.
- **Low-confidence partials.** If a partial match has confidence below the threshold, it is recorded as a `pending_partial` and re-evaluated when more context arrives. If the response ends and the partial is still below threshold, it is logged at info severity and discarded.

### 9.3 MCP Tool Output

MCP tool outputs are scanned with the same pipeline, with these additional considerations:

- **Tool identity.** The MCP server and tool name are recorded in the audit trail alongside any violation.
- **Structured output.** MCP tools may return structured data (JSON, tables). The scanner processes both the string representation and individual field values. Field names are not scanned (they are schema, not data).
- **Binary output.** Binary content (images, files) returned by MCP tools is not scanned by the text pipeline. A future extension (out of scope for this story) may add image-based PII detection.
- **MCP resource subscriptions.** Resources fetched via MCP subscriptions are scanned on each update. If a subscription update triggers a block, the subscription is paused and the user is notified.

### 9.4 Batched / Multi-Turn Responses

When loke processes a batch of responses (e.g., parallel tool calls returning simultaneously), each response is scanned independently. However, the aggregate violation count across the batch is considered for severity escalation — if three responses in a batch each have an advisory-level detection, the batch as a whole is escalated to warning severity.

### 9.5 Empty or Refused Responses

- **Empty responses.** No scan is performed. An empty response is not a compliance violation.
- **LLM refusal responses.** Responses where the LLM refuses to answer (detected via common refusal patterns) are not scanned for PII. They are logged as `llm_refusal` events in the audit trail.

### 9.6 Scanner Failure

If the response scanner fails (timeout, crash, out-of-memory):

- **Fail safe, not fail open.** The response is held until the scanner recovers or the user is informed.
- If the scanner times out (exceeds `max_scan_time_ms`), partial results are used. A `scan_timeout` event is logged. If no partial results are available, the response is treated as if it has a warning-level violation, and the user is shown: "Response scan incomplete — review manually."
- The scanner failure rate is tracked. If failures exceed 5% of responses in a rolling 1-hour window, a persistent warning is shown suggesting the user check system resources or reduce detection layers.

---

## 10. Performance Considerations

### 10.1 Latency Budget

Response scanning must not add perceptible delay to the user experience:

| Mode | Target latency | Maximum latency |
|------|---------------|-----------------|
| Streaming (progressive) | < 50ms per buffer scan | 200ms |
| Complete response (< 4K tokens) | < 200ms total | 500ms |
| Complete response (4K-16K tokens) | < 500ms total | 2000ms |
| Complete response (> 16K tokens) | < 2000ms total | `max_scan_time_ms` |

### 10.2 Layer Skipping

To meet latency targets, the scanner uses progressive layer activation:

1. **Regex** always runs (< 5ms for typical responses).
2. **NLP/compromise.js** always runs (< 50ms for typical responses).
3. **SLM NER** runs only if regex or NLP produced detections, or if the conversation classification is CONFIDENTIAL or above.
4. **Presidio** runs only if the active regulatory preset requires it, or if the conversation classification is RESTRICTED or above.

This ensures fast responses for low-sensitivity conversations while maintaining thorough scanning for high-sensitivity contexts.

### 10.3 Caching

Detection results for identical text spans are cached for the duration of the conversation. If a repeated phrase appears multiple times in a response, it is scanned once. The cache is keyed on the text span hash and the active policy version.

---

## 11. Complete Configuration Example

A full policy example showing the compliance feedback loop configured for a healthcare organisation under HIPAA:

```yaml
policy_version: "1.0"
metadata:
  name: "HealthCo HIPAA Compliance Policy"
  id: "healthco-hipaa-2026q2"
  regulation_basis:
    - "hipaa"

compliance:
  response_scanning:
    enabled: true
    confidence_threshold: 0.75             # Lower threshold for healthcare — more cautious
    detection_layers: [regex, nlp, slm, presidio]
    scan_restored: true
    max_scan_time_ms: 3000                 # Allow more time for Presidio

  severity_matrix:
    overrides:
      - entity_type: "medical_record"
        classification: "*"
        min_confidence: 0.75
        severity: "block"

      - entity_type: "diagnosis_code"
        classification: "*"
        min_confidence: 0.80
        severity: "block"

      - entity_type: "person_name"
        classification: "restricted"
        min_confidence: 0.85
        severity: "warning"

      - entity_type: "medication_name"
        classification: "*"
        min_confidence: 0.80
        severity: "warning"

  require_confirmation:
    mode: "above_classification"
    above_classification: "confidential"   # Confirm for CONFIDENTIAL and above
    providers: ["openai", "google"]        # Always confirm for cloud providers
    local_bypass: false                    # Even local models need confirmation in healthcare
    regulatory_triggers: true

  suppression:
    allowed: true
    min_severity_for_suppression: "warning" # Cannot suppress warnings or blocks
    max_permanent_suppressions: 50
    allow_permanent: false                  # Only conversation and session scope

  blocking:
    allow_user_override: true
    enterprise_hard_block: false
    discard_on_block: false

  streaming:
    mode: "buffered"                       # Full buffer before display in healthcare context
    pause_on_block: true

  audit:
    log_all_severities: true
    siem_realtime_min_severity: "advisory" # Forward advisory and above in real time
    aggregate_metrics: true

  ui:
    show_confidence: true
    show_entity_type: true
    show_policy_rule: true
    inline_annotations: true
    warning_auto_dismiss_seconds: 0        # No auto-dismiss
```

---

## Appendix A: Violation Type Reference

| Violation type ID | Trigger condition | Default severity range | Suppression default |
|-------------------|------------------|----------------------|-------------------|
| `pii_leakage` | PII detected in response that was not in the prompt | Advisory - Block | Suppressible at advisory and warning |
| `classification_escalation` | Response classification exceeds conversation classification | Warning - Block | Suppressible at warning |
| `regulatory_entity` | Entity type flagged by active regulatory preset | Warning - Block | Not suppressible by default |
| `policy_rule_match` | Custom policy pattern matched in response | Info - Block (configurable) | Suppressible at info and advisory |
| `cross_border_inference` | Response references data subjects in a restricted jurisdiction | Advisory - Warning | Suppressible at advisory |
| `restoration_anomaly` | Post-restoration scan found new violation from PII + context combination | Warning - Block | Not suppressible by default |

---

## Appendix B: Terminal Exit Codes

| Exit code | Meaning |
|-----------|---------|
| 0 | No compliance violations |
| 2 | Warning-level violations present (response displayed) |
| 3 | Block-level violation (response withheld until confirmed, or suppressed in non-interactive mode) |
| 4 | Enterprise hard block (response permanently withheld) |

---

## Appendix C: HTTP Headers for Proxy Mode

| Header | Direction | Description |
|--------|-----------|-------------|
| `X-Loke-Compliance-Warning` | Response | JSON array of warning-level violations. Present only when violations exist. |
| `X-Loke-Compliance-Block` | Response | JSON object describing the block-level violation. Accompanies HTTP 451 status. |
| `X-Loke-Confirmation-Required` | Response | `true` when require-confirmation mode is active. Accompanies HTTP 202 status. |
| `X-Loke-Scan-Status` | Response | `complete`, `partial` (timeout), or `skipped`. Always present. |
