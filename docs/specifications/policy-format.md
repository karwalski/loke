# Policy Definition Format Specification

**Story:** A3.1 — Policy definition format and loader
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-04

---

## 1. Overview

loke policies are YAML documents that define the rules governing how data is classified, which providers and MCP servers are permitted, what anonymisation is required, and how budgets and retention are managed. Policies are the mechanism through which regulatory requirements, organisational rules, and user preferences are expressed and enforced by the policy engine.

This specification defines:

- The complete YAML schema for policy documents
- How policies from multiple sources are loaded and merged
- Versioning and hot-reload semantics
- Validation rules and error handling

### 1.1 Design Alignment

This specification follows the loke design principles:

- **The user is the authority.** Policies inform and constrain, but enterprise hard blocks are the only truly unoverridable constraint. User-level policies can always loosen within the bounds set above them.
- **Do the right thing by default.** When no explicit policy is loaded, loke behaves as if the most restrictive reasonable defaults apply.
- **Warnings must be earned.** Policy violations produce graduated responses (info, advisory, warning, block) rather than treating everything as an error.
- **Privacy is the foundation.** The policy system defaults to protecting data, not exposing it.

---

## 2. Policy Sources

Policies can be loaded from three sources, listed in precedence order (highest first):

| Source | Description | Typical author |
|--------|-------------|----------------|
| **Enterprise** | Fetched from a URL on startup, or pushed via MDM (Mobile Device Management). Represents organisational mandates. | IT/compliance team |
| **Team** | Local file shared across a team (e.g. checked into a repository, distributed via shared drive, or fetched from a team-specific URL). | Team lead / project manager |
| **User** | Local file on the user's device. Personal preferences and overrides within permitted bounds. | Individual user |

### 2.1 Source Configuration

Policy sources are configured in the loke application settings (not within policy files themselves):

```yaml
# In loke application config (settings.yaml or equivalent)
policy_sources:
  enterprise:
    type: url                          # url | mdm | file
    url: "https://policies.acme.com/loke/enterprise.yaml"
    refresh_interval: 300              # seconds between re-fetches
    auth:
      type: bearer                     # bearer | mtls | oauth2
      token_env: "LOKE_ENTERPRISE_TOKEN"
    required: true                     # if true, loke refuses to start without it

  team:
    type: file
    path: "./.loke/team-policy.yaml"   # relative to project root, or absolute
    required: false

  user:
    type: file
    path: "~/.config/loke/policy.yaml"
    required: false
```

### 2.2 MDM Delivery

On managed devices, enterprise policies can be pushed via MDM profiles:

- **macOS:** Configuration profile placing the policy file at a managed path (e.g. `/Library/Managed Preferences/dev.loke/enterprise-policy.yaml`)
- **Windows:** Group Policy or Intune deploying to a managed directory
- **Linux:** Configuration management (Ansible, Puppet) placing the file

When an MDM-delivered policy is detected, it takes precedence over URL-fetched enterprise policy.

---

## 3. Policy Document Schema

Every policy file is a YAML document conforming to the schema below. All top-level sections are optional — an empty file is a valid (no-op) policy. Fields not specified inherit from the layer below or fall back to built-in defaults.

### 3.1 Document Root

```yaml
# Required metadata
policy_version: "1.0"                  # Schema version (semver major.minor)
metadata:
  name: "Acme Corp Enterprise Policy"  # Human-readable name
  id: "acme-enterprise-2026q1"         # Unique identifier for audit trail
  description: "Enterprise data governance policy for Acme Corporation"
  author: "security@acme.com"
  created: "2026-01-15T00:00:00Z"      # ISO 8601
  updated: "2026-03-20T14:30:00Z"      # ISO 8601
  regulation_basis:                     # Regulations this policy implements
    - "eu-gdpr"
    - "au-privacy-act"
  tags:                                 # Arbitrary tags for filtering/grouping
    - "production"
    - "apac-region"

# Policy sections (all optional)
data_classification: { ... }
provider_restrictions: { ... }
mcp_servers: { ... }
sensitivity_thresholds: { ... }
budget_limits: { ... }
retention: { ... }
anonymisation: { ... }
```

### 3.2 Field Reference: `policy_version`

| Property | Value |
|----------|-------|
| Type | `string` |
| Required | Yes |
| Format | Semver `major.minor` (e.g. `"1.0"`, `"1.1"`, `"2.0"`) |
| Validation | Must be a version this build of loke understands. Major version changes are breaking. |
| Current | `"1.0"` |

### 3.3 Field Reference: `metadata`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable policy name. Max 200 characters. |
| `id` | string | Yes | Unique identifier. Used in audit logs to record which policy was active. Must match `^[a-z0-9][a-z0-9._-]{0,127}$`. |
| `description` | string | No | Longer description. Max 2000 characters. |
| `author` | string | No | Contact or author identifier. |
| `created` | string (ISO 8601) | No | Creation timestamp. |
| `updated` | string (ISO 8601) | No | Last modification timestamp. |
| `regulation_basis` | list of string | No | Identifiers of regulations this policy implements. Informational only. |
| `tags` | list of string | No | Arbitrary tags. Max 20 tags, each max 50 characters. |

---

## 4. Data Classification

The `data_classification` section defines how data is categorised by sensitivity, and what rules apply to each classification level.

```yaml
data_classification:
  # Define classification levels (ordered from least to most sensitive)
  levels:
    - id: public
      name: "Public"
      description: "Information intended for public disclosure"
      color: "#22c55e"                 # UI display colour (optional)

    - id: internal
      name: "Internal"
      description: "General business information not intended for public release"
      color: "#3b82f6"

    - id: confidential
      name: "Confidential"
      description: "Sensitive business information with limited distribution"
      color: "#f59e0b"

    - id: restricted
      name: "Restricted"
      description: "Highly sensitive data — PII, financial records, health data, trade secrets"
      color: "#ef4444"

    - id: prohibited
      name: "Prohibited"
      description: "Data that must never leave the device under any circumstances"
      color: "#7f1d1d"

  # Default classification when data cannot be automatically classified
  default_level: confidential

  # Rules mapping data types to classification levels
  rules:
    - pattern: "email_address"
      level: restricted
      description: "Email addresses are personal data"

    - pattern: "credit_card"
      level: prohibited
      description: "Payment card data must never be transmitted"

    - pattern: "medical_record"
      level: restricted
      description: "Health information requires highest protection"

    - pattern: "source_code"
      level: confidential
      description: "Proprietary source code"

    - pattern: "public_api_docs"
      level: public
      description: "Published API documentation"
```

### 4.1 Field Reference: `data_classification`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `levels` | list of level objects | No | Built-in 5-level scale (public, internal, confidential, restricted, prohibited) | Ordered list from least to most sensitive. Min 2, max 10. |
| `levels[].id` | string | Yes | — | Unique identifier. Must match `^[a-z][a-z0-9_-]{0,31}$`. |
| `levels[].name` | string | Yes | — | Display name. Max 50 characters. |
| `levels[].description` | string | No | — | Human-readable description. Max 500 characters. |
| `levels[].color` | string | No | — | Hex colour for UI. Must match `^#[0-9a-fA-F]{6}$`. |
| `default_level` | string | No | `"confidential"` | Level ID applied when automatic classification is inconclusive. Must reference a defined level. |
| `rules` | list of rule objects | No | Built-in PII detection rules | Rules mapping detected data patterns to levels. |
| `rules[].pattern` | string | Yes | — | Pattern identifier from loke's detection engine (e.g. `email_address`, `phone_number`, `credit_card`, `ssn`, `medical_record`, `source_code`, `api_key`). Also supports regex via `regex:` prefix. |
| `rules[].level` | string | Yes | — | Classification level ID to assign. Must reference a defined level. |
| `rules[].description` | string | No | — | Why this rule exists. Shown to users when the rule triggers. |

### 4.2 Built-in Pattern Identifiers

The following pattern identifiers are recognised by loke's detection engine. Policy rules reference these by name.

| Pattern ID | Description | Detection Layer |
|------------|-------------|-----------------|
| `email_address` | Email addresses | Regex |
| `phone_number` | Phone numbers (international formats) | Regex |
| `credit_card` | Credit/debit card numbers (Luhn-validated) | Regex |
| `ssn` | US Social Security Numbers | Regex |
| `tfn` | Australian Tax File Numbers | Regex |
| `abn` | Australian Business Numbers | Regex |
| `medicare_number` | Australian Medicare numbers | Regex |
| `nhs_number` | UK NHS numbers | Regex |
| `iban` | International Bank Account Numbers | Regex |
| `ip_address` | IPv4 and IPv6 addresses | Regex |
| `date_of_birth` | Dates of birth (contextual) | NLP |
| `person_name` | Personal names | NLP / SLM NER |
| `organisation_name` | Company and organisation names | NLP / SLM NER |
| `street_address` | Physical addresses | NLP / SLM NER |
| `medical_record` | Medical/health information (ICD codes, diagnoses, prescriptions) | SLM NER |
| `genetic_data` | Genetic or biometric data | SLM NER |
| `api_key` | API keys and tokens | Regex |
| `password` | Passwords and credentials | Regex |
| `source_code` | Proprietary source code patterns | SLM classification |
| `financial_record` | Financial statements, account details | SLM NER |
| `legal_document` | Legal contracts, privileged communications | SLM classification |

Custom patterns can be defined using the `regex:` prefix:

```yaml
rules:
  - pattern: "regex:ACME-\\d{4}-[A-Z]{2}"
    level: confidential
    description: "Acme internal project codes"
```

---

## 5. Provider Restrictions

The `provider_restrictions` section controls which LLM providers and models can be used, and under what conditions.

```yaml
provider_restrictions:
  # Global default: allow or deny providers not explicitly listed
  default_action: deny                 # allow | deny

  providers:
    - id: anthropic
      action: allow
      models:
        - pattern: "claude-*"
          action: allow
        - pattern: "claude-*-instant"
          action: allow
      max_classification: confidential  # Highest data classification sendable
      regions:                          # Require provider processing in these regions
        - "us"
        - "eu"
      require_encryption: true          # Require TLS 1.3+

    - id: openai
      action: allow
      models:
        - pattern: "gpt-4*"
          action: allow
        - pattern: "gpt-3.5*"
          action: deny                 # Explicitly block older models
      max_classification: internal

    - id: google
      action: allow
      max_classification: internal

    - id: local
      action: allow
      max_classification: prohibited    # Local models can see everything
      note: "Local models process on-device; no data leaves"

    - id: "*"                           # Catch-all for unlisted providers
      action: deny
      reason: "Provider not approved. Contact security@acme.com to request approval."
```

### 5.1 Field Reference: `provider_restrictions`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `default_action` | `allow` or `deny` | No | `deny` | Action for providers not matching any rule. |
| `providers` | list of provider objects | No | Allow all providers up to `confidential` | Provider-specific rules. Evaluated in order; first match wins. |
| `providers[].id` | string | Yes | — | Provider identifier (`anthropic`, `openai`, `google`, `mistral`, `local`, `ollama`, etc.) or `"*"` for catch-all. |
| `providers[].action` | `allow` or `deny` | Yes | — | Whether to permit this provider. |
| `providers[].models` | list of model rules | No | All models inherit provider action | Model-specific overrides within a provider. |
| `providers[].models[].pattern` | string | Yes | — | Model name or glob pattern (e.g. `"gpt-4*"`, `"claude-sonnet-4-*"`). |
| `providers[].models[].action` | `allow` or `deny` | Yes | — | Override action for matching models. |
| `providers[].max_classification` | string | No | One level below `prohibited` | Highest data classification level that may be sent to this provider. Must reference a defined classification level. |
| `providers[].regions` | list of string | No | No restriction | ISO 3166-1 alpha-2 region codes where provider must process data. Empty list means no regional requirement. |
| `providers[].require_encryption` | boolean | No | `true` | Require TLS 1.3 or higher for API connections. |
| `providers[].reason` | string | No | — | Human-readable explanation shown when this rule blocks a request. |
| `providers[].note` | string | No | — | Informational note (not shown to users, used for policy documentation). |

---

## 6. MCP Server Controls

The `mcp_servers` section defines which MCP servers loke may connect to or host, and what data may flow through them.

```yaml
mcp_servers:
  # Global default for MCP servers not explicitly listed
  default_action: deny

  # Whitelist / blacklist entries
  servers:
    - pattern: "filesystem"
      action: allow
      max_classification: restricted
      data_filters:
        - exclude_patterns: ["*.env", "*.pem", "*.key", "*credentials*"]
      note: "Filesystem access with sensitive file exclusions"

    - pattern: "git"
      action: allow
      max_classification: confidential

    - pattern: "slack"
      action: allow
      max_classification: internal
      require_anonymisation: true       # All data through this MCP must be anonymised

    - pattern: "database-*"
      action: allow
      max_classification: restricted
      data_filters:
        - mask_columns: ["ssn", "email", "phone", "date_of_birth", "salary"]

    - pattern: "google-drive"
      action: deny
      reason: "Google Drive MCP not approved. Use filesystem MCP for local files."

    - pattern: "*"
      action: deny
      reason: "Unapproved MCP server. Contact your administrator to request access."

  # Controls for tool calls within allowed MCP servers
  tool_controls:
    - server: "filesystem"
      tool: "write_file"
      action: deny                     # Allow read but not write
      reason: "Filesystem write access disabled by policy"

    - server: "database-*"
      tool: "execute_query"
      action: allow
      constraints:
        read_only: true                # Only SELECT queries permitted
```

### 6.1 Field Reference: `mcp_servers`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `default_action` | `allow` or `deny` | No | `deny` | Action for MCP servers not matching any rule. |
| `servers` | list of server rules | No | Deny all | Server-level access rules. Evaluated in order; first match wins. |
| `servers[].pattern` | string | Yes | — | MCP server name or glob pattern. |
| `servers[].action` | `allow` or `deny` | Yes | — | Whether to permit connection. |
| `servers[].max_classification` | string | No | `internal` | Highest data classification sendable through this MCP. |
| `servers[].require_anonymisation` | boolean | No | `false` | Force all data through the anonymisation pipeline before sending to this MCP. |
| `servers[].data_filters` | list of filter objects | No | None | Data filtering rules specific to this server. |
| `servers[].data_filters[].exclude_patterns` | list of string | No | — | Glob patterns for files/data to exclude. |
| `servers[].data_filters[].mask_columns` | list of string | No | — | Column names to mask in database results. |
| `servers[].reason` | string | No | — | Human-readable explanation when rule blocks. |
| `servers[].note` | string | No | — | Documentation note. |
| `tool_controls` | list of tool rules | No | All tools inherit server action | Override actions for specific tools within an MCP server. |
| `tool_controls[].server` | string | Yes | — | MCP server name or glob pattern. |
| `tool_controls[].tool` | string | Yes | — | Tool name within the server. |
| `tool_controls[].action` | `allow` or `deny` | Yes | — | Override action. |
| `tool_controls[].constraints` | object | No | — | Additional constraints (server/tool-specific). |
| `tool_controls[].reason` | string | No | — | Human-readable explanation. |

---

## 7. Sensitivity Thresholds

The `sensitivity_thresholds` section configures how loke's detection engine classifies data sensitivity, and what actions are triggered at each threshold.

```yaml
sensitivity_thresholds:
  # Confidence threshold for PII detection (0.0 to 1.0)
  # Lower values catch more potential PII but increase false positives
  pii_detection_threshold: 0.7

  # Minimum confidence to auto-anonymise without user confirmation
  auto_anonymise_threshold: 0.9

  # Below this confidence, flag for user review rather than auto-acting
  review_threshold: 0.5

  # Actions triggered by sensitivity level
  actions:
    public:
      require_anonymisation: false
      allow_cloud: true
      require_user_confirmation: false
      log_level: info

    internal:
      require_anonymisation: false
      allow_cloud: true
      require_user_confirmation: false
      log_level: info

    confidential:
      require_anonymisation: true
      allow_cloud: true
      require_user_confirmation: false
      log_level: standard

    restricted:
      require_anonymisation: true
      allow_cloud: true                # Allowed only after anonymisation
      require_user_confirmation: true  # User must confirm before sending
      log_level: detailed

    prohibited:
      require_anonymisation: false     # Irrelevant — data cannot leave
      allow_cloud: false
      require_user_confirmation: false # No confirmation needed — just blocked
      log_level: detailed
```

### 7.1 Field Reference: `sensitivity_thresholds`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pii_detection_threshold` | float | No | `0.7` | Minimum confidence score (0.0–1.0) for a PII detection to be considered valid. |
| `auto_anonymise_threshold` | float | No | `0.9` | Minimum confidence for automatic anonymisation without user review. |
| `review_threshold` | float | No | `0.5` | Detections below this confidence are logged but not acted on. Between this and `pii_detection_threshold`, items are flagged for review. |
| `actions` | map of level ID to action object | No | Built-in defaults as shown above | Per-classification-level actions. Keys must reference defined classification levels. |
| `actions.<level>.require_anonymisation` | boolean | No | Varies by level | Whether data at this level must be anonymised before cloud transmission. |
| `actions.<level>.allow_cloud` | boolean | No | Varies by level | Whether data at this level may be sent to cloud providers (after anonymisation if required). |
| `actions.<level>.require_user_confirmation` | boolean | No | `false` | Whether user must explicitly confirm before data at this level is transmitted. |
| `actions.<level>.log_level` | `minimal`, `info`, `standard`, or `detailed` | No | `standard` | How much detail to capture in the audit trail for operations involving data at this level. |

### 7.2 Threshold Interaction

The three threshold values must satisfy: `review_threshold` <= `pii_detection_threshold` <= `auto_anonymise_threshold`. Validation rejects policies where this invariant is violated.

Detection confidence is mapped to actions as follows:

```
0.0 ─────────── review_threshold ─────────── pii_detection_threshold ─────────── auto_anonymise_threshold ─────────── 1.0
     Ignored          Flagged for review          Detected, user confirms            Auto-anonymised
```

---

## 8. Budget Limits

The `budget_limits` section defines spending controls for LLM API usage.

```yaml
budget_limits:
  # Currency for all monetary values
  currency: "USD"

  # Global budget (across all providers)
  global:
    daily: 5.00
    weekly: 25.00
    monthly: 80.00

  # Per-provider budgets (override global for specific providers)
  per_provider:
    anthropic:
      daily: 3.00
      monthly: 50.00
    openai:
      daily: 2.00
      monthly: 30.00

  # Per-model budgets (most specific, overrides provider and global)
  per_model:
    "claude-sonnet-4-20250514":
      daily: 2.00
    "gpt-4o":
      daily: 1.50

  # What happens when a budget is exceeded
  on_exceed:
    action: warn_and_block             # warn | warn_and_block | block | downgrade
    downgrade_to: "local"              # Provider to fall back to (for downgrade action)
    notification: true                 # Show notification to user
    allow_override: false              # Can user override the block?
    message: "Daily budget exceeded. Requests will be routed to local models until the budget resets."

  # Token tracking
  token_tracking:
    warn_at_percentage: 80             # Warn when this percentage of budget is used
    track_cached_tokens: false         # Whether cached/free tokens count toward budget
```

### 8.1 Field Reference: `budget_limits`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `currency` | string (ISO 4217) | No | `"USD"` | Currency code for all monetary amounts. |
| `global` | budget object | No | No limit | Global spending limits across all providers. |
| `global.daily` | float | No | No limit | Maximum daily spend. Resets at midnight UTC. |
| `global.weekly` | float | No | No limit | Maximum weekly spend. Resets Monday 00:00 UTC. |
| `global.monthly` | float | No | No limit | Maximum monthly spend. Resets 1st of month 00:00 UTC. |
| `per_provider` | map of provider ID to budget object | No | No per-provider limits | Provider-specific budgets. Same fields as `global`. |
| `per_model` | map of model ID to budget object | No | No per-model limits | Model-specific budgets. Same fields as `global`. |
| `on_exceed` | action object | No | `warn_and_block` | Behaviour when any budget is exceeded. |
| `on_exceed.action` | `warn`, `warn_and_block`, `block`, or `downgrade` | No | `warn_and_block` | `warn`: advisory only. `warn_and_block`: warn then block. `block`: block silently. `downgrade`: route to cheaper alternative. |
| `on_exceed.downgrade_to` | string | No | `"local"` | Provider to route to when downgrading. Only used with `downgrade` action. |
| `on_exceed.notification` | boolean | No | `true` | Whether to display a notification. |
| `on_exceed.allow_override` | boolean | No | `false` | Whether user can override the budget block. Enterprise policies typically set this to `false`. |
| `on_exceed.message` | string | No | Built-in message | Custom message shown to user. |
| `token_tracking.warn_at_percentage` | integer (1–99) | No | `80` | Show advisory when this percentage of any budget period is consumed. |
| `token_tracking.track_cached_tokens` | boolean | No | `false` | Whether semantically cached responses count toward spend. |

---

## 9. Retention

The `retention` section defines how long different types of data are kept locally.

```yaml
retention:
  # Audit logs
  audit_logs:
    duration: "365d"                   # How long to keep audit entries
    on_expiry: archive                 # delete | archive
    archive_path: "~/.loke/archives/"  # Only used when on_expiry is archive

  # Conversation history
  conversations:
    duration: "90d"
    on_expiry: delete

  # PII mapping tables (placeholder <-> real value)
  pii_mappings:
    duration: "session"                # session | Nd | never
    on_expiry: secure_delete           # Overwrite, don't just unlink

  # Semantic cache
  cache:
    duration: "30d"
    max_size: "2GB"                    # Maximum cache size on disk
    on_expiry: delete

  # Anonymisation cannot be reversed after this period
  deanonymisation_window:
    duration: "24h"                    # After this, mapping is destroyed
```

### 9.1 Field Reference: `retention`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `audit_logs.duration` | duration string | No | `"365d"` | Retention period. Format: `Nd` (days), `Nw` (weeks), `Nm` (months), `Ny` (years), or `"forever"`. |
| `audit_logs.on_expiry` | `delete` or `archive` | No | `archive` | What to do when retention period expires. |
| `audit_logs.archive_path` | string | No | `"~/.loke/archives/"` | Directory for archived logs. Only used with `archive` action. |
| `conversations.duration` | duration string | No | `"90d"` | Conversation history retention. |
| `conversations.on_expiry` | `delete` or `archive` | No | `delete` | Expiry action. |
| `pii_mappings.duration` | `"session"` or duration string or `"never"` | No | `"session"` | How long PII placeholder mappings are kept. `"session"` means destroyed when the session ends. |
| `pii_mappings.on_expiry` | `delete` or `secure_delete` | No | `secure_delete` | `secure_delete` overwrites data before unlinking. |
| `cache.duration` | duration string | No | `"30d"` | Semantic cache retention. |
| `cache.max_size` | size string | No | `"2GB"` | Maximum disk usage. Format: `N` + `MB`, `GB`, or `TB`. |
| `cache.on_expiry` | `delete` | No | `delete` | Cache entries are always deleted. |
| `deanonymisation_window.duration` | duration string or `"session"` | No | `"24h"` | Period after which PII mappings are irrevocably destroyed, making deanonymisation impossible. Regulatory policies often set this to `"session"`. |

### 9.2 Duration String Format

Duration strings follow the pattern `<integer><unit>`:

| Unit | Meaning | Example |
|------|---------|---------|
| `h` | Hours | `24h` |
| `d` | Days | `30d` |
| `w` | Weeks | `4w` |
| `m` | Months (calendar) | `6m` |
| `y` | Years (calendar) | `1y` |

Special values: `"session"` (destroyed at session end), `"forever"` or `"never"` (retained indefinitely, subject to explicit user deletion).

---

## 10. Anonymisation

The `anonymisation` section configures the anonymisation pipeline's behaviour.

```yaml
anonymisation:
  # Default anonymisation level applied when policy requires anonymisation
  default_level: standard

  # Anonymisation level definitions
  levels:
    minimal:
      description: "Replace only high-confidence structured PII (emails, SSNs, credit cards)"
      layers: [regex]
      placeholder_format: "[$TYPE]"     # e.g. [EMAIL], [SSN]

    standard:
      description: "Replace structured PII and named entities (names, organisations, locations)"
      layers: [regex, nlp]
      placeholder_format: "$t$n"        # e.g. $c1, $l2, $p3 (as per loke spec)

    comprehensive:
      description: "Full anonymisation including contextual and semantic PII"
      layers: [regex, nlp, slm_ner, presidio]
      placeholder_format: "$t$n"

    maximum:
      description: "Comprehensive anonymisation plus generalisation of quasi-identifiers"
      layers: [regex, nlp, slm_ner, presidio]
      placeholder_format: "$t$n"
      generalise_dates: true            # "March 15, 1990" -> "1990"
      generalise_locations: true        # "42 Oak St, Melbourne" -> "Melbourne, AU"
      generalise_ages: true             # "34 years old" -> "30-39"
      suppress_rare_values: true        # Values appearing <5 times in dataset suppressed

  # Entity-specific overrides
  entity_overrides:
    credit_card:
      action: redact                   # redact | anonymise | hash | mask
      # redact: replace entirely with placeholder
      # anonymise: reversible placeholder ($c1)
      # hash: one-way hash (irreversible)
      # mask: partial masking (****-****-****-1234)

    email_address:
      action: anonymise

    person_name:
      action: anonymise

    medical_record:
      action: redact                   # Never reversible for health data

  # Whether anonymisation can be reversed (deanonymisation)
  allow_deanonymisation: true
  deanonymisation_requires_auth: false  # If true, user must re-authenticate
```

### 10.1 Field Reference: `anonymisation`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `default_level` | string | No | `"standard"` | Default anonymisation level ID. Must reference a defined level. |
| `levels` | map of level ID to level object | No | Built-in levels as above | Anonymisation level definitions. |
| `levels.<id>.description` | string | No | — | Human-readable description. |
| `levels.<id>.layers` | list of layer IDs | Yes | — | Ordered list of detection layers to apply. Valid values: `regex`, `nlp`, `slm_ner`, `presidio`. |
| `levels.<id>.placeholder_format` | string | No | `"$t$n"` | Format for replacement placeholders. `$t` = type abbreviation, `$n` = counter. |
| `levels.<id>.generalise_dates` | boolean | No | `false` | Reduce date precision to year only. |
| `levels.<id>.generalise_locations` | boolean | No | `false` | Reduce location precision to city/country. |
| `levels.<id>.generalise_ages` | boolean | No | `false` | Replace exact ages with decade ranges. |
| `levels.<id>.suppress_rare_values` | boolean | No | `false` | Suppress values that could re-identify through uniqueness. |
| `entity_overrides` | map of pattern ID to override object | No | — | Per-entity-type handling overrides. Keys are pattern IDs from section 4.2. |
| `entity_overrides.<id>.action` | `redact`, `anonymise`, `hash`, or `mask` | Yes | — | How to handle this entity type. |
| `allow_deanonymisation` | boolean | No | `true` | Whether placeholder mappings are stored for later reversal. `false` makes all anonymisation one-way. |
| `deanonymisation_requires_auth` | boolean | No | `false` | Whether the user must re-authenticate to deanonymise. |

### 10.2 Anonymisation Actions

| Action | Behaviour | Reversible | Example |
|--------|-----------|-----------|---------|
| `redact` | Replace with type-only placeholder | No | `john.doe@acme.com` -> `[EMAIL]` |
| `anonymise` | Replace with typed+numbered placeholder, store mapping | Yes | `john.doe@acme.com` -> `$e1` |
| `hash` | Replace with deterministic one-way hash | No | `john.doe@acme.com` -> `a1b2c3d4` |
| `mask` | Partially obscure, preserving format | No | `john.doe@acme.com` -> `j***.d**@****.com` |

---

## 11. Hierarchical Merge Semantics

When multiple policy sources are present, they are merged into a single effective policy. The merge follows a strict precedence model: enterprise > team > user.

### 11.1 Merge Algorithm

The merge is performed section by section. The general principle is **most restrictive wins on conflicts**, but the precise behaviour depends on the field type.

#### Scalar Fields (strings, numbers, booleans)

For fields where "more restrictive" has a clear meaning, the more restrictive value wins regardless of source:

| Field type | "More restrictive" means | Example |
|------------|------------------------|---------|
| `default_action` (allow/deny) | `deny` wins over `allow` | Enterprise: `deny`, User: `allow` -> effective: `deny` |
| `max_classification` | Lower classification wins | Enterprise: `internal`, User: `restricted` -> effective: `internal` |
| `allow_cloud` | `false` wins over `true` | Team: `false`, User: `true` -> effective: `false` |
| `require_anonymisation` | `true` wins over `false` | Enterprise: `true`, User: `false` -> effective: `true` |
| `require_user_confirmation` | `true` wins over `false` | |
| Budget amounts | Lower amount wins | Enterprise: `$50/mo`, User: `$100/mo` -> effective: `$50/mo` |
| `pii_detection_threshold` | Lower threshold wins (catches more) | Enterprise: `0.5`, User: `0.8` -> effective: `0.5` |
| Retention durations | Regulatory minimum or maximum applies (see 11.2) | |
| `allow_deanonymisation` | `false` wins over `true` | |

For fields where "more restrictive" is ambiguous or not applicable, the highest-precedence source that defines the field wins:

| Field type | Behaviour |
|------------|-----------|
| `metadata` | Not merged. Each layer retains its own metadata. The effective policy records all three. |
| `currency` | Highest-precedence source wins. |
| `placeholder_format` | Highest-precedence source wins. |
| `on_exceed.action` | Highest-precedence source wins. |
| `on_exceed.message` | Highest-precedence source wins. |
| Display fields (`name`, `description`, `color`) | Highest-precedence source wins. |

#### List Fields (provider lists, server lists, rules)

Lists are **merged by union with override**:

1. All entries from all sources are combined.
2. When entries share the same `id` or `pattern`, the entry from the highest-precedence source wins.
3. Deny rules always take precedence over allow rules for the same target, regardless of source. A user-level policy cannot allow a provider that enterprise-level policy denies.

Example:

```yaml
# Enterprise policy
provider_restrictions:
  providers:
    - id: openai
      action: deny                     # Enterprise blocks OpenAI

# User policy
provider_restrictions:
  providers:
    - id: openai
      action: allow                    # User tries to allow OpenAI
    - id: mistral
      action: allow                    # User adds Mistral

# Effective policy
provider_restrictions:
  providers:
    - id: openai
      action: deny                     # Enterprise deny wins
    - id: mistral
      action: allow                    # User addition stands (no conflict)
```

#### Map Fields (per_provider budgets, entity_overrides, action maps)

Maps are merged by key union with override:

1. All keys from all sources are combined.
2. When the same key appears in multiple sources, the more restrictive value wins (using the scalar rules above).
3. Keys present in only one source are included as-is.

#### Classification Levels

Classification levels are special: the effective set is the **union** of all defined levels from all sources, ordered by the enterprise-defined ordering. If only user and team levels are defined, they are merged by ID and ordered by the team-defined ordering. Users cannot remove or reorder levels defined at a higher precedence.

### 11.2 Retention Merge Rules

Retention is nuanced because both too-short and too-long retention can be non-compliant:

- **Audit logs:** The longest duration wins (regulatory requirements typically mandate minimum retention periods). Enterprise: `365d`, User: `90d` -> effective: `365d`.
- **PII mappings and deanonymisation window:** The shortest duration wins (data minimisation). Enterprise: `session`, User: `30d` -> effective: `session`.
- **Conversations and cache:** The shortest duration wins (data minimisation).

### 11.3 Merge Traceability

The effective policy retains provenance information for every field, recording which source contributed the winning value. This is available in the Layer 2/3 inspection view and in audit logs.

```json
{
  "field": "provider_restrictions.providers[openai].action",
  "effective_value": "deny",
  "source": "enterprise",
  "policy_id": "acme-enterprise-2026q1",
  "reason": "Most restrictive wins (deny > allow)"
}
```

### 11.4 Merge Conflicts and Warnings

When a lower-precedence policy attempts something that a higher-precedence policy forbids, loke:

1. Applies the more restrictive value (no override possible).
2. Logs the conflict at `info` level.
3. Reports the conflict to the user at Layer 1 visibility (one click deeper) with an explanation of why their setting was overridden.
4. Does not treat the conflict as an error — the lower-precedence policy is still valid; its conflicting fields are simply overridden.

---

## 12. Policy Versioning

### 12.1 Schema Versioning

The `policy_version` field tracks schema compatibility:

- **Major version** (e.g. `1.x` -> `2.0`): Breaking changes. New fields are required, field semantics changed, fields removed. loke will reject policies with an unsupported major version.
- **Minor version** (e.g. `1.0` -> `1.1`): Additive changes. New optional fields, new enum values. loke will accept policies with a minor version higher than it understands (unknown fields are ignored with a warning).

### 12.2 Policy Instance Versioning

Each policy document carries its own identity via `metadata.id` and `metadata.updated`. The audit trail records the exact policy state active at the time of each auditable event:

```
Audit entry:
  timestamp: 2026-03-20T14:30:00Z
  event: prompt_sent_to_cloud
  active_policies:
    enterprise: { id: "acme-enterprise-2026q1", updated: "2026-03-20T14:30:00Z" }
    team: { id: "alpha-team-policy", updated: "2026-02-01T00:00:00Z" }
    user: { id: "user-default", updated: "2026-03-15T09:00:00Z" }
  effective_policy_hash: "sha256:a1b2c3d4..."
```

The `effective_policy_hash` is a SHA-256 hash of the merged effective policy, providing a tamper-evident record. If the same hash appears across multiple audit entries, the same effective policy was in force.

### 12.3 Policy History

loke maintains a local history of all policy versions it has loaded:

- Previous versions are retained for the audit log retention period.
- Users can inspect what policy was active at any historical point.
- Enterprise policies fetched from URLs are cached locally; the cache includes all previously fetched versions.

---

## 13. Hot-Reload Semantics

Policies are reloaded without restarting loke. This applies to all three sources.

### 13.1 Reload Triggers

| Source | Trigger | Mechanism |
|--------|---------|-----------|
| Enterprise (URL) | Timer-based | Re-fetched at the configured `refresh_interval`. Also re-fetched on network reconnection. |
| Enterprise (MDM) | File change | Filesystem watcher on the managed path. |
| Team (file) | File change | Filesystem watcher. |
| User (file) | File change | Filesystem watcher. |
| Manual | User action | User triggers reload via UI or `loke policy reload` CLI command. |

### 13.2 Reload Process

1. **Detect change.** Filesystem watcher or timer fires.
2. **Load new policy.** Parse the YAML file. If the source is a URL, fetch and parse.
3. **Validate.** Run full validation (section 14). If validation fails, the new policy is rejected and the previous version remains in effect.
4. **Merge.** Re-run the merge algorithm with the new policy replacing the old one from that source.
5. **Diff.** Compare the new effective policy to the previous effective policy. Record the diff.
6. **Apply.** The new effective policy takes effect immediately.
7. **Notify.** If the diff is non-empty, notify the user at the appropriate visibility level:
   - Changes that tighten restrictions: advisory-level notification.
   - Changes that loosen restrictions: info-level (logged but not surfaced unless user checks).
   - Changes that block something previously allowed: warning-level notification.
8. **Audit.** Record the policy change event, including the old and new `effective_policy_hash`, the diff summary, and the source that changed.

### 13.3 In-Flight Request Handling

Policy changes apply to new requests only. Requests already in the pipeline when a policy change occurs complete under the policy that was active when they entered the pipeline. This prevents inconsistent states where a request was approved under one policy but audited under another.

### 13.4 Failure Handling

| Failure | Behaviour |
|---------|-----------|
| Enterprise URL unreachable on startup | If `required: true`, loke refuses to start and shows a clear error. If `required: false`, loke starts without the enterprise policy and retries on a backoff schedule. |
| Enterprise URL unreachable on refresh | Previous enterprise policy remains in effect. Warning logged. Retries on exponential backoff (max 5 minutes). |
| Malformed YAML | Rejected. Previous policy remains. Error details logged and shown to user. |
| Schema validation failure | Rejected. Previous policy remains. Specific validation errors reported. |
| File deleted | If the source is `required`, this is treated as an error. Otherwise, the policy from that source is removed and the effective policy is re-merged without it. |

---

## 14. Validation

All policies are validated on load, on reload, and can be validated offline via `loke policy validate <file>`.

### 14.1 Validation Rules

Validation is performed in order. If a rule fails, the error is collected and validation continues (all errors are reported, not just the first).

| Rule | Severity | Description |
|------|----------|-------------|
| YAML syntax | Error | File must be valid YAML. |
| `policy_version` present | Error | Required field. |
| `policy_version` supported | Error | Major version must be supported by this build of loke. |
| `metadata.name` present | Error | Required field. |
| `metadata.id` present | Error | Required field. |
| `metadata.id` format | Error | Must match `^[a-z0-9][a-z0-9._-]{0,127}$`. |
| Classification level IDs unique | Error | No duplicate `id` values in `data_classification.levels`. |
| Classification level references valid | Error | Any field referencing a classification level must use a defined level ID. |
| Provider IDs non-empty | Error | `providers[].id` cannot be empty. |
| Threshold ordering | Error | `review_threshold` <= `pii_detection_threshold` <= `auto_anonymise_threshold`. |
| Thresholds in range | Error | All threshold values must be in [0.0, 1.0]. |
| Budget amounts non-negative | Error | All budget amounts must be >= 0. |
| Budget hierarchy consistent | Warning | Daily budget should not exceed weekly; weekly should not exceed monthly. |
| Duration strings valid | Error | Must match the duration format specified in section 9.2. |
| Size strings valid | Error | Must match `<integer>(MB\|GB\|TB)`. |
| Anonymisation layers valid | Error | Layer IDs must be from the set: `regex`, `nlp`, `slm_ner`, `presidio`. |
| Entity override actions valid | Error | Must be one of: `redact`, `anonymise`, `hash`, `mask`. |
| Glob patterns valid | Warning | Provider and MCP server patterns must be valid glob syntax. |
| Unknown fields | Warning | Fields not defined in this specification are flagged but do not cause rejection (forward compatibility). |
| Circular references | Error | No field may reference itself or create a reference cycle. |

### 14.2 Validation Output

Validation produces a structured report:

```yaml
validation_result:
  valid: false
  errors:
    - path: "sensitivity_thresholds.pii_detection_threshold"
      message: "Value 1.5 is out of range [0.0, 1.0]"
      rule: "thresholds_in_range"
    - path: "provider_restrictions.providers[2].max_classification"
      message: "Classification level 'secret' is not defined. Defined levels: public, internal, confidential, restricted, prohibited"
      rule: "classification_level_references_valid"
  warnings:
    - path: "budget_limits.global"
      message: "Daily budget ($100.00) exceeds weekly budget ($50.00)"
      rule: "budget_hierarchy_consistent"
    - path: "custom_field"
      message: "Unknown field 'custom_field' at document root. This field will be ignored."
      rule: "unknown_fields"
  info:
    policy_version: "1.0"
    metadata_id: "acme-enterprise-2026q1"
    sections_defined: ["data_classification", "provider_restrictions", "budget_limits"]
```

### 14.3 CLI Validation

```bash
# Validate a single policy file
loke policy validate enterprise-policy.yaml

# Validate and show the effective merged policy
loke policy merge enterprise.yaml team.yaml user.yaml

# Show the effective policy currently in use
loke policy show

# Show provenance for a specific field
loke policy explain provider_restrictions.providers.openai.action
```

---

## 15. Preset Policies

loke ships with preset policies that implement common regulatory frameworks. These are starting points — organisations should review and customise them for their specific obligations.

| Preset | File | Description |
|--------|------|-------------|
| EU GDPR | `eu-gdpr.yaml` | European General Data Protection Regulation compliance |
| AU Privacy Act | `au-privacy-act.yaml` | Australian Privacy Act 1988 compliance |
| HIPAA | `hipaa.yaml` | US Health Insurance Portability and Accountability Act compliance |
| Minimal | `minimal.yaml` | Development and testing — minimal restrictions |

Presets are loaded by referencing them in the policy source configuration:

```yaml
policy_sources:
  team:
    type: preset
    name: "eu-gdpr"                    # Loads the bundled eu-gdpr.yaml
```

Or they can be used as a base that is extended by a custom policy file. The preset is loaded first, then the custom file is merged on top of it at the same precedence level.

---

## 16. Security Considerations

### 16.1 Policy File Integrity

- Enterprise policies fetched via URL should be served over HTTPS. loke rejects HTTP URLs for enterprise policy sources unless explicitly overridden with `allow_insecure: true` (which generates a persistent warning).
- MDM-delivered policies inherit the integrity guarantees of the MDM platform.
- Local policy files are protected by filesystem permissions. loke warns if a policy file is world-writable.

### 16.2 Policy Tampering

- The audit trail records policy hashes, making post-hoc tampering detectable.
- Enterprise policies cannot be overridden by user or team policies in the direction of less restriction (see merge semantics).
- The effective policy hash is computed from the merged result, so any change to any input policy produces a different hash.

### 16.3 Credential Handling

- Policy files must never contain secrets (API keys, tokens, passwords).
- Authentication for enterprise URL fetch uses environment variables or OS keychain references, not inline credentials.
- Validation flags any string that matches common API key patterns within a policy file as a warning.

---

## 17. Example: Complete Policy File

The following example demonstrates all sections in a single policy file:

```yaml
policy_version: "1.0"
metadata:
  name: "Example Complete Policy"
  id: "example-complete-v1"
  description: "Demonstrates all policy sections"
  author: "loke documentation"
  created: "2026-04-01T00:00:00Z"
  updated: "2026-04-01T00:00:00Z"

data_classification:
  levels:
    - id: public
      name: "Public"
    - id: internal
      name: "Internal"
    - id: confidential
      name: "Confidential"
    - id: restricted
      name: "Restricted"
    - id: prohibited
      name: "Prohibited"
  default_level: confidential
  rules:
    - pattern: email_address
      level: restricted
    - pattern: credit_card
      level: prohibited

provider_restrictions:
  default_action: deny
  providers:
    - id: anthropic
      action: allow
      max_classification: confidential
    - id: local
      action: allow
      max_classification: prohibited

mcp_servers:
  default_action: deny
  servers:
    - pattern: "filesystem"
      action: allow
      max_classification: restricted
    - pattern: "git"
      action: allow
      max_classification: confidential

sensitivity_thresholds:
  pii_detection_threshold: 0.7
  auto_anonymise_threshold: 0.9
  review_threshold: 0.5
  actions:
    restricted:
      require_anonymisation: true
      allow_cloud: true
      require_user_confirmation: true

budget_limits:
  currency: "USD"
  global:
    monthly: 50.00
  on_exceed:
    action: warn_and_block

retention:
  audit_logs:
    duration: "365d"
  pii_mappings:
    duration: "session"
    on_expiry: secure_delete
  deanonymisation_window:
    duration: "24h"

anonymisation:
  default_level: standard
  entity_overrides:
    credit_card:
      action: redact
    medical_record:
      action: redact
  allow_deanonymisation: true
```
