# moke Demo — Feature Expansion Backlog

**Goal:** Showcase as many loke features as possible through the moke conceptual demo, making it the definitive interactive demonstration of loke's capabilities.

**Current state:** moke demonstrates schema-first privacy, local compute (15 operations), LLM-generated dashboards, sensitivity classification, governance rules, 17 datasets, and CSV upload. Running on ooke at port 11432.

**What's missing:** Token optimisation visibility, TOON before/after, MCP integration, feedback system, agent framework, Memory Palace, AAAK, companion devices, pipeline visibility, savings tracking, prompt approval, regulatory presets, compliance reporting, and streaming.

---

## MK8: Token Optimisation Showcase

*Show users exactly how much they save — TOON format, LLMLingua, caching, and combined metrics.*

| Story | Size | Summary |
|-------|------|---------|
| MK8.1 | M | TOON before/after comparison panel — display original JSON payload alongside TOON output with live token count and percentage savings on every request |
| MK8.2 | S | LLMLingua compression indicator — show prompt compression ratio in the console log when LLMLingua is active |
| MK8.3 | M | Semantic cache hit indicator — display "Cache HIT" badge with saved tokens/cost when a cached response is served; show cache miss with "first seen" label |
| MK8.4 | M | Cumulative savings ticker — persistent UI element showing running totals: tokens saved, estimated cost saved (USD), cache hit rate, local compute ratio |
| MK8.5 | S | Token budget widget — display remaining budget for the session with configurable daily/weekly/monthly limits and visual progress bar |

## MK9: Pipeline Visibility Integration

*Let users see every stage of the privacy pipeline in real time.*

| Story | Size | Summary |
|-------|------|---------|
| MK9.1 | L | Real-time pipeline panel — dockable panel showing all 9 stages (input → privacy scan → anonymisation → token optimisation → routing → LLM call → response scan → de-anonymisation → output) with live status transitions and per-stage timing |
| MK9.2 | M | Pipeline detail expansion — click any stage to see: entities detected, tokens before/after, model selected, cache decision, violations found |
| MK9.3 | S | Pipeline history sidebar — list of recent pipeline runs with status badges; click to replay the stage progression |

## MK10: Prompt Approval & Transparency

*Show exactly what will be sent to the LLM before it goes.*

| Story | Size | Summary |
|-------|------|---------|
| MK10.1 | M | Pre-send review modal — show original prompt on left, anonymised + compressed prompt on right, with diff highlighting (red for removed PII, amber for anonymised, blue for compressed); approve/cancel/edit buttons |
| MK10.2 | S | "Are you sure?" sensitivity gate — trigger approval modal automatically when dataset sensitivity is CONFIDENTIAL or RESTRICTED; skip for PUBLIC/INTERNAL |
| MK10.3 | S | Approval audit trail — log every approval/cancellation decision with timestamp, user action, and request ID; display in console log |

## MK11: Feedback & Quality

*Demonstrate the feedback loop on every interaction.*

| Story | Size | Summary |
|-------|------|---------|
| MK11.1 | M | Thumbs up/down on every response — add feedback buttons below each LLM response and dashboard card; capture rating, optional comment, model ID, and request ID |
| MK11.2 | S | Feedback summary panel — show aggregate feedback stats: thumbs up %, thumbs down %, by model, by dataset category; surface in settings page |
| MK11.3 | S | "Why this output?" button — click to see decision trace: which model was selected and why, what PII was detected, what compression was applied, pipeline timing |

## MK12: Agent Framework Demo

*Show lightweight agents performing scheduled and triggered tasks.*

| Story | Size | Summary |
|-------|------|---------|
| MK12.1 | L | Demo agent: nightly data quality scanner — scheduled agent that scans all loaded datasets for anomalies (using existing ML engine), generates a summary report, stores results in Memory Palace |
| MK12.2 | M | Demo agent: schema change detector — triggered when a dataset is re-uploaded; compares old vs new schema, flags added/removed/changed columns, alerts user |
| MK12.3 | M | Agent status panel — show registered agents with status (idle/running/scheduled/errored), last run time, next scheduled run, cost so far |
| MK12.4 | S | Agent output viewer — click an agent to see its diary: run history, findings, errors, duration, tokens used |

## MK13: Memory Palace Demo

*Demonstrate persistent cross-session memory with the palace hierarchy.*

| Story | Size | Summary |
|-------|------|---------|
| MK13.1 | L | Memory Palace browser — visual explorer showing Wings → Halls → Rooms → Drawers hierarchy; click to navigate; show drawer count per room |
| MK13.2 | M | Auto-memory from conversations — after each chat interaction, automatically store the question, response, dataset context, and findings as a drawer in the appropriate wing/hall/room |
| MK13.3 | M | Memory search — search bar that queries the palace semantically; results show relevance score, source conversation, timestamp; click to load context |
| MK13.4 | S | AAAK context display — show the AAAK-compressed context that's loaded into each LLM call; toggle between compressed and expanded views |
| MK13.5 | S | Memory status widget — show palace stats: total drawers, wings, storage size; displayed in settings |

## MK14: MCP Integration Demo

*Show moke as both an MCP client and host.*

| Story | Size | Summary |
|-------|------|---------|
| MK14.1 | M | MCP tool panel — display available MCP tools (compress, decompress, profile, analyse) with descriptions; click to invoke manually with sample data |
| MK14.2 | M | MCP broker status — show connected MCP servers, their tools, health status, and per-server permission badges (allowed/denied tools) |
| MK14.3 | S | Memory MCP server demo — expose memory.search, memory.store, memory.status tools via MCP; show tool invocations in console log |

## MK15: Regulatory & Governance Demo

*Show policy enforcement, compliance, and governance in action.*

| Story | Size | Summary |
|-------|------|---------|
| MK15.1 | M | Regulatory preset selector — dropdown to switch between GDPR, AU Privacy Act, HIPAA, CCPA, etc.; immediately changes anonymisation behaviour, blocked entities, and routing rules |
| MK15.2 | M | Governance dashboard panel — show governance health: privacy %, compliance violations, risk tier breakdown, kill switch status; mirrors the loke G4 dashboards |
| MK15.3 | S | Kill switch demo — red button that immediately stops all external LLM traffic; visual indicator showing "BLOCKED" state; resume button |
| MK15.4 | S | Compliance report generator — button to generate a compliance summary report for the current session; display inline or download as CSV/JSON |
| MK15.5 | S | Risk classification badges — show Low/Medium/High risk tier on each request with colour coding; click for explanation |

## MK16: Companion Device & Routing Demo

*Show intelligent model routing and companion device concepts.*

| Story | Size | Summary |
|-------|------|---------|
| MK16.1 | M | Model routing explainer — for each request, show why a particular model was selected: intent classification, sensitivity score, cost estimate, latency tolerance; display as expandable card |
| MK16.2 | M | Tiered inference visualiser — show the three inference tiers (Interactive/Considered/Background) with current request placement, throughput estimates, and model recommendations based on detected hardware |
| MK16.3 | S | Companion device simulator — simulated "nearby device" panel showing discovery, pairing flow, and offload indicator; no real networking required, just the UX flow |
| MK16.4 | S | Cost comparison widget — after each response, show: "Cloud cost: $X.XX | Local cost: $0.00 | You saved: $X.XX" |

## MK17: Streaming & Real-Time

*Show streaming responses and real-time updates.*

| Story | Size | Summary |
|-------|------|---------|
| MK17.1 | M | Streaming LLM responses — display tokens as they arrive from the LLM; show typing indicator; update token count live |
| MK17.2 | S | Live pipeline stage animation — pulse/glow animation on the active pipeline stage during streaming; stage transitions visible in real time |
| MK17.3 | S | Live console log — auto-scrolling console that shows pipeline events as they happen during a streaming request |

## MK18: i18n & a11y in Demo

*Ensure the demo itself is internationalised and accessible.*

| Story | Size | Summary |
|-------|------|---------|
| MK18.1 | M | Wrap all moke UI strings in t() — replace hardcoded English in all templates and pages with translation keys; add moke-specific keys to en.json |
| MK18.2 | M | Accessibility audit and fixes — add ARIA landmarks, skip link, keyboard navigation, live region announcements, focus management to all moke pages |
| MK18.3 | S | Language switcher in moke settings — allow switching between en-AU and en-US in the demo |

---

## Priority Order

1. **MK9** Pipeline Visibility — highest-impact demo of loke's core value proposition
2. **MK8** Token Optimisation — concrete savings numbers build credibility
3. **MK10** Prompt Approval — privacy-first "are you sure?" moment
4. **MK15** Regulatory & Governance — enterprise audience differentiator
5. **MK11** Feedback & Quality — demonstrates the learning loop
6. **MK13** Memory Palace — cross-session intelligence
7. **MK12** Agent Framework — automation capabilities
8. **MK14** MCP Integration — ecosystem connectivity
9. **MK16** Companion & Routing — intelligent model selection
10. **MK17** Streaming — polish and responsiveness
11. **MK18** i18n & a11y — ensures demo is accessible and translatable

---

## Summary

| Epic | Stories | Combined Size |
|------|---------|---------------|
| MK8 Token Optimisation | 5 | 2M + 2S + 1M |
| MK9 Pipeline Visibility | 3 | 1L + 1M + 1S |
| MK10 Prompt Approval | 3 | 1M + 2S |
| MK11 Feedback & Quality | 3 | 1M + 2S |
| MK12 Agent Framework | 4 | 1L + 2M + 1S |
| MK13 Memory Palace | 5 | 1L + 2M + 2S |
| MK14 MCP Integration | 3 | 2M + 1S |
| MK15 Governance | 5 | 2M + 3S |
| MK16 Routing & Companion | 4 | 2M + 2S |
| MK17 Streaming | 3 | 1M + 2S |
| MK18 i18n & a11y | 3 | 2M + 1S |
| **Total** | **41** | |
