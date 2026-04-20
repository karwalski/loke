# Audit Reporting and Export Specification

**Story:** A3.4 — Audit reporting and export
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke maintains an append-only, hash-chained audit trail (F6.2) that records every significant event in the privacy pipeline: PII detections, anonymisation actions, routing decisions, policy evaluations, token usage, and user overrides. This specification defines how that audit data is surfaced to users and administrators through structured reports that can be generated on demand, scheduled for recurring delivery, and exported in multiple formats.

This specification defines:

- Report types and their contents
- Export formats (PDF, CSV, JSON) with schema definitions
- Time range selection and filtering
- Report templates (built-in and custom, parameterised)
- Scheduled and automated report generation
- Data redaction rules for exported reports
- SIEM integration (syslog, webhook, CEF/LEEF)
- CLI commands for report management
- Browser mode UI for report building and preview
- Tamper evidence in exported reports

### 1.1 Design Alignment

This specification follows the loke design principles:

- **The user is the authority.** Users control what is reported, when, and to whom. Enterprise policies can mandate minimum reporting but cannot silently exfiltrate data.
- **Privacy is the foundation.** Reports must not leak PII. Exported reports redact all personal data by default; opting in to PII inclusion requires explicit action and is logged in the audit trail.
- **Warnings must be earned.** Report summaries surface genuine compliance risks, not noise. A clean report should be visually distinct from one with violations.
- **Do the right thing by default.** Built-in templates cover the most common regulatory reporting needs without configuration.

### 1.2 Dependencies

| Dependency | Story | Description |
|------------|-------|-------------|
| Audit trail system | F6.2 | Append-only hash-chained event store that this spec reads from |
| Policy format | A3.1 | Policy definitions referenced in compliance reports |
| Regulatory defaults | A3.2 | Preset retention periods and audit requirements per regulation |
| SQLite storage | F6.1 | SQLCipher-encrypted database where audit events are stored |

---

## 2. Report Types

loke supports five built-in report types. Each report type queries the audit trail and presents a focused view of system activity.

### 2.1 Compliance Summary

A high-level overview of policy adherence over a time period. Designed for regulators, auditors, and compliance officers.

**Contents:**

| Section | Description |
|---------|-------------|
| Policy overview | Active policies (enterprise, team, user) with IDs and versions |
| Regulation basis | Which regulatory presets were active and when |
| Violation summary | Count and severity breakdown of policy violations |
| Anonymisation coverage | Percentage of outbound requests with full anonymisation |
| Data classification distribution | Breakdown of data by sensitivity level (PUBLIC through RESTRICTED) |
| Provider compliance | Which providers were used, whether DPA/BAA requirements were met |
| Cross-border transfer log | Summary of data destinations by jurisdiction |
| Retention compliance | Whether PII mappings and cache entries were purged on schedule |
| Hash chain integrity | Whether the audit trail passed tamper verification |

### 2.2 PII Detection Log

A detailed record of every PII detection event. Designed for privacy engineers and DPOs.

**Contents:**

| Section | Description |
|---------|-------------|
| Detection summary | Total detections by entity type, detection layer, and sensitivity level |
| Detection timeline | Time-series chart of detection frequency |
| Layer effectiveness | Breakdown of which detection layer (regex, NLP, SLM NER, Presidio) caught each entity |
| False positive rate | Detections that were overridden by the user, grouped by entity type |
| Entity type distribution | Heatmap of entity types across sessions |
| Anonymisation actions | What action was taken for each detection (placeholder, redact, block, user override) |

**Note:** PII values are never included in this report. Only entity types, counts, and metadata are recorded.

### 2.3 Routing Decisions

A record of how requests were routed across providers. Designed for cost optimisation and architecture review.

**Contents:**

| Section | Description |
|---------|-------------|
| Routing summary | Total requests by provider, model, and routing strategy |
| Decision rationale | Why each routing decision was made (cheapest-adequate, fastest, local-first, sensitivity constraint) |
| Fallback events | Cases where the primary provider was unavailable and a fallback was used |
| Local vs cloud ratio | Percentage of requests handled locally vs sent to cloud providers |
| Latency distribution | Response times by provider and model |
| Sensitivity routing | How data classification affected routing (e.g. RESTRICTED data kept local) |

### 2.4 Cost and Token Usage

Financial and token consumption reporting. Designed for budget management and optimisation.

**Contents:**

| Section | Description |
|---------|-------------|
| Total spend | Aggregated cost by provider, model, and time period |
| Token consumption | Input and output tokens by provider and model |
| Savings from optimisation | Tokens saved by compression (LLMLingua), caching (semantic cache), and TOON serialisation |
| Savings from local routing | Estimated cost avoided by routing to local models |
| Budget utilisation | Current spend against configured budget limits (daily, weekly, monthly) |
| Cost trend | Time-series of daily/weekly spend with projection |
| Per-session breakdown | Cost attributed to individual sessions (optional, can be disabled) |

### 2.5 Policy Violations

A focused report on every event where a policy rule was triggered. Designed for security teams and incident review.

**Contents:**

| Section | Description |
|---------|-------------|
| Violation summary | Count by severity (info, advisory, warning, block) and policy rule |
| Violation timeline | Time-series of violations |
| Top violated rules | Most frequently triggered policy rules |
| User overrides | Cases where the user overrode a warning (with confirmation timestamp) |
| Blocked requests | Requests that were hard-blocked by enterprise policy |
| Resolution status | Whether violations were acknowledged, investigated, or resolved |

---

## 3. Export Formats

All report types can be exported in three formats. The format determines structure, not content — the same underlying data is presented in each.

### 3.1 JSON

The canonical machine-readable format. All other formats are derived from the JSON representation.

**Structure:**

```json
{
  "report": {
    "id": "rpt_20260405T143022Z_a7b3c1d2",
    "type": "compliance_summary",
    "version": "1.0",
    "generated_at": "2026-04-05T14:30:22Z",
    "generated_by": "loke v0.8.0",
    "time_range": {
      "start": "2026-03-01T00:00:00Z",
      "end": "2026-03-31T23:59:59Z"
    },
    "filters": {
      "sensitivity_levels": ["confidential", "restricted"],
      "providers": ["anthropic", "openai"],
      "policies": ["acme-enterprise-2026q1"]
    },
    "template": "compliance-summary-default",
    "pii_redacted": true,
    "checksum": {
      "algorithm": "sha256",
      "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "hash_chain_verification": {
      "verified": true,
      "chain_start": "evt_20260301T000000Z_0001",
      "chain_end": "evt_20260331T235959Z_4821",
      "events_verified": 4821,
      "breaks_detected": 0
    }
  },
  "data": {
    "policy_overview": { ... },
    "violation_summary": { ... },
    "anonymisation_coverage": { ... },
    ...
  }
}
```

**Field Reference: `report` envelope**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique report identifier. Format: `rpt_{ISO8601}_{random8hex}`. |
| `type` | string | Report type: `compliance_summary`, `pii_detection_log`, `routing_decisions`, `cost_token_usage`, `policy_violations`. |
| `version` | string | Report schema version (semver). |
| `generated_at` | string (ISO 8601) | Timestamp of report generation. |
| `generated_by` | string | loke version that generated the report. |
| `time_range.start` | string (ISO 8601) | Start of the reporting period (inclusive). |
| `time_range.end` | string (ISO 8601) | End of the reporting period (inclusive). |
| `filters` | object | Active filters applied to the report. All fields optional. |
| `template` | string | Template ID used to generate this report. |
| `pii_redacted` | boolean | Whether PII was redacted from this report (default: `true`). |
| `checksum.algorithm` | string | Hash algorithm used for the report checksum. Always `sha256`. |
| `checksum.value` | string | SHA-256 hash of the `data` section (serialised as canonical JSON). |
| `hash_chain_verification` | object | Result of verifying the audit trail hash chain over the report's time range. |

### 3.2 CSV

Tabular export for spreadsheet analysis. Each report type produces one or more CSV files (one per data section). When multiple sections are exported, they are bundled in a ZIP archive.

**Naming convention:** `{report_id}_{section_name}.csv`

**Example** (PII detection log — detection summary section):

```csv
timestamp,session_id,entity_type,detection_layer,sensitivity_level,action_taken,was_overridden
2026-03-15T09:12:33Z,sess_a1b2c3,email_address,regex,restricted,placeholder,false
2026-03-15T09:12:33Z,sess_a1b2c3,person_name,nlp_ner,confidential,placeholder,false
2026-03-15T09:14:07Z,sess_a1b2c3,medical_record,slm_ner,restricted,redact,false
```

**CSV rules:**

- UTF-8 encoding with BOM for Excel compatibility
- RFC 4180 compliant (quoted fields, escaped quotes)
- Header row always present
- Timestamps in ISO 8601 (UTC)
- PII values never appear in any column; only entity types and metadata
- A `_metadata.json` sidecar file in the ZIP contains the report envelope (id, time range, filters, checksum)

### 3.3 PDF

Human-readable formatted report with charts, tables, and branding. Generated using a headless rendering pipeline.

**Structure:**

| Section | Contents |
|---------|----------|
| Cover page | Report title, type, time range, generation timestamp, loke version |
| Table of contents | Hyperlinked section list |
| Executive summary | Key metrics and findings in 3-5 bullet points |
| Detailed sections | Full report data with tables and charts |
| Hash chain verification | Verification result, chain boundaries, break count |
| Report integrity | SHA-256 checksum of the report data, verification instructions |
| Appendix | Filter criteria, template parameters, glossary |

**PDF generation:**

- Rendered via Playwright (Chromium headless) from an HTML template
- Charts rendered as inline SVG (no external dependencies)
- Page size: A4 (default) or US Letter (configurable)
- Supports custom enterprise branding (logo, colours) via template parameters

---

## 4. Time Range and Filtering

### 4.1 Time Range Selection

Reports require a time range. The following presets are available, plus custom ranges:

| Preset | Description |
|--------|-------------|
| `today` | Current calendar day (midnight to now, local time) |
| `yesterday` | Previous calendar day |
| `this_week` | Monday 00:00 to now (ISO week) |
| `last_week` | Previous ISO week (Monday to Sunday) |
| `this_month` | First of current month to now |
| `last_month` | Previous calendar month |
| `this_quarter` | First day of current quarter to now |
| `last_quarter` | Previous calendar quarter |
| `last_7d` | Rolling 7 days from now |
| `last_30d` | Rolling 30 days from now |
| `last_90d` | Rolling 90 days from now |
| `last_365d` | Rolling 365 days from now |
| `all` | Entire audit trail history |
| `custom` | Arbitrary start and end timestamps |

**Custom range example:**

```yaml
time_range:
  start: "2026-03-01T00:00:00+11:00"
  end: "2026-03-31T23:59:59+11:00"
```

All timestamps are stored internally as UTC. Display formatting respects the user's local timezone.

### 4.2 Filters

Filters narrow the report to a subset of audit events. All filters are optional and combinable (AND logic).

| Filter | Type | Description |
|--------|------|-------------|
| `sensitivity_levels` | list of string | Include only events involving these classification levels. Values: `public`, `internal`, `confidential`, `restricted`, `prohibited`. |
| `providers` | list of string | Include only events involving these LLM providers (e.g. `anthropic`, `openai`, `local`). |
| `models` | list of string | Include only events involving these models (e.g. `claude-sonnet-4-20250514`, `gpt-4o`). Supports glob patterns. |
| `sessions` | list of string | Include only events from these session IDs. |
| `policies` | list of string | Include only events evaluated against these policy IDs. |
| `entity_types` | list of string | Include only PII detection events for these entity types (e.g. `email_address`, `person_name`). |
| `detection_layers` | list of string | Include only detections from these layers: `regex`, `nlp`, `slm_ner`, `presidio`. |
| `violation_severity` | list of string | Include only violations at these severity levels: `info`, `advisory`, `warning`, `block`. |
| `actions` | list of string | Include only events with these outcomes: `placeholder`, `redact`, `block`, `allow`, `override`. |
| `min_cost` | number | Include only interactions costing at least this amount (in configured currency). |

**Filter example (CLI):**

```bash
loke report generate compliance-summary \
  --range last_month \
  --filter sensitivity_levels=confidential,restricted \
  --filter providers=anthropic,openai \
  --format json
```

**Filter example (YAML, for templates and schedules):**

```yaml
filters:
  sensitivity_levels: [confidential, restricted]
  providers: [anthropic, openai]
  violation_severity: [warning, block]
```

---

## 5. Report Templates

Templates define reusable, parameterised report configurations. loke ships with built-in templates and supports user-defined custom templates.

### 5.1 Built-in Templates

| Template ID | Report Type | Description |
|-------------|-------------|-------------|
| `compliance-summary-default` | compliance_summary | Full compliance overview with all sections |
| `compliance-summary-executive` | compliance_summary | Condensed executive summary (cover page + key metrics + violations only) |
| `pii-detection-full` | pii_detection_log | Complete PII detection log with all sections |
| `pii-detection-summary` | pii_detection_log | Detection counts and layer effectiveness only (no event-level detail) |
| `routing-overview` | routing_decisions | Routing decisions with provider and model breakdown |
| `cost-monthly` | cost_token_usage | Monthly cost report with budget utilisation and savings |
| `cost-daily` | cost_token_usage | Daily cost breakdown (designed for scheduled daily delivery) |
| `violations-full` | policy_violations | Complete violation log with user overrides |
| `violations-critical` | policy_violations | Only `warning` and `block` severity violations |
| `gdpr-article-30` | compliance_summary | Tailored for GDPR Article 30 records of processing activities |
| `hipaa-access-log` | pii_detection_log | Tailored for HIPAA access logging requirements |
| `au-privacy-act-app12` | compliance_summary | Tailored for Australian Privacy Act APP 12 access requests |

### 5.2 Custom Templates

Custom templates are YAML files stored in `~/.config/loke/report-templates/` (user) or distributed via enterprise policy.

**Template schema:**

```yaml
template_version: "1.0"
metadata:
  id: "acme-quarterly-compliance"
  name: "Acme Quarterly Compliance Report"
  description: "Quarterly compliance report for Acme Corp board presentation"
  author: "compliance@acme.com"
  created: "2026-03-01T00:00:00Z"

report_type: compliance_summary

# Default time range (can be overridden at generation time)
default_time_range: last_quarter

# Default filters (can be overridden at generation time)
default_filters:
  sensitivity_levels: [confidential, restricted]
  policies: ["acme-enterprise-2026q1"]

# Sections to include (omit sections to exclude them)
sections:
  - id: policy_overview
    enabled: true
  - id: violation_summary
    enabled: true
    options:
      include_resolved: false        # Only show open violations
  - id: anonymisation_coverage
    enabled: true
  - id: provider_compliance
    enabled: true
  - id: cross_border_transfers
    enabled: true
  - id: hash_chain_integrity
    enabled: true
  - id: data_classification_distribution
    enabled: false                   # Exclude from this template
  - id: retention_compliance
    enabled: true

# PDF-specific configuration
pdf:
  page_size: a4
  branding:
    logo_path: "~/.config/loke/branding/acme-logo.png"
    primary_colour: "#1e40af"
    footer_text: "Acme Corp — Confidential"
  cover_page:
    title: "Quarterly Privacy Compliance Report"
    subtitle: "{{ time_range.start | date('MMMM YYYY') }} to {{ time_range.end | date('MMMM YYYY') }}"

# Parameters (user-supplied values at generation time)
parameters:
  - id: department
    name: "Department"
    type: string
    required: false
    description: "Filter by department tag"
  - id: include_local
    name: "Include local model activity"
    type: boolean
    default: false
    description: "Whether to include local model interactions in the report"
```

### 5.3 Template Parameters

Templates can define parameters that are resolved at generation time. Parameters use Jinja2-style `{{ }}` interpolation in template text fields.

**Parameter types:**

| Type | Description | Example |
|------|-------------|---------|
| `string` | Free-text value | Department name |
| `boolean` | True/false toggle | Include local models |
| `number` | Numeric value | Minimum cost threshold |
| `date` | ISO 8601 date | Custom start date |
| `enum` | One of a predefined set | Severity level |
| `list` | List of values | Provider names |

### 5.4 Template Distribution

| Source | Location | Precedence |
|--------|----------|------------|
| Built-in | Bundled with loke | Lowest |
| Enterprise | Distributed via enterprise policy URL or MDM | Middle |
| User | `~/.config/loke/report-templates/*.yaml` | Highest (can override built-in IDs) |

Enterprise templates are fetched alongside enterprise policies (see A3.1 section 2.1) and cached locally.

---

## 6. Scheduled Report Generation

Reports can be scheduled for automatic generation and delivery at recurring intervals.

### 6.1 Schedule Configuration

Schedules are defined in YAML and stored in `~/.config/loke/report-schedules/` or managed via CLI.

```yaml
schedule_version: "1.0"
metadata:
  id: "weekly-compliance"
  name: "Weekly Compliance Summary"
  description: "Generated every Monday at 08:00 for the previous week"
  created: "2026-03-01T00:00:00Z"

template: "compliance-summary-default"
time_range: last_week

filters:
  sensitivity_levels: [confidential, restricted]

format: pdf

# Cron-style schedule (UTC)
cron: "0 8 * * 1"                    # Every Monday at 08:00 UTC

# Delivery targets (one or more)
delivery:
  - type: file
    path: "~/Documents/loke-reports/"
    filename_pattern: "compliance-{date}-{report_id}.pdf"

  - type: webhook
    url: "https://hooks.slack.com/services/T00/B00/xxxx"
    method: POST
    headers:
      Content-Type: "application/json"
    body_template: |
      {
        "text": "Weekly compliance report generated",
        "attachments": [{"title": "Report", "text": "{{ summary }}"}]
      }
    include_attachment: false          # Webhook receives summary only, not the full report

  - type: email
    to: ["compliance@acme.com"]
    subject: "loke Weekly Compliance Report — {{ time_range.start | date('D MMM') }} to {{ time_range.end | date('D MMM YYYY') }}"
    body: "Please find attached the weekly compliance summary."
    attach_report: true
    smtp:
      host: "smtp.acme.com"
      port: 587
      encryption: starttls
      username_env: "LOKE_SMTP_USER"
      password_env: "LOKE_SMTP_PASS"

# Retry on failure
retry:
  max_attempts: 3
  backoff: exponential               # exponential | fixed
  initial_delay: 60                  # seconds
```

### 6.2 Cron Syntax

Schedules use standard 5-field cron syntax (minute, hour, day-of-month, month, day-of-week). All times are UTC.

| Field | Values | Special characters |
|-------|--------|--------------------|
| Minute | 0-59 | `, - * /` |
| Hour | 0-23 | `, - * /` |
| Day of month | 1-31 | `, - * /` |
| Month | 1-12 | `, - * /` |
| Day of week | 0-6 (0 = Sunday) | `, - * /` |

**Common schedules:**

| Cron expression | Description |
|----------------|-------------|
| `0 8 * * 1` | Weekly, Monday 08:00 UTC |
| `0 6 1 * *` | Monthly, 1st at 06:00 UTC |
| `0 0 1 1,4,7,10 *` | Quarterly, 1st of Jan/Apr/Jul/Oct at midnight |
| `0 18 * * 5` | Weekly, Friday 18:00 UTC |
| `30 7 * * 1-5` | Weekdays at 07:30 UTC |

### 6.3 Delivery Methods

| Method | Description | Authentication |
|--------|-------------|----------------|
| `file` | Save to local filesystem | Filesystem permissions |
| `webhook` | HTTP POST to a URL | Custom headers (Bearer token, API key) |
| `email` | SMTP email with optional attachment | SMTP credentials via environment variables |
| `siem` | Forward to SIEM (see section 8) | Configured in SIEM integration settings |

### 6.4 Schedule Lifecycle

- **Created:** Schedule is defined but not yet active.
- **Active:** Schedule is running. loke checks for due schedules on startup and every 60 seconds while running.
- **Paused:** Schedule exists but will not trigger until resumed.
- **Failed:** Last execution failed. Schedule remains active; next execution will be attempted. After `max_attempts` consecutive failures, schedule is paused and a notification is emitted.
- **Deleted:** Schedule is removed. Previously generated reports are not affected.

**Note:** Scheduled reports require loke to be running. In terminal mode, a lightweight daemon (`loke daemon`) can run in the background to execute schedules. In browser mode, schedules run while the application is open.

---

## 7. Data Redaction in Reports

### 7.1 Default Behaviour

**All exported reports redact PII by default.** This is a non-negotiable default aligned with loke's core principle that privacy is the foundation. The audit trail stores metadata about PII events (entity type, detection layer, sensitivity level, action taken) but never stores PII values. Reports inherit this property.

**What is redacted:**

| Data | Redacted? | What appears instead |
|------|-----------|---------------------|
| PII values (names, emails, etc.) | Always (not stored in audit trail) | Entity type label (e.g. "email_address") |
| Session content (prompts, responses) | Always (not stored in audit trail) | Session ID and metadata only |
| Placeholder tokens ($c1, $l2) | Yes, by default | Entity type and count |
| Provider API keys | Always | Provider name only |
| User identifiers | Configurable | Anonymised user ID or full identifier |

### 7.2 PII Inclusion Opt-In

In specific circumstances (e.g. an internal investigation, or a data subject access request under GDPR Art. 15), a report may need to include PII. This requires explicit opt-in.

**Requirements for PII inclusion:**

1. The `--include-pii` flag must be passed explicitly (CLI) or the checkbox must be ticked (browser mode)
2. The active policy must permit PII inclusion in reports (`report_settings.allow_pii_export: true`). Enterprise policies can hard-block this.
3. The user must confirm via an interactive prompt: "This report will contain personal data. Ensure you have a lawful basis for this export. Continue? [y/N]"
4. The PII inclusion event is logged in the audit trail with the user's identity and stated purpose
5. The exported report is watermarked (PDF) or tagged (JSON/CSV) with a `contains_pii: true` flag

**Policy control:**

```yaml
# In policy file (A3.1 format)
report_settings:
  allow_pii_export: false            # Enterprise can hard-block
  pii_export_requires_reason: true   # User must state a reason (logged)
  pii_export_max_range: 30d          # Maximum time range for PII-inclusive reports
  pii_export_watermark: true         # PDF reports watermarked "CONTAINS PERSONAL DATA"
```

### 7.3 User Identity in Reports

By default, reports attribute actions to anonymised user IDs (e.g. `user_a1b2c3`). Enterprise policies can configure full user identity display:

```yaml
report_settings:
  user_identity_display: anonymised  # anonymised | full | department_only
```

---

## 8. SIEM Integration

loke can forward audit events and report summaries to Security Information and Event Management systems in real time or on a schedule.

### 8.1 Forwarding Modes

| Mode | Description |
|------|-------------|
| **Real-time** | Each audit event is forwarded as it occurs (< 5 second delay) |
| **Batch** | Events are buffered and forwarded at a configurable interval (default: 60 seconds) |
| **Report** | Completed report summaries are forwarded on generation |

### 8.2 Transport Protocols

| Protocol | Port (default) | Encryption | Description |
|----------|---------------|------------|-------------|
| Syslog UDP | 514 | None | Legacy syslog (RFC 5424). Not recommended. |
| Syslog TCP | 514 | Optional TLS | Reliable syslog delivery |
| Syslog TLS | 6514 | Required TLS | Encrypted syslog (RFC 5425) |
| HTTPS webhook | 443 | Required TLS | HTTP POST with JSON or CEF payload |

### 8.3 Event Formats

#### 8.3.1 CEF (Common Event Format)

ArcSight-compatible format. One line per event.

```
CEF:0|loke|loke|0.8.0|pii_detected|PII Detection Event|3|
  src=127.0.0.1
  dst=api.anthropic.com
  act=placeholder
  cs1Label=entity_type cs1=email_address
  cs2Label=detection_layer cs2=regex
  cs3Label=sensitivity_level cs3=restricted
  cs4Label=session_id cs4=sess_a1b2c3
  cn1Label=entity_count cn1=3
  rt=2026-03-15T09:12:33Z
```

**CEF severity mapping:**

| loke severity | CEF severity | CEF numeric |
|---------------|-------------|-------------|
| info | Low | 3 |
| advisory | Medium | 5 |
| warning | High | 7 |
| block | Very High | 9 |

#### 8.3.2 LEEF (Log Event Extended Format)

QRadar-compatible format.

```
LEEF:2.0|loke|loke|0.8.0|pii_detected|
  cat=Privacy
  src=127.0.0.1
  dst=api.anthropic.com
  action=placeholder
  entityType=email_address
  detectionLayer=regex
  sensitivityLevel=restricted
  sessionId=sess_a1b2c3
  entityCount=3
  devTime=2026-03-15T09:12:33Z
```

#### 8.3.3 JSON (Webhook)

Structured JSON for generic SIEM/SOAR integration.

```json
{
  "source": "loke",
  "version": "0.8.0",
  "event_id": "evt_20260315T091233Z_f4e5d6c7",
  "event_type": "pii_detected",
  "severity": "info",
  "timestamp": "2026-03-15T09:12:33Z",
  "details": {
    "entity_type": "email_address",
    "detection_layer": "regex",
    "sensitivity_level": "restricted",
    "action": "placeholder",
    "session_id": "sess_a1b2c3",
    "entity_count": 3,
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514"
  },
  "hash_chain": {
    "previous_hash": "a1b2c3d4...",
    "current_hash": "e5f6a7b8..."
  }
}
```

### 8.4 SIEM Configuration

```yaml
# In loke application config
siem:
  enabled: true
  mode: real_time                    # real_time | batch | report

  # Primary target
  targets:
    - id: splunk-primary
      transport: syslog_tls
      host: "siem.acme.com"
      port: 6514
      format: cef                    # cef | leef | json
      tls:
        ca_cert: "/etc/loke/siem-ca.pem"
        client_cert: "/etc/loke/siem-client.pem"
        client_key_env: "LOKE_SIEM_CLIENT_KEY"
      filter:
        min_severity: advisory       # Only forward advisory and above
        event_types:                 # Only forward these event types
          - pii_detected
          - policy_violation
          - routing_decision
          - user_override

    - id: webhook-secondary
      transport: https_webhook
      url: "https://soar.acme.com/api/v1/events"
      format: json
      auth:
        type: bearer
        token_env: "LOKE_SOAR_TOKEN"
      filter:
        min_severity: warning        # Only warnings and blocks

  # Batch mode settings (ignored in real_time mode)
  batch:
    interval: 60                     # seconds
    max_batch_size: 1000             # events per batch

  # Retry settings
  retry:
    max_attempts: 5
    backoff: exponential
    initial_delay: 5                 # seconds
    max_delay: 300                   # seconds

  # Buffer for offline resilience
  buffer:
    enabled: true
    max_size: 10000                  # events buffered when SIEM is unreachable
    flush_on_reconnect: true
```

### 8.5 Event Types

The following event types can be forwarded to SIEM:

| Event type | Description | Default severity |
|------------|-------------|-----------------|
| `pii_detected` | PII entity detected in user input | info |
| `pii_anonymised` | PII replaced with placeholder | info |
| `pii_redacted` | PII irreversibly removed | info |
| `pii_blocked` | Content blocked due to PII policy | warning |
| `policy_violation` | Policy rule triggered | Varies (info to block) |
| `policy_override` | User overrode a policy warning | advisory |
| `routing_decision` | Request routed to a provider | info |
| `routing_fallback` | Primary provider unavailable, fallback used | advisory |
| `provider_error` | LLM provider returned an error | warning |
| `budget_warning` | Budget threshold reached (80%, 90%, 100%) | advisory to block |
| `hash_chain_break` | Audit trail tamper detected | block |
| `report_generated` | Report was generated and exported | info |
| `pii_export_approved` | User opted in to PII-inclusive report | warning |
| `session_start` | New session opened | info |
| `session_end` | Session closed | info |

---

## 9. CLI Commands

All report operations are available through the `loke report` command group.

### 9.1 `loke report generate`

Generate a report on demand.

```
loke report generate <template> [options]

Arguments:
  template              Template ID or report type (e.g. "compliance-summary-default",
                        "compliance_summary")

Options:
  --range <preset>      Time range preset (today, last_week, last_month, etc.)
  --start <datetime>    Custom start time (ISO 8601)
  --end <datetime>      Custom end time (ISO 8601)
  --format <fmt>        Output format: json, csv, pdf (default: json)
  --output <path>       Output file path (default: stdout for json/csv, auto-named for pdf)
  --filter <key=value>  Filter (repeatable). E.g. --filter providers=anthropic,openai
  --param <key=value>   Template parameter (repeatable). E.g. --param department=engineering
  --include-pii         Include PII in report (requires policy permission, prompts for confirmation)
  --verify-chain        Verify hash chain integrity before generating (default: true)
  --no-verify-chain     Skip hash chain verification
  --quiet               Suppress progress output
  --dry-run             Show what the report would contain without generating it
```

**Examples:**

```bash
# Generate a compliance summary for last month as PDF
loke report generate compliance-summary-default \
  --range last_month --format pdf --output ~/reports/march-compliance.pdf

# Generate a PII detection summary for a specific date range as JSON
loke report generate pii-detection-summary \
  --start 2026-03-01 --end 2026-03-15 --format json

# Generate a cost report filtered to Anthropic, output to stdout
loke report generate cost-monthly \
  --range last_month --filter providers=anthropic

# Dry run to preview what a violation report would contain
loke report generate violations-full --range last_week --dry-run
```

### 9.2 `loke report schedule`

Manage scheduled reports.

```
loke report schedule <subcommand> [options]

Subcommands:
  create                Create a new schedule from a YAML file or inline options
  list                  List all schedules
  show <id>             Show details of a specific schedule
  pause <id>            Pause a schedule
  resume <id>           Resume a paused schedule
  delete <id>           Delete a schedule
  run <id>              Manually trigger a scheduled report now
  history <id>          Show execution history for a schedule
```

**Examples:**

```bash
# Create a schedule from a YAML file
loke report schedule create --file weekly-compliance.yaml

# Create a schedule inline
loke report schedule create \
  --id weekly-violations \
  --template violations-critical \
  --range last_week \
  --format pdf \
  --cron "0 8 * * 1" \
  --delivery file --delivery-path ~/reports/

# List all schedules
loke report schedule list

# Pause a schedule
loke report schedule pause weekly-violations

# Manually run a schedule now
loke report schedule run weekly-violations

# Show execution history
loke report schedule history weekly-violations --limit 10
```

### 9.3 `loke report list`

List previously generated reports.

```
loke report list [options]

Options:
  --type <type>         Filter by report type
  --range <preset>      Filter by generation date
  --format <fmt>        Filter by export format
  --template <id>       Filter by template ID
  --limit <n>           Maximum number of results (default: 20)
  --json                Output as JSON instead of table
```

**Example output:**

```
ID                              Type                 Generated            Format  Template
rpt_20260405T143022Z_a7b3c1d2   compliance_summary   2026-04-05 14:30     pdf     compliance-summary-default
rpt_20260401T080015Z_b8c4d2e1   policy_violations    2026-04-01 08:00     json    violations-critical
rpt_20260331T180000Z_c9d5e3f2   cost_token_usage     2026-03-31 18:00     csv     cost-monthly
```

### 9.4 `loke report templates`

List and inspect available templates.

```
loke report templates [options]

Options:
  --type <type>         Filter by report type
  --source <source>     Filter by source: builtin, enterprise, user
  --json                Output as JSON

Subcommands:
  show <id>             Show full template definition
  validate <file>       Validate a custom template YAML file
```

---

## 10. Browser Mode UI

### 10.1 Report Builder

The report builder is accessible from the loke sidebar under the "Reports" section. It provides a guided interface for generating reports.

**Layout:**

1. **Report type selector** — Card-based selection of the five report types, each with a brief description and icon.
2. **Template selector** — Dropdown of available templates for the selected report type, with a "Custom" option.
3. **Time range picker** — Preset buttons (Today, Last Week, Last Month, etc.) plus a calendar date-range picker for custom ranges.
4. **Filter panel** — Collapsible panel with filter controls. Each filter type has an appropriate input: multi-select dropdowns for providers and models, checkboxes for sensitivity levels, search-and-select for sessions.
5. **Template parameters** — Dynamic form fields generated from the template's parameter definitions.
6. **Format selector** — Radio buttons for PDF, CSV, JSON.
7. **Preview button** — Generates a preview of the report without saving.
8. **Generate button** — Generates and saves the report.

### 10.2 Report Preview

The preview renders the report in a read-only panel within the browser mode window. For PDF, it renders the formatted layout. For JSON and CSV, it renders a structured data view with collapsible sections and syntax highlighting.

The preview includes:

- A banner showing the time range and active filters
- A hash chain verification status indicator (green checkmark or red warning)
- A "Download" button to export the previewed report
- A "Schedule" button to create a recurring schedule from the current configuration

### 10.3 Report History

A table view of all previously generated reports, sortable by date, type, and format. Each row has actions: view, download, delete, and re-generate (with the same parameters).

### 10.4 Schedule Manager

A dedicated panel for managing scheduled reports:

- List of all schedules with status indicators (active, paused, failed)
- Next execution time for each schedule
- Last execution result and timestamp
- Create, edit, pause, resume, and delete actions
- Execution history log for each schedule

### 10.5 SIEM Status Panel

A monitoring panel showing:

- Connection status to each configured SIEM target (connected, disconnected, reconnecting)
- Events forwarded in the last hour/day
- Buffer status (events queued, buffer utilisation percentage)
- Last error message (if any)

---

## 11. Tamper Evidence

All exported reports include tamper evidence derived from the underlying audit trail hash chain (F6.2).

### 11.1 Hash Chain Verification

Before generating a report, loke verifies the integrity of the audit trail hash chain over the requested time range. The verification walks the chain from the first event in the range to the last, confirming that each event's hash is correctly derived from its content and the previous event's hash.

**Verification result (included in every report):**

```json
{
  "hash_chain_verification": {
    "verified": true,
    "chain_start": "evt_20260301T000000Z_0001",
    "chain_end": "evt_20260331T235959Z_4821",
    "events_verified": 4821,
    "breaks_detected": 0,
    "verification_timestamp": "2026-04-05T14:30:22Z",
    "verifier_version": "loke v0.8.0"
  }
}
```

If breaks are detected, the report includes the break locations and a warning banner:

```json
{
  "hash_chain_verification": {
    "verified": false,
    "chain_start": "evt_20260301T000000Z_0001",
    "chain_end": "evt_20260331T235959Z_4821",
    "events_verified": 4821,
    "breaks_detected": 2,
    "break_locations": [
      {
        "event_id": "evt_20260315T141200Z_2103",
        "expected_hash": "a1b2c3d4...",
        "actual_hash": "e5f6a7b8...",
        "description": "Hash mismatch — possible tampering or data corruption"
      }
    ],
    "verification_timestamp": "2026-04-05T14:30:22Z",
    "verifier_version": "loke v0.8.0"
  }
}
```

### 11.2 Report Checksums

Every exported report includes a SHA-256 checksum of its data section. This enables recipients to verify that the report has not been modified after generation.

**Checksum calculation:**

1. Serialise the `data` section as canonical JSON (sorted keys, no whitespace, UTF-8)
2. Compute SHA-256 hash of the serialised bytes
3. Include the hash in the `report.checksum` envelope field

**Verification command:**

```bash
# Verify a JSON report's integrity
loke report verify report.json

# Output:
# Report: rpt_20260405T143022Z_a7b3c1d2
# Checksum: VALID (sha256:e3b0c44298fc1c14...)
# Hash chain: VERIFIED (4821 events, 0 breaks)
```

### 11.3 PDF Digital Signatures

PDF reports can optionally be digitally signed using a user-provided certificate. This provides non-repudiation — proof that the report was generated by a specific loke instance.

```yaml
# In loke application config
report_signing:
  enabled: true
  certificate: "/etc/loke/report-signing.pem"
  private_key_env: "LOKE_REPORT_SIGNING_KEY"
  include_timestamp: true            # Embed a trusted timestamp (RFC 3161)
  timestamp_authority: "http://timestamp.digicert.com"
```

---

## 12. Configuration Reference

Complete configuration schema for report settings, combining all sections from this specification.

```yaml
# In loke application config (settings.yaml)
reporting:
  # Default export settings
  defaults:
    format: json                     # json | csv | pdf
    time_range: last_month
    verify_chain: true               # Verify hash chain before generating

  # PDF rendering
  pdf:
    renderer: playwright             # playwright (Chromium headless)
    page_size: a4                    # a4 | letter
    branding:
      logo_path: null                # Path to logo image (optional)
      primary_colour: "#1e40af"      # Primary brand colour
      footer_text: null              # Custom footer text (optional)

  # Report storage
  storage:
    path: "~/.local/share/loke/reports/"
    max_reports: 500                 # Maximum stored reports (oldest deleted first)
    max_storage: "1GB"               # Maximum disk usage for stored reports

  # Template directories
  templates:
    user_dir: "~/.config/loke/report-templates/"
    enterprise_dir: null             # Set by enterprise policy

  # Schedule settings
  schedules:
    dir: "~/.config/loke/report-schedules/"
    daemon_check_interval: 60        # seconds between schedule checks

  # SMTP for email delivery
  smtp:
    host: null
    port: 587
    encryption: starttls             # starttls | ssl | none
    username_env: "LOKE_SMTP_USER"
    password_env: "LOKE_SMTP_PASS"
    from: null                       # Sender address

  # Report signing
  signing:
    enabled: false
    certificate: null
    private_key_env: null
    timestamp_authority: null

# SIEM configuration (see section 8.4)
siem:
  enabled: false
  mode: batch
  targets: []
  batch:
    interval: 60
    max_batch_size: 1000
  retry:
    max_attempts: 5
    backoff: exponential
    initial_delay: 5
    max_delay: 300
  buffer:
    enabled: true
    max_size: 10000
    flush_on_reconnect: true

# Policy-level report settings (in policy file, A3.1 format)
# report_settings:
#   allow_pii_export: false
#   pii_export_requires_reason: true
#   pii_export_max_range: 30d
#   pii_export_watermark: true
#   user_identity_display: anonymised
#   mandatory_reports:               # Enterprise can mandate scheduled reports
#     - template: compliance-summary-default
#       cron: "0 8 1 * *"
#       format: pdf
#       delivery:
#         - type: file
#           path: "/shared/compliance-reports/"
```

---

## 13. Implementation Notes

### 13.1 Performance Considerations

- Report generation must complete within 30 seconds for time ranges up to 90 days with up to 100,000 audit events. For larger ranges, progress indicators must be shown.
- Hash chain verification is O(n) in the number of events. For very large audit trails (> 1 million events), verification can be parallelised by checking sub-chains and verifying join points.
- PDF rendering via Playwright adds 2-5 seconds of overhead. The Playwright browser instance should be reused across report generations, not started fresh each time.
- CSV export streams rows incrementally and does not require loading the entire dataset into memory.

### 13.2 Error Handling

| Error | Behaviour |
|-------|-----------|
| Audit trail empty for time range | Generate report with zero-data sections and an informational banner |
| Hash chain verification fails | Generate report with a prominent warning; do not suppress the report |
| PDF renderer unavailable | Fall back to JSON with an error message explaining PDF is unavailable |
| SIEM target unreachable | Buffer events locally; retry with exponential backoff |
| Schedule delivery fails | Retry up to `max_attempts`; pause schedule and emit notification on exhaustion |
| Template validation fails | Reject with a descriptive error listing all validation failures |
| Insufficient disk space | Refuse to generate; emit a warning with current usage and configured limits |

### 13.3 Security Considerations

- Report files are written with restrictive permissions (0600 on Unix).
- SMTP credentials and signing keys are read from environment variables, never stored in configuration files.
- Webhook URLs and SIEM targets should use TLS. loke emits a warning if a non-TLS target is configured.
- PII-inclusive reports (section 7.2) are the highest-risk export. The audit trail records every PII export with user identity, stated reason, and timestamp. Enterprise policies can disable this entirely.
- Report checksums (section 11.2) use SHA-256. The checksum covers the data section only, not the envelope, so that verification metadata can be added without invalidating the checksum.
