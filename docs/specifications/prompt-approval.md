# Prompt Approval Workflow Specification

**Story:** A4.4 — Prompt approval workflow for beta
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

Before any prompt leaves the device, loke can show the user exactly what will be sent, how it differs from what they typed, and let them approve, edit, or cancel. This is the prompt approval workflow — a trust-building mechanism designed for loke's beta phase, where users are still learning what the privacy pipeline does and need visibility into every outbound request.

This specification defines:

- When approval is triggered (and when it is not)
- What the user sees in the pre-send display
- Available user actions (approve, edit, cancel)
- Mode-specific UI (browser, terminal, proxy)
- "Don't ask again" rules and their management
- Timeout, batch approval, and audit trail behaviour
- Policy integration and CLI configuration

### 1.1 Design Alignment

This specification follows the loke design principles:

- **The user is the authority.** Approval is advisory by default. The user can override, skip, or permanently dismiss it — except where enterprise policy mandates confirmation.
- **No data leaves without understanding.** The pre-send display exists so users can see precisely what crosses the network boundary, not a sanitised summary.
- **Warnings must be earned.** Approval prompts are shown only when they add value. For low-sensitivity prompts with trusted providers, automatic approval is the right default. Over-prompting trains users to click "approve" without reading.
- **Complexity is available, not imposed.** Layer 0 is "approve / cancel". Layer 1 adds the diff view and metadata. Layer 2 shows the full pipeline trace. Users choose their depth.
- **Speed is a feature.** The approval step must not make loke feel slow. Keyboard shortcuts, auto-approve rules, and batch approval exist to keep the workflow fast once trust is established.

---

## 2. Approval Trigger Rules

The approval workflow activates based on a combination of policy configuration, sensitivity level, provider, and user preferences. The trigger evaluation runs after the privacy pipeline has completed (anonymisation + optimisation) but before the request is dispatched to the provider.

### 2.1 Trigger Modes

| Mode | Behaviour |
|------|-----------|
| `always` | Every prompt requires approval, regardless of sensitivity or provider. Useful during initial onboarding or for high-security environments. |
| `by_sensitivity` | Approval required only when the prompt's sensitivity level meets or exceeds a configured threshold. This is the default. |
| `by_provider` | Approval required for specific providers (e.g. cloud providers but not local models). |
| `by_policy` | Approval required when the active policy's `sensitivity_thresholds.actions.<level>.require_user_confirmation` is `true`. Defers entirely to the policy engine (A3.1). |
| `never` | Approval is never shown. Prompts are sent immediately. Only permitted when no enterprise policy mandates confirmation. |

When multiple trigger conditions are active, they combine with logical OR — if any condition requires approval, the workflow activates.

### 2.2 Default Behaviour

Out of the box, with no policy loaded:

- `by_sensitivity` mode is active
- Threshold is `restricted` — prompts classified as RESTRICTED or above require approval
- All other prompts are sent without approval
- Users can tighten this to `always` or loosen it to `never` in their settings

### 2.3 Enterprise Override

Enterprise policies can enforce a minimum approval mode that users cannot weaken:

```yaml
# In enterprise policy
prompt_approval:
  minimum_mode: by_sensitivity        # User cannot set mode to 'never'
  minimum_sensitivity: confidential   # User cannot raise threshold above confidential
  lockout_message: "Your organisation requires approval for confidential and above."
```

When a `minimum_mode` is set, the user's settings page shows which approval rules are enterprise-enforced and cannot be changed, along with the `lockout_message` if provided.

---

## 3. Pre-Send Display

The pre-send display shows the user what will actually be sent, how it differs from what they typed, and relevant metadata. The goal is informed consent — the user should understand the outbound request well enough to make a meaningful approve/cancel decision.

### 3.1 Display Sections

#### 3.1.1 Original Prompt

The prompt as the user typed it (or as it was received from the upstream tool in proxy mode). Displayed in full, with syntax highlighting where applicable (markdown, code blocks).

#### 3.1.2 Transformed Prompt

The prompt after the full privacy pipeline has run — anonymisation, placeholder insertion, token optimisation, and any format conversion. This is the exact payload that will be sent to the provider. Displayed with the same syntax highlighting.

#### 3.1.3 Visual Diff

A side-by-side or inline diff between the original and transformed prompts, highlighting:

- **Anonymised entities** — PII replaced with placeholders, shown in a distinct colour (e.g. amber/orange) with tooltip or annotation showing the entity type (e.g. `[PERSON_NAME]`, `[EMAIL]`)
- **Compressed sections** — text reduced by the token optimiser, shown in a distinct colour (e.g. blue) with annotation showing compression ratio
- **Removed content** — text stripped entirely, shown as deletions
- **Unchanged content** — shown without highlighting, collapsed if the prompt is long

The diff view is the default view in the pre-send display. Users can switch to "original only" or "transformed only" tabs.

#### 3.1.4 Metadata Panel

| Field | Description |
|-------|-------------|
| **Target model** | The model selected by the router (e.g. `claude-sonnet-4-20250514`) |
| **Provider** | Provider name and whether it is local or cloud |
| **Estimated cost** | Token cost estimate in the configured currency (e.g. `~$0.003`) |
| **Sensitivity level** | The highest sensitivity classification detected (e.g. `CONFIDENTIAL`), with colour badge |
| **PII entities found** | Count and types of PII detected (e.g. `3 entities: 2 person names, 1 email address`) |
| **Token count** | Original tokens vs. transformed tokens, with percentage savings |
| **Anonymisation** | Whether anonymisation was applied, and which layers triggered |
| **Policy** | Name of the active policy, if any |

### 3.2 Long Prompt Handling

For prompts exceeding 200 lines:

- The diff view shows a summary header ("42 changes across 1,847 lines") with the first 50 lines expanded
- Remaining content is collapsed into scrollable/pageable sections
- A "Jump to changes" control navigates between diff hunks
- In terminal mode, a pager (`less`-style) is used with `/` search support

---

## 4. User Actions

### 4.1 Approve

Sends the transformed prompt to the provider as displayed. The approval decision and timestamp are recorded in the audit trail.

### 4.2 Edit

Opens the transformed prompt in an editable view. The user can modify the text that will be sent — for example, to manually redact something the pipeline missed, or to restore a placeholder that was overzealous.

Constraints:

- Edits apply to the **transformed** prompt only. The original is never modified.
- After editing, the metadata panel updates to reflect the new token count and estimated cost.
- Edited prompts are flagged in the audit trail as `user_edited`, with the edit diff recorded.
- Enterprise policy can disable editing if required (`allow_edit: false`).

### 4.3 Cancel

Aborts the request. Nothing is sent. The user is returned to their input context (chat panel, CLI prompt, or upstream tool receives an error response).

In proxy mode, cancellation returns an appropriate error to the upstream tool (e.g. HTTP 403 with a JSON body explaining the cancellation).

---

## 5. Browser Mode UI

### 5.1 Layout

The approval workflow appears as a **modal overlay** in the Electron window, preventing interaction with the chat panel or browser view behind it. The modal is divided into three regions:

1. **Header bar** — sensitivity badge, model/provider, estimated cost, approve/edit/cancel buttons
2. **Main area** — tabbed view with "Diff" (default), "Original", and "Transformed" tabs
3. **Footer** — PII entity summary, token savings, "Don't ask again" checkbox, keyboard shortcut hints

### 5.2 Diff View

- Inline diff by default (unified diff style), with option to toggle side-by-side
- Anonymised placeholders highlighted in amber with entity-type labels
- Compressed sections highlighted in blue with compression annotations
- Line numbers shown on both sides in side-by-side mode
- Syntax highlighting preserved through the diff (markdown, code, JSON, YAML)

### 5.3 Edit Mode

Clicking "Edit" transforms the "Transformed" tab into an editable text area with:

- The same syntax highlighting as the read-only view
- A "Revert" button to discard edits
- A "Send edited" button (replaces "Approve")
- Live-updating token count and cost estimate in the header

### 5.4 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` or `Cmd+Enter` | Approve and send |
| `Escape` | Cancel |
| `e` | Enter edit mode |
| `d` | Toggle diff view mode (inline / side-by-side) |
| `Tab` | Cycle through display tabs |
| `n` / `p` | Next / previous diff hunk |

### 5.5 Accessibility

- All actions reachable via keyboard
- Screen reader labels on all interactive elements
- Diff colours paired with text labels (not colour-only)
- High-contrast mode support

---

## 6. Terminal Mode UI

### 6.1 Display Format

The approval display uses a pager-style output to the terminal:

```
╔══════════════════════════════════════════════════════════════════╗
║  PROMPT APPROVAL REQUIRED                                       ║
║  Model: claude-sonnet-4   Provider: anthropic (cloud)           ║
║  Sensitivity: CONFIDENTIAL   Cost: ~$0.003                      ║
║  PII: 2 person names, 1 email   Tokens: 1,204 → 847 (−30%)    ║
╚══════════════════════════════════════════════════════════════════╝

--- Original → Transformed ---

  Can you review the contract for John Smith at
- john.smith@acme.com and summarise the key terms?
+ [PERSON_NAME_1] at [EMAIL_1] and summarise the key terms?

──────────────────────────────────────────────────────────────────

[a]pprove  [e]dit  [c]ancel  [d]on't ask again for CONFIDENTIAL
```

### 6.2 Coloured Diff

- Removed text (original PII): red with strikethrough where terminal supports it
- Added text (placeholders): green, bold
- Compressed sections: blue
- Unchanged context: default colour, dimmed
- Metadata header: bold, with sensitivity colour-coded (green/blue/amber/red)

### 6.3 Pager Mode

For prompts exceeding the terminal height, the diff is piped through a built-in pager with:

- Arrow key / `j`/`k` scrolling
- `/` search
- `q` to exit pager and return to the action prompt
- `n`/`p` to jump between diff hunks

### 6.4 Action Prompt

After the display, a single-character prompt:

- `a` or `y` — approve
- `e` — edit (opens `$EDITOR` or `nano` with the transformed prompt; on save, the edited version is sent)
- `c` or `n` — cancel
- `d` — don't ask again (prompts for scope: this sensitivity level, this provider, this session)

---

## 7. Proxy Mode Considerations

When loke runs as a proxy (A2.2) intercepting prompts from tools like Claude Code, Cursor, or other coding LLMs, the approval workflow has unique constraints:

- The upstream tool is waiting for a response and may time out
- The user may be in a flow state and interruptions are costly
- Prompts may arrive in rapid bursts (e.g. multi-step agentic workflows)

### 7.1 Proxy Approval Display

In proxy mode, the approval prompt appears in loke's own terminal (not the upstream tool's terminal). loke logs a brief notice to stderr in the upstream tool's terminal:

```
[loke] Approval required — switch to loke terminal to review (timeout: 30s)
```

### 7.2 Timeout Handling

If the user does not respond within the configured timeout:

| Timeout action | Behaviour |
|----------------|-----------|
| `deny` (default) | Request is cancelled. Upstream tool receives a timeout error. |
| `approve` | Request is sent as-is. Used when the user has high trust in the pipeline. |
| `downgrade` | Request is rerouted to a local model that does not require approval. |

```yaml
# In user config or policy
prompt_approval:
  proxy:
    timeout: 30                       # seconds
    timeout_action: deny              # deny | approve | downgrade
    downgrade_to: "local"             # provider for downgrade action
```

### 7.3 Batch Approval

When multiple prompts arrive in sequence (e.g. an agentic workflow making several MCP tool calls), loke groups them for batch review:

- **Approve all** — approve all pending prompts in the batch
- **Approve individually** — step through each prompt one by one
- **Cancel all** — abort all pending prompts

Batch grouping uses a configurable window: prompts arriving within `batch_window` seconds of each other are grouped.

```yaml
prompt_approval:
  proxy:
    batch_window: 5                   # seconds; 0 disables batching
```

### 7.4 Auto-Approve Rules

For proxy mode, users can define rules that skip approval entirely:

```yaml
prompt_approval:
  auto_approve:
    - provider: local                 # All local model requests
    - sensitivity: public             # All PUBLIC prompts
    - sensitivity: internal           # All INTERNAL prompts
    - upstream_tool: "claude-code"    # All prompts from Claude Code
      sensitivity: confidential       # ...but only up to CONFIDENTIAL
```

Auto-approve rules are evaluated before the approval workflow activates. If any rule matches, the prompt is sent without approval. These rules are subject to enterprise policy constraints — enterprise policy can set a ceiling on what can be auto-approved.

---

## 8. "Don't Ask Again" Rules

The "don't ask again" mechanism lets users progressively reduce approval friction as they build trust in the pipeline. Rules are additive — each "don't ask again" action creates a new auto-approve rule.

### 8.1 Rule Scopes

| Scope | Example | Effect |
|-------|---------|--------|
| **Per sensitivity level** | "Don't ask for PUBLIC" | All prompts at or below PUBLIC skip approval |
| **Per provider** | "Always approve local models" | All prompts routed to `local` skip approval |
| **Per sensitivity + provider** | "Don't ask for INTERNAL to Anthropic" | Prompts at INTERNAL or below going to Anthropic skip approval |
| **Per upstream tool** | "Don't ask for Claude Code" | All prompts from Claude Code skip approval (proxy mode) |

### 8.2 Duration

Each "don't ask again" rule has a duration:

| Duration | Behaviour |
|----------|-----------|
| `session` | Rule expires when loke is closed |
| `permanent` | Rule persists across sessions, stored in user config |

When triggered from the approval UI, the user is asked to choose the duration. The default is `session` — permanent rules require an explicit second confirmation.

### 8.3 Revocation

All "don't ask again" rules are visible and revocable from:

- **Browser mode:** Settings > Privacy > Approval Rules
- **Terminal mode:** `loke config approval-rules list` and `loke config approval-rules remove <id>`
- **Direct config edit:** Rules are stored in the user config file as YAML (see Section 11)

Revoking a rule immediately re-enables approval for matching prompts.

### 8.4 Enterprise Constraints

Enterprise policy can set a floor below which "don't ask again" rules cannot be created:

```yaml
# In enterprise policy
prompt_approval:
  dont_ask_again:
    min_sensitivity: confidential     # Users cannot skip approval at CONFIDENTIAL or above
    allow_permanent: false            # Only session-scoped rules permitted
```

---

## 9. Timeout Behaviour

### 9.1 General Timeout

The approval prompt has a configurable timeout, after which a default action is taken. This applies to all modes, but is most important in proxy mode where upstream tools are waiting.

| Setting | Default | Description |
|---------|---------|-------------|
| `timeout` | `0` (no timeout) | Seconds before timeout. `0` means wait indefinitely. |
| `timeout_action` | `deny` | Action on timeout: `deny`, `approve`, `downgrade`. |
| `timeout_warning` | `10` | Seconds before timeout to show a countdown warning. |

### 9.2 Mode-Specific Defaults

| Mode | Default timeout | Default action | Rationale |
|------|----------------|----------------|-----------|
| Browser | `0` (none) | N/A | User is actively looking at the screen |
| Terminal (direct) | `0` (none) | N/A | User is actively at the terminal |
| Proxy | `30` | `deny` | Upstream tool will time out; default-deny is safest |

### 9.3 Timeout Display

- Browser: countdown timer in the approval modal header, progressing from green to amber to red
- Terminal: countdown displayed in the action prompt line, updating in place
- On timeout, a clear message explains what happened and what action was taken

---

## 10. Audit Trail

Every approval workflow interaction is recorded in the audit trail (F6.2). Approval events are append-only and tamper-evident.

### 10.1 Recorded Events

| Event | Fields |
|-------|--------|
| `approval_shown` | Timestamp, prompt ID, sensitivity level, provider, model, trigger reason, mode (browser/terminal/proxy) |
| `approval_granted` | Timestamp, prompt ID, decision time (ms), auto-approved (bool), rule ID if auto-approved |
| `approval_denied` | Timestamp, prompt ID, decision time (ms), reason (user/timeout/policy) |
| `approval_edited` | Timestamp, prompt ID, edit diff (what changed), original transformed hash, edited hash |
| `approval_timeout` | Timestamp, prompt ID, timeout duration, action taken |
| `approval_batch` | Timestamp, batch ID, prompt IDs, action (approve_all/cancel_all/individual) |
| `dont_ask_again_created` | Timestamp, rule scope, duration, sensitivity, provider |
| `dont_ask_again_revoked` | Timestamp, rule ID, revocation source (settings/CLI/policy) |

### 10.2 Privacy in Audit Logs

Audit logs for approval events record:

- The **transformed** prompt (post-anonymisation), never the original
- PII entity types and counts, not the original values
- Edit diffs reference the transformed prompt only

This ensures that even if audit logs are exported or forwarded (to SIEM systems per F6.2), no PII is exposed.

---

## 11. Configuration

### 11.1 Policy Integration

The `prompt_approval` section can appear in any policy layer (enterprise, team, user). Merge rules follow the standard policy precedence (A3.1): enterprise > team > user.

```yaml
# Full prompt_approval policy section
prompt_approval:
  # Trigger mode
  mode: by_sensitivity                # always | by_sensitivity | by_provider | by_policy | never
  sensitivity_threshold: restricted   # Minimum level requiring approval (for by_sensitivity mode)

  # Provider-specific triggers
  providers:
    require_approval:
      - "openai"
      - "anthropic"
      - "google"
    skip_approval:
      - "local"
      - "ollama"

  # Pre-send display
  display:
    default_view: diff                # diff | original | transformed
    diff_mode: inline                 # inline | side_by_side
    show_metadata: true
    show_cost_estimate: true
    collapse_unchanged_after: 200     # lines; 0 to never collapse

  # User actions
  actions:
    allow_edit: true                  # Whether users can edit the transformed prompt
    allow_cancel: true                # Whether users can cancel (false only for audit-only mode)

  # Timeout
  timeout:
    browser: 0                        # seconds; 0 = no timeout
    terminal: 0
    proxy: 30
    timeout_action: deny              # deny | approve | downgrade
    timeout_warning: 10               # seconds before timeout to show warning
    downgrade_to: "local"

  # Proxy mode
  proxy:
    batch_window: 5                   # seconds; 0 disables batching
    stderr_notice: true               # Show notice in upstream tool's stderr

  # Auto-approve rules (user-created, subject to enterprise constraints)
  auto_approve:
    - provider: local
    - sensitivity: public
    - sensitivity: internal
      provider: anthropic

  # "Don't ask again" constraints (enterprise only)
  dont_ask_again:
    min_sensitivity: restricted       # Floor for user-created rules
    allow_permanent: true             # Whether permanent rules are allowed

  # Enterprise overrides (enterprise policy only)
  minimum_mode: by_sensitivity        # User cannot set mode below this
  minimum_sensitivity: confidential   # User cannot raise threshold above this
  lockout_message: "Organisational policy requires approval for confidential data and above."
```

### 11.2 CLI Flags

The following CLI flags override configuration for the current invocation only. They are not persisted.

| Flag | Effect |
|------|--------|
| `--approve-all` | Skip all approval prompts for this session. Equivalent to `mode: never`. Blocked if enterprise policy sets a `minimum_mode`. |
| `--dry-run` | Run the full pipeline but do not send. Display the approval screen and exit. Useful for testing policy and pipeline behaviour. |
| `--approval-timeout <seconds>` | Override the timeout for this session. |
| `--approval-mode <mode>` | Override the trigger mode for this session (`always`, `by_sensitivity`, `never`, etc.). |

```bash
# Skip approval for a trusted local session
loke ask --approve-all "Summarise this document"

# Preview what would be sent without actually sending
loke ask --dry-run "Review the contract for John Smith at john@acme.com"

# Proxy mode with 60-second timeout
loke proxy claude-code --approval-timeout 60
```

### 11.3 `--dry-run` Behaviour

When `--dry-run` is active:

1. The full pipeline runs (anonymisation, optimisation, routing decision)
2. The pre-send display is shown exactly as it would be in a real approval
3. No request is sent to any provider regardless of user action
4. The audit trail records a `dry_run` event
5. Exit code: `0` if the prompt would have been approved (by policy/auto-rules), `1` if it would have required manual approval, `2` if it would have been blocked

This is useful for CI pipelines validating that prompts conform to policy, and for users exploring how the pipeline transforms their input.

---

## 12. State Machine

The approval workflow follows a deterministic state machine:

```
                    ┌─────────────┐
                    │  Pipeline   │
                    │  Complete   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Evaluate   │──── auto-approve rule matches ──→ SEND
                    │  Triggers   │
                    └──────┬──────┘
                           │ approval required
                    ┌──────▼──────┐
              ┌─────│   Display   │─────┐
              │     │  Approval   │     │
              │     └──────┬──────┘     │
              │            │            │
         ┌────▼───┐  ┌────▼───┐  ┌─────▼────┐
         │ Cancel │  │Approve │  │   Edit   │
         └────┬───┘  └────┬───┘  └────┬─────┘
              │           │           │
              │           │     ┌─────▼─────┐
              │           │     │  Editor   │
              │           │     └─────┬─────┘
              │           │           │
              │      ┌────▼───────────▼────┐
              │      │        SEND         │
              │      └─────────────────────┘
         ┌────▼───────────┐
         │    ABORT       │
         └────────────────┘
```

Timeout transitions to ABORT (default) or SEND (if `timeout_action: approve`).

---

## 13. Security Considerations

### 13.1 Edit Tampering

The edit capability allows users to modify the transformed prompt. This means a user could re-insert PII that was anonymised. This is by design — **the user is the authority**. However:

- The audit trail records the full edit diff, making re-insertion visible in audit reports
- Enterprise policy can disable editing (`allow_edit: false`) for environments where this is unacceptable
- If the edited prompt's sensitivity is higher than the original assessment, a re-evaluation warning is shown

### 13.2 Auto-Approve Abuse

Auto-approve rules bypass the approval screen entirely. Safeguards:

- Enterprise policy sets a floor (`dont_ask_again.min_sensitivity`) that users cannot bypass
- All auto-approved prompts are still recorded in the audit trail with `auto_approved: true`
- The savings dashboard (A4.3) shows auto-approval statistics so users and admins can monitor
- `--approve-all` is blocked when enterprise policy sets a `minimum_mode`

### 13.3 Timeout Race Conditions

In proxy mode, a timeout can race with a user's approve action. The implementation must use atomic state transitions to ensure exactly one outcome (approve or deny) is applied. If the timeout fires after the user clicks approve but before the state transition completes, the user's action takes precedence.

---

## 14. Future Considerations

These items are out of scope for the beta implementation but may be added based on user feedback:

- **Approval delegation** — allow a second user (e.g. a security reviewer) to approve on behalf of the requester
- **Approval templates** — pre-approved prompt patterns that skip approval when matched
- **ML-based auto-approve** — learn from user approval patterns to suggest auto-approve rules
- **Approval analytics** — dashboard showing approval rates, edit frequency, most-common PII types, average decision time
- **Mobile notifications** — push approval requests to a companion mobile app for remote approval
