# moke — Feature Document

**Version:** 0.2.0
**Generated:** 2026-05-20
**License:** Apache 2.0

moke is a data analysis demo application that exercises loke's privacy pipeline, governance controls, and LLM integration end-to-end. It serves as a reference implementation, integration test scaffold, and the primary demo for loke's capabilities.

moke runs on port 11432 via `ooke-toke serve` and communicates with loke on port 11430 for LLM inference and privacy filtering.

---

## How moke Demonstrates loke

| loke Feature | How moke Demonstrates It |
|-------------|--------------------------|
| **Privacy pipeline** | Confirm modal shows raw data vs anonymised data side-by-side. PII entity chips show what was detected. TOON tokens replace sensitive values. |
| **Sensitivity classification** | Every dataset gets a sensitivity badge (PUBLIC/CONFIDENTIAL/RESTRICTED) shown throughout the UI. Colour-coded: green/amber/red. |
| **Pipeline transparency** | Collapsible pipeline console logs each stage (anonymise, routing, compute, restore) with timestamps. |
| **Kill switch** | Governance page has an engage/release toggle. When active, a pulsing red banner blocks all LLM traffic. |
| **Feedback system** | Thumbs up/down buttons on every LLM response. Feedback stored locally, exportable via settings. Feedback score shown on governance dashboard. |
| **Cost tracking** | Session stats show token counts (in/out), cost estimate, and savings vs cloud. Governance dashboard shows cumulative cost and local/cloud ratio. |
| **Model routing** | Settings page configures Anthropic/OpenAI keys. Pipeline auto-routes: if API key present, uses Claude; otherwise falls back to Ollama (local). |
| **Governance dashboard** | Full risk breakdown (low/medium/high), request log with risk badges, compliance report generation, regulatory presets. |
| **Memory palace** | Hierarchical wing/hall/room/drawer navigation with semantic search, AAAK compression, and persistent storage. |
| **MCP tools** | Tool browser, broker status, memory operations — invoke MCP tools with JSON args and see results. |
| **Data type detection** | 26-detector cascade identifies PII, dates, currency, percentages, IDs, booleans, geo coordinates, URLs, and more. |

---

## Application Shell

**File:** `templates/base.tkt`

The app shell provides the persistent layout across all pages.

**Navigation (Sidebar):**
- **Workspace:** Home (dataset selector), Analysis (chat), Dashboard, Insight Lab
- **Tools:** Upload, Connections, Agents, Memory, MCP
- **System:** Governance, System Monitor, Settings

**Status Bar:**
- loke connection indicator (green dot = connected, red = offline)
- Privacy filter status (ON/OFF)
- Current dataset name and sensitivity badge
- Version display (loke + moke)

**Health Polling:**
Auto-detects deployment mode — tries same-origin `/api/health` first (for single-port deployment), falls back to cross-origin `http://127.0.0.1:11430` (for dev mode with separate ports). Updates every 15 seconds.

**Guided Demo Walkthrough:**
8-step floating overlay panel (bottom-right) that walks new users through the full moke experience:
1. Load IT Server Hardware dataset
2. View schema with type detection
3. Ask "Show servers with expired warranties"
4. Navigate to Dashboard and generate visualisation
5. Navigate to Insight Lab and run clustering
6. Load IT Performance Metrics
7. Ask "Which servers have memory leaks?"
8. Navigate to Governance and view session stats

Progress stored in sessionStorage — survives page navigation. "Start Demo" button on landing page.

---

## Pages

### Home — Dataset Selector

**File:** `templates/index.tkt`

Landing page with categorised dataset cards. One-click loading into the analysis workspace.

**Dataset Categories:**

**Government & Public Sector (3 datasets):**

| Dataset | Rows | Columns | Sensitivity | Patterns |
|---------|------|---------|-------------|----------|
| Medicare Benefits Schedule | 500 | 28 | CONFIDENTIAL | Seasonal flu spike (July), bulk billing rate by state, gap amounts by specialty, follow-up flags |
| Sydney Water Quality | 200 | 25 | PUBLIC | Seasonal temperature variation, 3 sensors with deteriorating pH, 2 turbidity alerts, weather correlation |
| ABS Employment Statistics | 30 | 22 | PUBLIC | National employment data |

**IT Operations (8 datasets):**

| Dataset | Rows | Columns | Sensitivity | Patterns |
|---------|------|---------|-------------|----------|
| IT Server Hardware | 200 | 34 | CONFIDENTIAL | 12 overloaded (>90% CPU), 8 expired warranties, 5 unpatched, 3 untested DR servers across SYD-1/SYD-2/MEL-1/BNE-1 |
| IT Performance Metrics | 10,000 | 12 | INTERNAL | Daily CPU spikes 09:00-10:00, memory leak on 3 servers, disk latency degradation, correlated network/error spikes. Generated via seeded PRNG. |
| IT Incidents & Alerts | 500 | 14 | CONFIDENTIAL | Recurring P1 on 2 servers (same root cause), P2 cluster during maintenance windows, >15% SLA breach rate for network category |
| IT Change Management | 300 | 11 | INTERNAL | Emergency changes correlate with P1 incidents, Friday deployments have 3x rollback rate |
| IT Application Performance | 2,000 | 13 | INTERNAL | Version 2.3.1 latency regression, one endpoint with 5x error rate, apdex drops during peak hours |
| IT Asset & Cost | 48 | 14 | CONFIDENTIAL | 20% of servers consume 60% of costs, 5 servers past depreciation still running |

**Customer Intelligence (1 dataset):**

| Dataset | Rows | Columns | Sensitivity | Patterns |
|---------|------|---------|-------------|----------|
| Customer Intelligence | 1,000 | 26 | CONFIDENTIAL | 5 segments: Growth (400), At-risk (200), Dormant (180), Whales (20, LTV $15K-58K), Regular (170), Anomalies (30, disposable emails) |

**Cross-Dataset Relationships:**
Foreign key registry linking server_id across Hardware ↔ Metrics ↔ Incidents ↔ Changes ↔ Assets. Natural language query suggestions for cross-dataset analysis (e.g., "Show incidents for servers with >90% CPU utilisation").

Larger datasets (500+ rows) use seeded PRNG generator functions for deterministic, reproducible data that doesn't bloat the template.

---

### Analysis Chat

**File:** `templates/chat.tkt` (~2,200 lines)

The primary analysis interface — chat with an LLM about the loaded dataset.

**26-Detector Type Detection Engine:**
Cascading detector array from most specific to generic:
- PII by name (patient_name, medicare_number, etc.)
- Email regex, phone regex, URL regex
- UUID, IP address, colour hex
- Currency (with symbol detection)
- Percentage, boolean, ordinal
- Date/time (ISO 8601, AU formats)
- Geo coordinates (lat/lng ranges)
- JSON structure, categorical
- Integer, float, free text (fallback)

Each detector returns `{type, subtype, confidence, stats}`.

**Schema Panel (Left):**
- Column cards showing detected type with icon and colour
- Type-specific summary stats: date range for dates, sum/mean for currency, true/false ratio for booleans, unique count for categoricals, min/max for numerics, PII lock icon for sensitive fields
- Column type override (click to change)
- Sensitivity badge

**Data Preview Table:**
- First 10 rows in sortable table
- Column headers with type badges
- Row count and column count

**Chat Interface:**
- Message bubbles with assistant/user styling
- Thumbs up/down on every response (stored to localStorage)
- Demo prompt chips (dataset-specific suggested questions)
- Chat history persistence across page navigations (sessionStorage)
- New conversation button (clears history, increments counter)

**Pipeline Console:**
- Collapsible panel logging each processing stage
- Colour-coded: schema (teal), profile (blue), anonymise (amber), LLM (purple), compute (green), restore (teal)
- Timestamps per entry
- Clear button

**Session Stats:**
- Requests count
- Tokens in/out
- Cost estimate
- Local vs cloud ratio
- Estimated savings vs cloud-only

**Privacy Review (Pre-Send):**
Before sending to the LLM, shows the privacy confirmation modal (see Confirm section below). Users see exactly what data leaves and what stays local.

---

### Privacy Confirmation

**File:** `templates/confirm.tkt`

Full transparency layer before any data is sent to an external LLM.

**Split-Panel View:**
- **Left:** Raw data — all columns, sample rows, PII columns highlighted in red as "SUPPRESSED"
- **Right:** Anonymised version — TOON tokens replacing sensitive values (PERSON_1, MEDICARE_1, DOB_1, ADDRESS_1, etc.)

**PII Entity Chips:**
Dynamic display of detected entity types with counts per type (PERSON, MEDICARE_ID, DATE_OF_BIRTH, ADDRESS, PHONE, EMAIL).

**System Prompt Preview:**
Collapsible view showing the exact system prompt sent to the LLM, including guardian instructions and governance constraints. Full transparency into what instructs the model.

**Sensitivity Badge:**
Colour-coded header: RESTRICTED (red), CONFIDENTIAL (red), INTERNAL (amber), PUBLIC (green).

**Actions:**
- **Cancel** — abort the request entirely
- **Edit** — modify the prompt before sending
- **Approve & Send** — proceed with anonymised data
- **"Don't ask again this session"** checkbox

---

### Dashboard Generation

**File:** `templates/dashboard.tkt`

Three-phase pipeline combining LLM design with local computation.

**Phase 1 — LLM Design:**
User question + dataset schema sent to loke's pipeline endpoint. LLM returns Dashboard DDL (Domain Definition Language) describing card layout, chart types, metrics, queries.

**Phase 2 — Local Computation:**
Client-side query execution — zero data egress. Supports: groupBy, bucketDates, metric calculations (sum, avg, min, max, count), filters on numeric/categorical columns.

**Phase 3 — Rendering:**
Chart.js integration for 5 card types:
- **Metric** — single KPI with delta/trend
- **Chart** — bar, line, pie, scatter, area
- **Table** — sortable rows with pagination
- **Text** — markdown rendered
- **List** — bulleted/numbered items

**Dataset-Specific Prompts:**
Pre-loaded suggestions for each dataset type (Medicare claims analysis, server utilisation, customer segmentation, water quality compliance, etc.).

**Template System:**
Save/load dashboard configurations to localStorage. Export as PNG, JSON, or PDF.

**Refinement:**
After initial generation, ask follow-up questions. Dashboard updates in real-time with new DDL.

---

### Insight Lab — Client-Side ML

**File:** `templates/insight.tkt`

Zero-data-egress machine learning — all algorithms run client-side in the browser.

**Algorithms:**

| Algorithm | Purpose | Parameters |
|-----------|---------|-----------|
| K-Means Clustering | Discover groups in data | k = 2–20, convergence detection |
| Z-Score Anomalies | Statistical outlier detection | Threshold (default 2.5 std devs) |
| IQR Outliers | Conservative outlier detection | Q1, Q3, 1.5×IQR fences |
| Pearson Correlation | Feature relationship mapping | All numeric column pairs |

**Quick Analysis:**
3 pre-built analyses per dataset with one-click execution. Examples: "High-value Medicare claims", "Server utilisation clusters", "Customer churn signals".

**5-Stage Progress Display:**
Load → Init → Iterate → Results → Viz — with animated progress indicators.

**Result Visualisation:**
Cluster cards with centroid profile bar charts. Anomaly tables with scores. Correlation matrix heatmap.

**Dashboard Integration:**
Convert ML results to DDL format and push to dashboard for visualisation.

---

### Governance Dashboard

**File:** `templates/governance.tkt`

Full visibility into privacy pipeline, compliance reporting, and emergency controls.

**Kill Switch:**
Toggle to immediately block all external LLM traffic. Pulsing red banner when active.

**Risk Dashboard:**
- Risk breakdown bars: low (green) / medium (amber) / high (red)
- Request log table with timestamp, type, detail, risk badge
- Privacy score (% of requests with no violations)

**Session Metrics (auto-refreshed every 10 seconds):**
- Total cost (USD)
- PII entities detected
- Tokens consumed
- Feedback score (thumbs up %)
- Request count
- Local vs cloud ratio (pie chart)

**Compliance Reporting:**
Generate reports as inline, CSV, or JSON. Templates for: EU GDPR, AU Privacy Act, HIPAA, CCPA, UK GDPR, Singapore PDPA.

**External Integration Connectors (10 presets):**
PagerDuty, Datadog, Grafana, Splunk, Elastic, Slack, Microsoft Teams, Opsgenie, ServiceNow, Custom webhook.

---

### Settings

**File:** `templates/settings.tkt`

**Session Settings:**
Memory persistence toggle, pipeline verbosity (minimal/standard/verbose), default sensitivity level, auto-save dashboard templates.

**LLM Configuration:**
Preferred model dropdown (auto-loaded from Ollama), Anthropic/OpenAI API key inputs with masking, connection test button, base URL override.

**Data & Feedback:**
Export feedback JSON, data retention policy, session memory toggle.

**Connection Info:**
loke version, Ollama status, proxy health, connection test.

---

### Upload

**File:** `templates/upload.tkt`

**Input Methods:**
1. **File upload** — drag-drop CSV/TSV with auto-delimiter detection
2. **Paste** — raw data with header/delimiter detection
3. **Built-in datasets** — 9 reference datasets with one-click load

**Type Inference:**
Numeric, categorical (≤15 unique), datetime, text. PII detection by column name patterns and regex.

**Schema Review:**
Sortable preview table, column type badges, pagination, column rename.

---

### API Connections

**File:** `templates/connections.tkt`

**Connection Form:**
Name, URL, method (GET/POST/PUT/DELETE), auth type (None/API Key/Bearer/Basic/OAuth 2.0), headers (key-value table), query parameters, request body (JSON, POST/PUT only).

**Test Connection:**
One-click test with latency measurement. Response status badge, headers, body preview (first 500 chars).

**Save & Load:**
Connections persisted to localStorage. Credentials stored server-side via loke (never in browser).

---

### Memory Palace

**File:** `templates/memory.tkt`

Hierarchical navigation: Wings (Work, Reference, Personal, Learning) → Halls → Rooms → Drawers.

**Search:** Keyword matching with scoring (exact > partial > fuzzy). Top 20 results.

**AAAK Compression:** Client-side text compression (removes articles, prepositions). Shows compression ratio.

**Persistent Storage:** localStorage with auto-save. 5 default system memories seeded.

---

### MCP Tools

**File:** `templates/mcp.tkt`

**Tabs:**
1. **Tools Browser** — grid of available MCP tools with category badges, invoke button
2. **Broker Status** — server count, tool count, health indicators
3. **Memory Operations** — direct buttons for `memory.status`, `memory.search`, `memory.store`

**Invocation Modal:** JSON args textarea, live result display, console log.

---

### System Monitor

**File:** `templates/sysmon.tkt`

System health monitoring and diagnostics.

---

### Agents

**File:** `templates/agents.tkt`

Agent management UI — create, schedule, monitor, and review agent runs.

---

### Presentation Mode

**File:** `templates/presentation.tkt`

Full-screen slideshow with auto-cycle (8-second intervals). Keyboard controls: arrows (navigate), Space/P (play/pause), F (fullscreen), ESC (exit). 4 demo slides: customer metric, cluster scatter, revenue trend, top customers table.

---

## JavaScript Utility Modules

**Directory:** `static/js/`

Nine standalone modules (zero external dependencies) providing client-side data source integration:

| Module | Global | Purpose |
|--------|--------|---------|
| `json-parser.js` | `MokeJsonParser` | Parse JSON API responses into tabular datasets. Auto-detects arrays, wrapped objects, pagination. Flattens nested objects with dot notation. |
| `graphql-source.js` | `MokeGraphQL` | Execute GraphQL queries, introspect schemas, convert responses to tabular format. Save/load queries to localStorage. |
| `openapi-discovery.js` | `MokeOpenAPI` | Parse Swagger 2.0 / OpenAPI 3.x specs. Auto-fill connection form from endpoints. Generate example request bodies from schemas. Built-in YAML parser. |
| `auth-methods.js` | `MokeAuth` | 5 auth types (API Key, Bearer, Basic, OAuth 2.0, mTLS). Form rendering, credential storage via loke backend, token refresh, value masking. |
| `datagov-source.js` | `MokeDataGov` | Search data.gov.au CKAN API. Download CSV datasets. 6 pre-suggested datasets (ABS, Medicare, BoM, Transport, Water, Energy). |
| `url-import.js` | `MokeUrlImport` | Fetch CSV/Excel from URLs. Auto-detect delimiter, encoding, header row. Google Sheets, Dropbox, GitHub URL transforms. Basic .xlsx reader. |
| `connection-manager.js` | `MokeConnectionManager` | CRUD for saved connections. Health tracking (green/amber/red). Scheduled refresh (5min–24h). Export/import configs (secrets stripped). |
| `api-cache.js` | `MokeApiCache` | sessionStorage cache with configurable TTL (default 5 min). Hit/miss tracking, LRU eviction on quota, auto-prune. Drop-in `cachedFetch()` wrapper. |
| `rate-limiter.js` | `MokeRateLimiter` | Per-host request queuing (max 3 concurrent). 429 + Retry-After handling. Exponential backoff with jitter. Status panel rendering. |

---

## Data Flow

```
User loads dataset
    → upload.tkt (schema inference, PII detection, sensitivity classification)
    → Stored in sessionStorage

User asks question
    → chat.tkt (26-detector type profiling, prompt construction)
    → confirm.tkt (transparency: raw vs anonymised side-by-side)
    → User approves
    → POST to loke /api/pipeline (privacy filter → LLM → response)
    → Response displayed with feedback buttons

User generates dashboard
    → dashboard.tkt Phase 1: LLM returns DDL
    → Phase 2: client-side computation (zero egress)
    → Phase 3: Chart.js rendering

User runs ML analysis
    → insight.tkt (K-Means, anomalies, correlations — all client-side, zero egress)

Governance review
    → governance.tkt (risk breakdown, request log, compliance reports)
```

**Key principle:** All sensitive data processing happens client-side. External LLMs only receive anonymised data via loke's privacy filter. ML analysis runs entirely in the browser with zero data egress.

---

## GA3 UX Enhancements — Completed

The following UX improvements from the GA3 epic are now implemented across moke:

**Graduated Warning System (GA3.2):** Four-level warning display applied throughout moke — Info (non-interruptive, shown in pipeline view), Advisory (subtle indicator, dismissible), Warning (clear banner, requires acknowledgement), Block (cannot proceed without decision). Applied to PII detection, cost thresholds, sensitivity changes, and policy violations.

**Simple/Advanced View Toggle (GA3.3):** The chat page now offers a "Simple View / Advanced View" toggle. Simple mode shows only chat bubbles and the send button. Advanced mode reveals the schema panel, pipeline console, session stats, and data preview. Defaults to Simple for new users.

**Pre-Send Cost Estimation (GA3.4):** Before sending a prompt, moke displays the estimated token count and cost based on the selected model pricing (e.g., "This will cost ~$0.003 (245 tokens)"). Users see cost before confirming, preventing accidental overspend.

**Cancel In-Flight Request (GA3.5):** A "Cancel" button is now visible during LLM processing, allowing users to abort requests that take too long.

**Feedback Comments (GA3.6):** When a user clicks thumbs-down, a lightweight text input appears with "What went wrong?" prompt. No required fields. The comment is stored alongside the rating for feedback analysis.

**Sensitivity Tooltips (GA3.7):** Sensitivity badges (PUBLIC/CONFIDENTIAL/RESTRICTED) throughout moke now show a tooltip explaining how sensitivity was inferred (e.g., "CONFIDENTIAL: dataset contains patient_name and medicare_number columns").

**Accessibility Overhaul (GA3.1):** Full ARIA label coverage across all interactive elements in all moke templates — `aria-expanded` on collapsible panels, `aria-label` on icon buttons, `role="dialog"` on modals, `aria-live="polite"` on dynamic content (typing indicator, pipeline console, loading states), skip navigation links, visible focus states, and logical tab order.
