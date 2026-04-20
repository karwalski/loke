# In-App Feedback & Issue Reporting Specification

**Epic:** A5 — In-App Feedback & Issue Reporting
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke treats feedback as a first-class feature. Every LLM response, routing decision, and anonymisation result already has thumbs-up/down rating (design principle 3). This specification extends that foundation with structured issue reporting, AI-assisted report drafting, and version checking — the mechanisms through which users escalate beyond a thumbs-down into actionable problem reports, and through which they stay informed about available updates.

This specification defines:

- The issue report data model and form layout (browser and terminal modes)
- AI-assisted report drafting via the privacy pipeline
- Destination configuration for routing reports to APIs, email, or external trackers
- Version check and update notification flow
- Privacy safeguards for report content
- Integration with the existing thumbs-up/down feedback system

### 1.1 Design Alignment

This specification follows the loke design principles:

- **The user is the authority.** Reports are stored locally until the user explicitly chooses to send them. No telemetry, no silent uploads, no "phone home" behaviour.
- **Feedback is a first-class feature.** This specification builds on the thumbs-up/down system described in the design principles. A thumbs-down with comment can be promoted to a full issue report. The feedback loop is continuous, not a separate workflow.
- **We don't know what this product should look like yet.** The issue reporting system exists because the MVP is a learning tool. Every report teaches us something. The system is designed to maximise signal, not minimise friction — though it does both where possible.
- **Privacy is the foundation.** Issue reports may contain sensitive context (screenshots of anonymised prompts, reproduction steps referencing real data, system state). Reports are treated as potentially sensitive data and processed through the privacy pipeline before any external transmission.
- **Complexity is available, not imposed.** Layer 0 is a quick description and send. Layer 1 adds structured fields. Layer 2 adds AI-assisted drafting. Users choose their depth.

---

## 2. Issue Report Data Model

### 2.1 TypeScript Interface

```typescript
/**
 * Classification of the issue being reported.
 */
type IssueType = 'bug' | 'enhancement' | 'question' | 'feedback';

/**
 * Where the report will be sent when the user explicitly submits it.
 */
type DestinationType = 'api' | 'email' | 'github' | 'linear' | 'local_only';

/**
 * Current lifecycle state of the report.
 */
type ReportStatus = 'draft' | 'submitted' | 'acknowledged' | 'resolved';

/**
 * A screenshot or file attached to the report.
 */
interface ReportAttachment {
  /** Unique identifier for this attachment. */
  id: string;

  /** Original filename as provided by the user. */
  filename: string;

  /** MIME type (e.g. 'image/png', 'text/plain'). */
  mimeType: string;

  /** File size in bytes. */
  sizeBytes: number;

  /** Base64-encoded content, stored locally. */
  contentBase64: string;

  /**
   * Whether this attachment has been processed through the privacy
   * pipeline to redact visible PII (e.g. screenshot OCR + redaction).
   */
  privacyProcessed: boolean;

  /** ISO 8601 timestamp of when the attachment was added. */
  addedAt: string;
}

/**
 * Snapshot of the application environment at report creation time.
 * Collected automatically — no user action required.
 */
interface EnvironmentSnapshot {
  /** loke version string (e.g. '0.4.2'). */
  lokeVersion: string;

  /** Operating system and version (e.g. 'macOS 15.3'). */
  os: string;

  /** CPU architecture (e.g. 'arm64', 'x64'). */
  arch: string;

  /** Active mode when the report was created. */
  mode: 'browser' | 'terminal' | 'proxy';

  /** Electron version, if running in browser mode. */
  electronVersion?: string;

  /** Node.js version. */
  nodeVersion: string;

  /** Whether Ollama is running and reachable. */
  ollamaAvailable: boolean;

  /** Names of configured LLM providers. */
  configuredProviders: string[];

  /** Name of the active policy, if any. */
  activePolicy?: string;

  /** Locale in use (e.g. 'en-AU'). */
  locale: string;
}

/**
 * Record of AI-assisted drafting, if the user opted in.
 */
interface AiDraftingRecord {
  /** The user's original draft before AI refinement. */
  originalDraft: string;

  /** The AI-refined version presented to the user. */
  refinedDraft: string;

  /** Whether the user accepted the refined version. */
  accepted: boolean;

  /** The model used for drafting assistance. */
  model: string;

  /** Whether the draft was processed through the privacy pipeline. */
  privacyPipelineApplied: boolean;

  /** ISO 8601 timestamp. */
  timestamp: string;
}

/**
 * A complete issue report. Stored locally in SQLite.
 * Only transmitted externally when the user explicitly submits.
 */
interface IssueReport {
  /** UUID v4 — unique identifier for this report. */
  id: string;

  /** Classification of the issue. */
  type: IssueType;

  /** Short summary (max 200 characters). */
  title: string;

  /** Detailed description of the issue or feedback. */
  description: string;

  /** Steps to reproduce (for bugs). Optional. */
  reproductionSteps?: string;

  /** What the user expected to happen. Optional. */
  expectedBehaviour?: string;

  /** What actually happened. Optional. */
  actualBehaviour?: string;

  /** Attached screenshots or files. */
  attachments: ReportAttachment[];

  /** Automatically captured environment snapshot. */
  environment: EnvironmentSnapshot;

  /** AI drafting record, if the user used AI assistance. */
  aiDrafting?: AiDraftingRecord;

  /**
   * ID of the feedback item (thumbs-down) that triggered this report,
   * if the report was promoted from inline feedback.
   */
  sourceFeedbackId?: string;

  /**
   * ID of the specific pipeline execution, prompt, or interaction
   * that this report relates to. Allows linking to audit trail.
   */
  relatedInteractionId?: string;

  /** Where this report was sent, if submitted. */
  destination?: DestinationType;

  /** External reference (e.g. GitHub issue URL, Linear ticket ID). */
  externalReference?: string;

  /** Current lifecycle state. */
  status: ReportStatus;

  /** ISO 8601 timestamp of creation. */
  createdAt: string;

  /** ISO 8601 timestamp of last modification. */
  updatedAt: string;

  /** ISO 8601 timestamp of submission, if submitted. */
  submittedAt?: string;
}
```

### 2.2 Storage

Reports are stored in the local SQLite database (F6.1) in an `issue_reports` table. Attachments are stored as BLOBs in a related `report_attachments` table.

Reports are never transmitted automatically. They remain local until the user explicitly triggers submission. Draft reports persist across sessions — a user can start a report, close loke, and finish it later.

### 2.3 Retention

- Draft reports older than 90 days are flagged for cleanup (user is prompted, not auto-deleted).
- Submitted reports are retained indefinitely for the user's own records.
- Attachments follow the same retention as their parent report.

---

## 3. Issue Reporting Form

### 3.1 Access Points

The issue reporting form is accessible from every view in loke:

| Access point | Mechanism |
|---|---|
| **Global menu** | "Report an issue" item in the Help menu (browser mode) |
| **Keyboard shortcut** | `Cmd+Shift+I` (macOS) / `Ctrl+Shift+I` (other) |
| **Thumbs-down promotion** | "Report an issue" link in the thumbs-down comment popover |
| **Settings page** | "Report an issue" button in the About section |
| **CLI command** | `loke report` (terminal mode) |
| **Error toast** | "Report this issue" link on error notifications |

When accessed from a thumbs-down or error context, the form is pre-populated with available context (the interaction ID, the error message, the feedback comment).

### 3.2 Browser Mode Layout

The form appears as a **slide-over panel** from the right edge of the window (not a modal — the user can still see the context behind it). The panel is 480px wide on desktop, full-width on narrow viewports.

```
┌──────────────────────────────────────────┐
│  Report an Issue                    [×]  │
├──────────────────────────────────────────┤
│                                          │
│  Type: [Bug ▼]                           │
│                                          │
│  Title                                   │
│  ┌──────────────────────────────────────┐│
│  │ Brief summary of the issue          ││
│  └──────────────────────────────────────┘│
│                                          │
│  Description                             │
│  ┌──────────────────────────────────────┐│
│  │                                      ││
│  │ What happened?                       ││
│  │                                      ││
│  └──────────────────────────────────────┘│
│                                          │
│  ▸ Reproduction steps (optional)         │
│  ▸ Expected behaviour (optional)         │
│  ▸ Actual behaviour (optional)           │
│                                          │
│  Screenshots                             │
│  [+ Add screenshot]  [📋 Paste]          │
│  ┌──────┐ ┌──────┐                      │
│  │thumb1│ │thumb2│                      │
│  └──────┘ └──────┘                      │
│                                          │
│  ──────────────────────────────────────  │
│  Environment: loke 0.4.2 · macOS 15.3   │
│  Mode: browser · Policy: acme-corp       │
│  ──────────────────────────────────────  │
│                                          │
│  [✨ Refine with AI]                     │
│                                          │
│  [Save draft]    [Submit report →]       │
│                                          │
└──────────────────────────────────────────┘
```

#### 3.2.1 Field Details

| Field | Required | Details |
|---|---|---|
| **Type** | Yes | Dropdown: Bug, Enhancement, Question, Feedback. Default: Bug. |
| **Title** | Yes | Single-line text. Max 200 characters. Placeholder: "Brief summary of the issue". |
| **Description** | Yes | Multi-line text. No length limit. Placeholder: "What happened? Include as much detail as you'd like." Supports Markdown. |
| **Reproduction steps** | No | Collapsible section. Multi-line text. Placeholder: "1. Open loke\n2. Navigate to...\n3. ..." |
| **Expected behaviour** | No | Collapsible section. Multi-line text. Placeholder: "What did you expect to happen?" |
| **Actual behaviour** | No | Collapsible section. Multi-line text. Placeholder: "What happened instead?" |
| **Screenshots** | No | File picker (images only) or clipboard paste. Thumbnails with remove button. Max 5 attachments, max 10MB each. |
| **Environment** | Auto | Read-only display of the environment snapshot. Collapsible for full details. |

Optional sections (reproduction steps, expected behaviour, actual behaviour) are collapsed by default. When the type is "Bug", they expand automatically with a subtle prompt: "Bug reports are most helpful with reproduction steps."

#### 3.2.2 Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Cmd+Enter` | Submit report |
| `Cmd+S` | Save draft |
| `Escape` | Close panel (with confirmation if unsaved changes) |
| `Cmd+Shift+A` | Add screenshot |
| `Cmd+Shift+R` | Refine with AI |

### 3.3 Terminal Mode Layout

In terminal mode, `loke report` launches an interactive form using the structured prompt pattern (similar to `npm init`):

```
$ loke report

╔══════════════════════════════════════════════════════════╗
║  REPORT AN ISSUE                                         ║
║  loke 0.4.2 · macOS 15.3 · terminal mode                ║
╚══════════════════════════════════════════════════════════╝

Type? [b]ug / [e]nhancement / [q]uestion / [f]eedback: b

Title: Anonymisation misses email in code block

Description (Ctrl+D to finish, empty line for paragraph break):
When I include an email address inside a fenced code block in my
prompt, the regex detector doesn't catch it. The NER layer also
misses it because it treats code blocks as non-prose.

Reproduction steps (optional, Ctrl+D to finish, Enter to skip):
1. Start loke in terminal mode
2. Run: loke ask "Check this config: user_email=john@acme.com"
3. Observe the pre-send display — email is not anonymised

Expected behaviour (optional, Enter to skip):
The email should be replaced with [EMAIL_1] in the transformed
prompt.

Actual behaviour (optional, Enter to skip):
The email passes through unchanged.

Attach screenshot? (path or Enter to skip):

──────────────────────────────────────────────────────────

[r]efine with AI  [s]ave draft  [S]ubmit  [c]ancel
```

If the user provides a file path for a screenshot, the file is read and attached. The path can be absolute or relative to the current directory.

### 3.4 Pre-Population from Context

When a report is triggered from a specific context, fields are pre-populated:

| Source | Pre-populated fields |
|---|---|
| **Thumbs-down on LLM response** | `relatedInteractionId`, type = "bug", description = thumbs-down comment |
| **Thumbs-down on anonymisation** | `relatedInteractionId`, type = "bug", title = "Anonymisation issue" |
| **Thumbs-down on routing** | `relatedInteractionId`, type = "feedback", title = "Routing feedback" |
| **Error toast** | `relatedInteractionId`, type = "bug", title = error summary, description = error message + stack trace (redacted) |
| **CLI with context** | `loke report --from-interaction <id>` pre-populates the interaction ID and pulls context from the audit trail |

---

## 4. AI-Assisted Report Drafting

### 4.1 Purpose

Users often know something is wrong but struggle to articulate it clearly. The AI-assisted drafting feature helps refine a rough description into a structured, actionable report — using the same privacy pipeline that protects all other LLM interactions.

### 4.2 Flow

```
┌──────────────┐
│  User writes  │
│  rough draft  │
└──────┬───────┘
       │
┌──────▼───────┐
│  User clicks  │
│ "Refine with  │
│     AI"       │
└──────┬───────┘
       │
┌──────▼───────────────────────┐
│  Privacy pipeline processes   │
│  the draft text:              │
│  - Anonymise PII in the      │
│    description, repro steps,  │
│    and any pasted content     │
│  - Replace real names, emails │
│    paths, IPs with placeholders│
└──────┬───────────────────────┘
       │
┌──────▼───────────────────────┐
│  Anonymised draft sent to     │
│  LLM (via normal routing)     │
│  with refinement prompt       │
└──────┬───────────────────────┘
       │
┌──────▼───────────────────────┐
│  LLM response rehydrated      │
│  (placeholders → originals)   │
└──────┬───────────────────────┘
       │
┌──────▼───────────────────────┐
│  User sees original and       │
│  refined side by side         │
│                               │
│  [Accept] [Edit] [Discard]    │
└──────────────────────────────┘
```

### 4.3 Privacy Pipeline Integration

The report draft is treated as any other outbound prompt. This is important because reports often contain exactly the kind of sensitive context that the privacy pipeline is designed to handle:

- A user describing a bug might paste the prompt they were working on, which contains client names
- Reproduction steps might reference internal systems, hostnames, or file paths
- Screenshots might show anonymised data alongside UI elements

The pipeline processes the draft text through all configured layers (regex, NER, SLM-based detection) before it reaches any external LLM. Rehydration restores the original terms in the refined output so the user sees their real context, not placeholders.

### 4.4 Refinement Prompt

The system prompt for AI-assisted drafting instructs the model to:

1. Restructure the description for clarity without changing the meaning
2. Identify missing information and suggest additions (e.g. "Could you add what you expected to happen?")
3. Separate symptoms from causes where possible
4. Format the report using Markdown for readability
5. Preserve all technical details exactly as provided
6. Never fabricate information — only restructure what the user wrote

The refinement prompt is a versioned template (F3.7) stored alongside other loke prompt templates.

### 4.5 Opt-In and Fallback

AI-assisted drafting is strictly opt-in:

- The "Refine with AI" button is clearly labelled and never activates automatically
- If no LLM provider is configured, the button is hidden
- If only local models are available, the button is shown with a note: "Uses local model — no data leaves your device"
- If the privacy pipeline blocks the draft (e.g. it contains RESTRICTED-level data and the policy prevents sending to the selected model), the user is informed and offered the option to proceed with a local model or skip AI assistance
- The form is fully functional without AI assistance — all fields, submission, and destination routing work identically

### 4.6 Terminal Mode AI Assistance

In terminal mode, the `[r]efine with AI` option at the action prompt sends the current draft through the pipeline and displays the result:

```
Refining with AI (via local qwen-9b)...

── Original ──────────────────────────────────────────
The anonymisation thing doesn't work with code blocks.
Emails in backticks go through.

── Refined ───────────────────────────────────────────
**Summary:** Email addresses inside fenced code blocks
are not detected by the anonymisation pipeline.

**Details:** When an email address appears within a
Markdown fenced code block (triple backticks), neither
the regex detector nor the NER layer identifies it as
PII. The email is sent to the provider unchanged.

**Suggested additions:**
- Which detection layers were active?
- Was a custom policy in effect?

[a]ccept  [e]dit  [d]iscard:
```

---

## 5. Destination Configuration

### 5.1 Configuration Format

Report destinations are configured in the loke application settings. Multiple destinations can be configured; the user selects which one to use at submission time, or a default is applied.

```yaml
# In loke application config (settings.yaml or equivalent)
feedback:
  destinations:
    # API endpoint — POST JSON to a URL
    - name: "Internal tracker"
      type: api
      url: "https://feedback.acme.com/api/v1/issues"
      auth:
        type: bearer
        token_env: "LOKE_FEEDBACK_TOKEN"
      default: true

    # Email — compose and send via system mail or SMTP
    - name: "Email to team"
      type: email
      to: "loke-feedback@acme.com"
      subject_prefix: "[loke]"
      smtp:                              # Optional — uses system mail if omitted
        host: "smtp.acme.com"
        port: 587
        auth_env: "LOKE_SMTP_AUTH"       # username:password from env

    # GitHub Issues — create issue via GitHub API
    - name: "GitHub Issues"
      type: github
      owner: "karwalski"
      repo: "loke"
      labels:
        - "user-report"
        - "triage"
      token_env: "GITHUB_TOKEN"

    # Linear — create issue via Linear API
    - name: "Linear"
      type: linear
      team_id: "LOKE"
      project_id: "feedback"
      token_env: "LINEAR_API_KEY"

    # Local only — store but never transmit
    - name: "Save locally"
      type: local_only

  # Default destination when user does not choose
  default_destination: "Internal tracker"

  # Whether to show destination picker on submit
  show_destination_picker: true

  # Maximum attachment size per file (bytes)
  max_attachment_size: 10485760          # 10 MB

  # Maximum number of attachments per report
  max_attachments: 5
```

### 5.2 Destination Behaviour

| Destination | Submission behaviour |
|---|---|
| **API** | POST the report as JSON to the configured URL. Body follows the `IssueReport` interface (attachments as base64). Expects 2xx response. Retries on 5xx with exponential backoff (via P5.3 base HTTP client). |
| **Email** | Compose an email with the report title as subject, description + fields as body (Markdown rendered to plain text), attachments as MIME attachments. Send via configured SMTP or delegate to the system mail client. |
| **GitHub** | Create an issue via the GitHub API (`POST /repos/{owner}/{repo}/issues`). Title maps to issue title. Description, reproduction steps, expected/actual behaviour, and environment are formatted as Markdown in the issue body. Attachments are uploaded separately and linked. Labels from config are applied. |
| **Linear** | Create an issue via the Linear GraphQL API. Title maps to issue title. Description fields are formatted as Markdown in the issue description. Team and project from config. |
| **Local only** | Report is saved locally in its current state. No network request is made. Status remains `draft`. |

### 5.3 Submission Flow

1. User clicks "Submit report" (or presses `Cmd+Enter` / selects `[S]ubmit`)
2. If `show_destination_picker` is true and multiple destinations are configured, a picker appears
3. If the selected destination is not `local_only`, a confirmation is shown: "This report will be sent to [destination name]. It may contain information about your environment and usage. Continue?"
4. The report is submitted to the destination
5. On success: status updates to `submitted`, the `externalReference` is populated (e.g. GitHub issue URL), and the user sees a confirmation with a link to the external reference if available
6. On failure: the user is informed, the report remains in `draft` status, and they can retry or save locally

### 5.4 Privacy Before Submission

Before a report is sent to any external destination (not `local_only`), the user is shown a summary of what will be transmitted:

- The full text of all fields
- The list of attachments with sizes
- The environment snapshot
- A warning if any field appears to contain PII that was not processed through the pipeline

This follows the guardrail pattern: inform, explain, offer alternatives, allow override.

---

## 6. Version Check and Update Notification

### 6.1 Version Check Flow

loke checks for available updates by querying a configurable endpoint. No telemetry is sent — the check is a simple GET request.

```
┌──────────────────┐
│  loke starts or   │
│  daily timer fires│
│  or user triggers │
│  manual check     │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  GET endpoint     │──── network error ──→ silently skip, retry next cycle
│  /releases/latest │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Compare remote   │
│  version with     │
│  local version    │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ newer?  │
    └────┬────┘
    no   │   yes
    │    │
    │  ┌─▼──────────────┐
    │  │ Store result    │
    │  │ locally, show   │
    │  │ notification    │
    │  └────────────────┘
    │
  (done)
```

### 6.2 Endpoint Configuration

```yaml
# In loke application config
updates:
  # URL to check for the latest version
  endpoint: "https://api.github.com/repos/karwalski/loke/releases/latest"

  # How often to check (seconds). Default: 86400 (daily)
  check_interval: 86400

  # Whether to check automatically on startup
  check_on_startup: true

  # Whether to show a notification when an update is available
  show_notification: true

  # Custom headers for the request (e.g. for private repos)
  headers:
    Accept: "application/vnd.github.v3+json"
```

### 6.3 Response Schema

The version check expects a JSON response conforming to this schema. The default configuration targets the GitHub Releases API, but any endpoint returning this shape is compatible.

```typescript
/**
 * Expected shape of the version check response.
 * Compatible with GitHub Releases API (/repos/{owner}/{repo}/releases/latest).
 */
interface VersionCheckResponse {
  /** The version tag (e.g. 'v0.5.0'). Semver with optional 'v' prefix. */
  tag_name: string;

  /** Human-readable release name (e.g. 'loke 0.5.0 — Pipeline Improvements'). */
  name: string;

  /** Release notes in Markdown. */
  body: string;

  /** ISO 8601 publication date. */
  published_at: string;

  /** URL to the release page for manual download. */
  html_url: string;

  /** Whether this is a pre-release. Pre-releases are shown only if the user opts in. */
  prerelease: boolean;

  /** Download assets. loke selects the appropriate asset for the current platform. */
  assets: Array<{
    name: string;
    browser_download_url: string;
    size: number;
    content_type: string;
  }>;
}
```

If the endpoint returns a different shape (e.g. a custom update server), a response mapper can be configured:

```yaml
updates:
  endpoint: "https://updates.example.com/loke/latest"
  response_mapping:
    version_field: "version"            # JSONPath to version string
    release_url_field: "download_url"   # JSONPath to release page URL
    release_notes_field: "changelog"    # JSONPath to release notes
    published_field: "released_at"      # JSONPath to publication date
```

### 6.4 Version Comparison

Versions are compared using semver. The `tag_name` is stripped of a leading `v` if present. The check result is one of:

| Result | Condition | User-visible behaviour |
|---|---|---|
| **Up to date** | Remote version equals or is older than local | No notification. Settings page shows "Up to date" with last check timestamp. |
| **Update available** | Remote version is newer than local (ignoring pre-releases unless opted in) | Notification badge on settings. Toast on first detection. Settings page shows version, release notes, and download link. |
| **Pre-release available** | Remote pre-release is newer, and user has opted in to pre-release notifications | Same as "Update available" but labelled as pre-release. |
| **Check failed** | Network error, invalid response, or timeout | No notification. Settings page shows "Unable to check for updates" with last successful check timestamp. Retries on next cycle. |

### 6.5 Browser Mode UI

Update status is displayed in the Settings > About section:

```
┌──────────────────────────────────────────────────────┐
│  About loke                                           │
│                                                       │
│  Version: 0.4.2                                       │
│  License: Apache 2.0                                  │
│  Runtime: Electron 33.2 · Node 22.4 · macOS 15.3     │
│                                                       │
│  ── Updates ──────────────────────────────────────    │
│                                                       │
│  ✦ Update available: 0.5.0                            │
│  Released 2 days ago                                  │
│                                                       │
│  Pipeline Improvements                                │
│  • Improved code block PII detection                  │
│  • 15% faster anonymisation pipeline                  │
│  • New Linear integration for feedback                │
│                                                       │
│  [View release page →]    [Check now]                 │
│                                                       │
│  ☐ Include pre-release versions                       │
│  Last checked: 3 hours ago                            │
│                                                       │
└──────────────────────────────────────────────────────┘
```

When an update is available, a subtle badge appears on the Settings navigation item (a dot, not a number — this is informational, not urgent). A toast notification is shown once per detected version: "loke 0.5.0 is available. View in Settings."

There is no auto-update mechanism. The "View release page" link opens the release URL in the system browser, where the user can download the update manually. This is deliberate — auto-update introduces a remote code execution vector that conflicts with loke's local-first, user-is-the-authority model.

### 6.6 Terminal Mode UI

In terminal mode, the version check result is shown on startup (if an update is available) and via `loke version`:

```
$ loke version
loke 0.4.2 (Apache 2.0)
Runtime: Node 22.4 · macOS 15.3 arm64
Ollama: running (3 models loaded)

Update available: 0.5.0 (released 2 days ago)
  https://github.com/karwalski/loke/releases/tag/v0.5.0
```

On startup, if an update is available and the last notification was more than 24 hours ago:

```
$ loke ask "Summarise this document"
[loke] Update available: 0.5.0 — run `loke version` for details
...
```

The startup notice is a single line to stderr, non-intrusive. It does not interrupt the command.

### 6.7 Manual Check

- **Browser mode:** "Check now" button in Settings > About
- **Terminal mode:** `loke update --check` (checks and displays result; does not download or install anything)

---

## 7. Privacy Considerations

### 7.1 Reports Are Local by Default

All issue reports are stored locally in the SQLite database. No report is transmitted to any external service unless the user explicitly clicks "Submit" and confirms the destination. This is the fundamental privacy guarantee.

### 7.2 Report Content May Contain PII

Issue reports are inherently likely to contain sensitive information:

- Users describe real problems with real data
- Reproduction steps may reference client names, internal systems, or file paths
- Screenshots may capture sensitive UI content
- Error messages may contain file paths, usernames, or API keys

loke does not automatically strip PII from reports — doing so might remove the context needed to diagnose the issue. Instead:

1. **Before submission**, the report content is scanned by the privacy pipeline and the user is shown any detected PII entities with the option to redact them
2. **The user decides** whether to redact, modify, or submit as-is
3. **The submission confirmation** clearly states what will be sent and where
4. **The audit trail** records the submission decision (report ID, destination, timestamp — not the report content)

### 7.3 AI-Assisted Drafting Privacy

When the user opts into AI-assisted drafting:

- The draft text passes through the full privacy pipeline before reaching any external LLM
- PII is anonymised in transit and rehydrated in the response
- The pipeline audit trail records the AI drafting interaction
- If the active policy blocks the data's sensitivity level from leaving the device, the user is informed and offered a local-model alternative
- The `AiDraftingRecord` is stored locally for the user's own reference

### 7.4 Version Check Privacy

The version check is a simple HTTP GET with no request body. loke does not send:

- The current version (the endpoint returns the latest; loke compares locally)
- Any telemetry, usage data, or device identifiers
- Any cookies or tracking headers

The only information visible to the endpoint operator is the IP address of the requesting machine (unavoidable for any HTTP request) and the request path. If this is unacceptable (e.g. in a high-security environment), the version check can be disabled entirely:

```yaml
updates:
  check_on_startup: false
  check_interval: 0                    # 0 disables periodic checks
```

### 7.5 Screenshot Privacy

Screenshots may contain visible PII (text on screen, names in tabs, data in tables). When a screenshot is attached:

1. The attachment is stored locally as-is
2. Before external submission, loke offers OCR-based PII detection on the image (using a local model if available)
3. Detected PII regions are highlighted and the user can choose to redact them (blur/black-box) before submission
4. If no local OCR model is available, the user is warned: "Screenshots may contain visible personal information. Review before submitting."

This is advisory — the user makes the final decision.

---

## 8. Integration with Thumbs-Up/Down Feedback

### 8.1 The Feedback Continuum

The design principles establish thumbs-up/down as a lightweight signal on every interaction. Issue reporting extends this into a continuum:

```
Signal only          │  Signal + context       │  Structured report
─────────────────────┼─────────────────────────┼────────────────────
👍 Thumbs up          │                         │
                     │                         │
👎 Thumbs down        │  👎 + "email missed"     │  Full issue report
(one tap)            │  (optional comment)     │  (form with fields,
                     │                         │   screenshots, AI
                     │                         │   drafting)
```

### 8.2 Promotion Flow

A thumbs-down with a comment can be promoted to a full issue report:

1. User gives a thumbs-down on an anonymisation result
2. A comment popover appears: "What went wrong?" with a text input
3. User types: "Email in code block wasn't caught"
4. Below the send button, a link appears: "Report as issue"
5. Clicking opens the issue reporting form pre-populated with:
   - `type`: bug
   - `description`: the comment text
   - `relatedInteractionId`: the interaction that received the thumbs-down
   - `title`: auto-generated from the comment (first 200 chars)
   - `sourceFeedbackId`: the feedback item's ID

The original thumbs-down is preserved as a standalone feedback signal regardless of whether the user completes the issue report.

### 8.3 Feedback Aggregation

Feedback signals (thumbs-up/down) and issue reports feed into a local analytics view:

- **Thumbs-down clusters:** Groups of thumbs-down on the same surface (e.g. anonymisation) are highlighted as potential systemic issues
- **Unresolved reports:** Draft and submitted reports are listed with their status
- **Feedback-to-report ratio:** Tracks how often thumbs-down escalates to a full report (a proxy for issue severity)

This view is local-only — it helps the user see their own feedback history and helps loke developers (when reports are submitted) prioritise issues.

---

## 9. Configuration

### 9.1 Full Configuration Reference

```yaml
# In loke application config (settings.yaml or equivalent)

feedback:
  # Report destinations (see Section 5.1 for full schema)
  destinations:
    - name: "GitHub Issues"
      type: github
      owner: "karwalski"
      repo: "loke"
      labels: ["user-report"]
      token_env: "GITHUB_TOKEN"

    - name: "Save locally"
      type: local_only

  default_destination: "GitHub Issues"
  show_destination_picker: true
  max_attachment_size: 10485760
  max_attachments: 5

  # AI-assisted drafting
  ai_drafting:
    enabled: true                        # Show the "Refine with AI" button
    prefer_local: true                   # Prefer local models for drafting
    model_override: null                 # Force a specific model (null = use router)

  # Thumbs-up/down configuration
  inline_feedback:
    enabled: true                        # Show thumbs on all interactions
    show_promotion_link: true            # Show "Report as issue" on thumbs-down
    surfaces:                            # Which surfaces show thumbs
      - llm_response
      - anonymisation_preview
      - routing_decision
      - warning
      - compression_result
      - cost_estimate

  # Draft retention
  draft_retention_days: 90               # Flag drafts for cleanup after N days

updates:
  endpoint: "https://api.github.com/repos/karwalski/loke/releases/latest"
  check_interval: 86400
  check_on_startup: true
  show_notification: true
  include_prereleases: false
  headers:
    Accept: "application/vnd.github.v3+json"
  response_mapping: null                 # null = use GitHub Releases API shape
```

### 9.2 CLI Flags

| Flag | Effect |
|---|---|
| `loke report` | Open the issue reporting form (terminal mode) |
| `loke report --type bug` | Pre-set the issue type |
| `loke report --from-interaction <id>` | Pre-populate from an audit trail interaction |
| `loke report --no-ai` | Skip AI-assisted drafting even if configured |
| `loke report --destination <name>` | Submit directly to the named destination |
| `loke report --local-only` | Save locally without submitting |
| `loke version` | Show version and update status |
| `loke update --check` | Check for updates and display result |

---

## 10. Accessibility

### 10.1 Browser Mode

- All form controls have associated labels and descriptions (X3.1)
- Tab order follows visual order: type, title, description, optional sections, screenshots, AI button, actions (X3.2)
- The slide-over panel traps focus when open and restores focus to the trigger element on close (X3.3)
- Screen reader announces panel open/close and form submission results (X3.4)
- Colour is not the sole indicator of issue type or status — each has an icon and text label (X3.5)
- The AI drafting comparison view announces "Original" and "Refined" sections to screen readers

### 10.2 Terminal Mode

- All prompts have clear labels and accept keyboard input
- The action menu uses single-character shortcuts with clear descriptions
- Output is structured with headings and separators for screen reader navigation
- No colour-only information — all status is also conveyed via text

---

## 11. Security Considerations

### 11.1 Destination Authentication

Credentials for external destinations (API tokens, SMTP passwords) are stored in environment variables, not in the configuration file. The configuration file references the environment variable name (`token_env`, `auth_env`), and loke reads the value at runtime.

For enhanced security, credentials can be stored in the OS keychain (F1.5) and referenced by keychain item name instead of environment variable.

### 11.2 Report Content in Transit

When a report is submitted to an external destination:

- API destinations use HTTPS (TLS 1.2+). HTTP endpoints are rejected unless explicitly allowed in configuration.
- Email destinations use STARTTLS when SMTP is configured.
- GitHub and Linear destinations use their respective HTTPS APIs.

### 11.3 Attachment Safety

Attachments are validated on addition:

- File type must be an allowed MIME type (images: PNG, JPEG, GIF, WebP; text: plain, CSV, JSON, YAML)
- File size must not exceed `max_attachment_size`
- Files are stored as base64 in the local database — they are not executed or rendered unsafely

### 11.4 Version Check Endpoint Trust

The version check endpoint is configurable, which means a misconfigured or compromised endpoint could serve false update information. Safeguards:

- loke never downloads or executes anything from the update endpoint — it only reads version metadata
- The "View release page" link is displayed to the user, who decides whether to follow it
- The link URL is shown in full (not behind a shortened URL) so the user can verify the domain

---

## 12. Future Considerations

These items are out of scope for the beta implementation but may be added based on user feedback:

- **Feedback digest:** Periodic summary of all thumbs-down and reports, surfaced in the dashboard
- **Report status tracking:** Bidirectional sync with external trackers so the user can see when their report is triaged, in progress, or resolved
- **Team feedback aggregation:** For enterprise deployments, aggregate anonymised feedback signals across a team to surface common issues
- **Automated reproduction:** Capture enough state (prompt, pipeline config, model versions) to auto-generate a reproduction script
- **Feedback-driven routing improvements:** Use thumbs-up/down signals on routing decisions to fine-tune the router over time
- **Voice-to-report:** Use speech-to-text (local model) to dictate issue reports in terminal mode
