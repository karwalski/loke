# Savings Dashboard Specification

**Story:** A4.3 — Savings dashboard
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

The savings dashboard gives users concrete, continuous visibility into the value loke provides. It answers four questions at a glance: How much money have I saved? How many tokens were optimised away? How much of my data stayed private? And how much of my compute stayed local?

This specification defines:

- The metrics collected and how they are calculated
- Time-series aggregation and trend views
- Browser mode layout (cards, charts, drill-down)
- Terminal mode equivalent (`loke stats`)
- Data storage, retention, and export
- Integration with the F4.5 token budget manager
- Privacy constraints on the dashboard itself
- Optional gamification elements

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Reinforce value.** The dashboard exists so users see the concrete benefit of loke in dollars and data protected. If users cannot see the value, they will stop using the tool.
- **Complexity is available, not imposed.** The default view is a handful of summary cards. Drill-down, time-series, and export are one click or one flag away.
- **Privacy is the foundation.** The dashboard displays only counts and types — never the PII values themselves.
- **The user is the authority.** All metrics are stored locally. Nothing is phoned home. Users can export, reset, or delete their metrics at any time.

---

## 2. Core Metrics

The dashboard tracks five metric families. Each metric has a current value (since last reset or install), a period value (configurable window), and a trend (direction and magnitude vs previous period).

### 2.1 Tokens Saved

| Field | Type | Description |
|-------|------|-------------|
| `pre_optimisation_tokens` | integer | Token count of the prompt/response before any loke optimisation |
| `post_optimisation_tokens` | integer | Token count actually sent to/received from the LLM |
| `tokens_saved` | integer | `pre_optimisation_tokens - post_optimisation_tokens` |
| `saving_percentage` | float | `(tokens_saved / pre_optimisation_tokens) * 100` |
| `saving_by_stage` | map | Breakdown by pipeline stage: TOON serialisation, LLMLingua compression, semantic cache hit, prompt deduplication |

Token counts use the tokeniser appropriate to the target model (tiktoken for OpenAI, sentencepiece for others). When the exact tokeniser is unavailable, a conservative estimate using cl100k_base is used and flagged as approximate.

### 2.2 Cost Saved

| Field | Type | Description |
|-------|------|-------------|
| `baseline_cost` | decimal (USD) | What it would have cost to send the unoptimised prompt to the model the user would have used without loke |
| `actual_cost` | decimal (USD) | What was actually spent (provider API charges + estimated local compute) |
| `cost_saved` | decimal (USD) | `baseline_cost - actual_cost` |
| `saving_percentage` | float | `(cost_saved / baseline_cost) * 100` |
| `local_compute_cost` | decimal (USD) | Estimated electricity cost for local inference (see section 5.2) |

#### 2.2.1 Baseline Model Selection

The baseline cost answers: "What would this have cost without loke?" The baseline model is determined by:

1. **User-configured baseline.** The user can set a default baseline model in settings (e.g. "gpt-4o" or "claude-sonnet-4"). This represents what they would normally use.
2. **Router's quality-equivalent.** If no baseline is configured, loke uses the cheapest cloud model that meets the quality tier the router classified the request into.
3. **Same model, unoptimised tokens.** If the request was routed to a cloud model, the baseline is the same model but at the pre-optimisation token count.

### 2.3 PII Entities Intercepted

| Field | Type | Description |
|-------|------|-------------|
| `total_entities` | integer | Total PII entities detected and anonymised |
| `by_type` | map | Count per entity type (e.g. `email_address: 42`, `person_name: 187`, `phone_number: 23`) |
| `by_sensitivity` | map | Count per sensitivity level: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED` |
| `by_detection_layer` | map | Count per detection layer: `regex`, `nlp`, `slm_ner`, `presidio` |
| `false_positive_rate` | float | Percentage of entities the user marked as incorrect via feedback (thumbs down on anonymisation preview) |

Entity types follow the Presidio entity taxonomy (180+ types), grouped into display categories for the summary view.

### 2.4 Local vs Cloud Ratio

| Field | Type | Description |
|-------|------|-------------|
| `total_requests` | integer | Total LLM requests processed |
| `local_requests` | integer | Requests handled by local models (Ollama, MLX, @electron/llm) |
| `cloud_requests` | integer | Requests routed to cloud providers |
| `companion_requests` | integer | Requests routed to companion devices |
| `local_ratio` | float | `(local_requests + companion_requests) / total_requests * 100` |

Companion device requests are counted as "local" for the ratio because data does not leave the user's trusted network.

### 2.5 Cache Hit Rate

| Field | Type | Description |
|-------|------|-------------|
| `cache_queries` | integer | Total requests checked against the semantic cache |
| `cache_hits` | integer | Requests served from cache (above similarity threshold) |
| `cache_hit_rate` | float | `(cache_hits / cache_queries) * 100` |
| `cache_tokens_saved` | integer | Tokens that would have been consumed if cache misses had been sent to a model |
| `cache_cost_saved` | decimal (USD) | Cost avoided through cache hits |

---

## 3. Time-Series Trends

### 3.1 Granularity

Metrics are recorded per-request and aggregated into time buckets:

| Granularity | Retention | Use case |
|-------------|-----------|----------|
| Per-request | 7 days | Drill-down into individual requests |
| Hourly | 30 days | Intraday patterns |
| Daily | 365 days | Day-over-day trends |
| Weekly | 2 years | Longer-term patterns |
| Monthly | Unlimited | Historical record |

Aggregation runs as a background task on a schedule (hourly for hourly buckets, daily at midnight local time for daily buckets, etc.). Raw per-request records are pruned after 7 days but their aggregated values are preserved in the coarser buckets.

### 3.2 Trend Indicators

Each metric includes a trend indicator comparing the current period to the previous equivalent period:

- **Direction:** up, down, or stable (< 2% change)
- **Magnitude:** percentage change
- **Colour coding:** Green for improvements (more savings, more local, more PII caught), amber for neutral, red for regressions

### 3.3 Anomaly Detection

Simple threshold-based anomaly detection flags unusual periods:

- Cost savings dropping below 20% of the rolling 7-day average
- PII detection count spiking above 3x the rolling 7-day average (may indicate a new data source or a detection issue)
- Cache hit rate dropping below 10% (may indicate cache invalidation or changed usage patterns)

Anomalies are surfaced as info-level notes on the dashboard, not as warnings (per the "warnings must be earned" principle).

---

## 4. Browser Mode Dashboard

### 4.1 Layout

The dashboard is a dedicated panel accessible from the main navigation. It uses the Scorecard Pattern (see design principles): ambient awareness, always available, never a warning.

#### 4.1.1 Summary Cards (Top Row)

Four cards across the top, each showing:

- **Metric name** (e.g. "Tokens Saved")
- **Primary value** (large, prominent — e.g. "1.2M tokens")
- **Secondary value** (percentage or dollar amount — e.g. "67% reduction")
- **Sparkline** (last 7 days, inline, no axis labels)
- **Trend arrow** (colour-coded direction indicator)

Cards:

| Card | Primary | Secondary | Sparkline source |
|------|---------|-----------|------------------|
| Tokens Saved | Absolute count | Percentage saved | Daily tokens saved |
| Cost Saved | Dollar amount | Percentage saved | Daily cost saved |
| PII Protected | Entity count | "across N types" | Daily entity count |
| Local Ratio | Percentage | "N of M requests" | Daily local ratio |

#### 4.1.2 Trend Chart (Middle)

A time-series area chart below the cards. Defaults to daily granularity, last 30 days. User can switch between:

- Tokens saved over time
- Cost saved over time
- PII entities over time
- Local ratio over time

Granularity selector: hourly / daily / weekly / monthly.
Period selector: last 24 hours / 7 days / 30 days / 90 days / 365 days / custom range.

#### 4.1.3 Drill-Down Panels (Bottom)

Expandable sections below the chart:

- **PII Breakdown.** Horizontal bar chart of entity types by count, sorted descending. Colour-coded by sensitivity level. Clicking a type shows the time series for that specific entity type.
- **Optimisation Breakdown.** Stacked bar showing contribution of each pipeline stage (TOON, LLMLingua, cache, dedup) to total token savings.
- **Routing Breakdown.** Pie or donut chart showing request distribution by model/provider. Table with per-model cost and token statistics.
- **Cache Performance.** Hit rate over time, average similarity score of hits, most frequently cached prompt categories.

#### 4.1.4 Depth Layers

Following the "complexity is available, not imposed" principle:

- **Layer 0:** Summary cards only (visible at all times in a sidebar widget or status bar)
- **Layer 1:** Full dashboard with cards, chart, and collapsed drill-downs
- **Layer 2:** Expanded drill-downs with breakdowns and per-model detail
- **Layer 3:** Raw metrics table with per-request data, export controls, and budget integration

### 4.2 Interactions

- **Hover:** Tooltip with exact values and timestamps on all chart elements
- **Click card:** Scrolls to and expands the relevant drill-down section
- **Period selector:** Applies globally to all cards, charts, and drill-downs
- **Refresh:** Metrics update in real time as requests are processed. No manual refresh needed.
- **Reset:** Settings menu option to reset all metrics (with confirmation dialogue)

---

## 5. Terminal Mode

### 5.1 Commands

```
loke stats                          # Summary for current period (default: today)
loke stats --period hourly          # Hourly breakdown for today
loke stats --period daily           # Daily breakdown for last 7 days
loke stats --period weekly          # Weekly breakdown for last 4 weeks
loke stats --period monthly         # Monthly breakdown for last 12 months
loke stats --from 2026-03-01 --to 2026-03-31   # Custom date range
loke stats --metric tokens          # Single metric detail
loke stats --metric cost            # Single metric detail
loke stats --metric pii             # Single metric detail
loke stats --metric local           # Single metric detail
loke stats --metric cache           # Single metric detail
loke stats --json                   # Output as JSON
loke stats --csv                    # Output as CSV
loke stats export --format csv --output ./loke-stats.csv   # Export to file
```

### 5.2 Default Output

```
loke stats — Today (2026-04-05)
────────────────────────────────────────────────

  Tokens saved      │  48,291 tokens (64.2%)     ▲ +3.1% vs yesterday
  Cost saved        │  $2.47 (58.3%)             ▲ +$0.31 vs yesterday
  PII protected     │  127 entities (14 types)   ▼ -8 vs yesterday
  Local ratio       │  71.4% (25 of 35)          ● stable
  Cache hit rate    │  23.1% (8 of 35)           ▲ +5.2% vs yesterday

────────────────────────────────────────────────
  Budget: $3.82 of $10.00 daily (38.2%)  ██████████░░░░░░░░░░░░░░░░
```

### 5.3 Period Output

```
loke stats --period daily
────────────────────────────────────────────────

  Day         │ Tokens Saved │ Cost Saved │ PII  │ Local │ Cache
  ────────────┼──────────────┼────────────┼──────┼───────┼──────
  2026-04-05  │  48,291 64%  │  $2.47 58% │  127 │  71%  │  23%
  2026-04-04  │  44,102 61%  │  $2.16 55% │  135 │  68%  │  18%
  2026-04-03  │  51,887 68%  │  $2.89 62% │   98 │  74%  │  27%
  2026-04-02  │  39,441 59%  │  $1.93 51% │  142 │  65%  │  15%
  2026-04-01  │  46,320 63%  │  $2.31 57% │  111 │  70%  │  21%
  2026-03-31  │  42,775 60%  │  $2.08 54% │  119 │  67%  │  19%
  2026-03-30  │  37,998 57%  │  $1.74 49% │   87 │  63%  │  14%
  ────────────┼──────────────┼────────────┼──────┼───────┼──────
  Total       │ 310,814 62%  │ $15.58 55% │  819 │  68%  │  20%
```

### 5.4 Verbose and JSON Output

`loke stats --metric pii` shows the full PII breakdown by type and sensitivity level in table format.

`loke stats --json` returns a JSON object matching the metric schema defined in section 2, suitable for piping to `jq` or other tools.

---

## 6. Calculation Methodology

### 6.1 Token Counting

Every request passing through the pipeline records two token counts:

1. **Pre-optimisation.** The token count of the original user prompt before any loke processing (TOON serialisation, LLMLingua compression, cache substitution). Counted using the target model's tokeniser.
2. **Post-optimisation.** The token count of the prompt actually sent to the model (or zero if served from cache).

Token counting occurs at two pipeline points:

- **Entry:** After receiving the user's prompt, before any transformations
- **Exit:** After all transformations, immediately before sending to the model (or returning a cache hit)

Response tokens are counted similarly: actual response tokens received vs what the unoptimised prompt would have produced (estimated using the same model's typical output ratio, or exact if the request was also served in an unoptimised form for A/B testing).

### 6.2 Cost Calculation

#### 6.2.1 Provider Pricing

loke maintains a pricing table for supported providers and models:

```typescript
interface ModelPricing {
  model_id: string;            // e.g. "gpt-4o", "claude-sonnet-4"
  provider: string;            // e.g. "openai", "anthropic"
  input_cost_per_1k: number;   // USD per 1,000 input tokens
  output_cost_per_1k: number;  // USD per 1,000 output tokens
  updated: string;             // ISO 8601 timestamp
}
```

Pricing is bundled with loke and updated with each release. Users can override prices in their configuration for custom or enterprise pricing tiers.

#### 6.2.2 Local Compute Cost

Local inference has no direct API cost, but does consume electricity. loke estimates local compute cost as:

```
local_cost = inference_time_seconds * tdp_watts * electricity_rate / 3_600_000
```

Where:
- `tdp_watts` is the TDP of the user's GPU/NPU/CPU (auto-detected or user-configured, default: 30W for Apple Silicon)
- `electricity_rate` is the user's electricity cost in USD/kWh (configurable, default: $0.15/kWh — approximate global average)
- `3_600_000` converts watt-seconds to kWh

This is a rough estimate, clearly labelled as approximate in the UI.

#### 6.2.3 Savings Formula

```
baseline_cost = pre_optimisation_input_tokens * baseline_model_input_rate
              + estimated_output_tokens * baseline_model_output_rate

actual_cost   = post_optimisation_input_tokens * actual_model_input_rate
              + actual_output_tokens * actual_model_output_rate
              + local_compute_cost

cost_saved    = baseline_cost - actual_cost
```

If `cost_saved` is negative (optimisation actually cost more due to routing to a more expensive model for quality reasons), the dashboard displays it honestly as a negative saving with an explanatory note.

### 6.3 PII Counting

Each PII entity detected by the privacy pipeline is counted once, even if detected by multiple layers. The deduplication logic in the privacy pipeline orchestrator (F3.6) ensures no double-counting. The detection layer recorded is the first layer that identified the entity.

---

## 7. Data Storage

### 7.1 Schema

Metrics are stored in the local SQLite database (F6.1, encrypted via SQLCipher). Two tables:

#### `metrics_raw`

Per-request metrics, retained for 7 days.

```sql
CREATE TABLE metrics_raw (
  id                    TEXT PRIMARY KEY,  -- ULID
  timestamp             TEXT NOT NULL,     -- ISO 8601
  request_id            TEXT NOT NULL,     -- Links to request audit trail
  pre_opt_tokens        INTEGER NOT NULL,
  post_opt_tokens       INTEGER NOT NULL,
  baseline_cost_usd     REAL NOT NULL,
  actual_cost_usd       REAL NOT NULL,
  local_compute_cost    REAL NOT NULL DEFAULT 0,
  pii_entity_count      INTEGER NOT NULL DEFAULT 0,
  pii_by_type           TEXT,             -- JSON map
  pii_by_sensitivity    TEXT,             -- JSON map
  pii_by_layer          TEXT,             -- JSON map
  route_destination     TEXT NOT NULL,    -- "local", "cloud", "companion", "cache"
  model_id              TEXT,
  provider              TEXT,
  cache_hit             INTEGER NOT NULL DEFAULT 0, -- boolean
  saving_by_stage       TEXT,             -- JSON map
  inference_time_ms     INTEGER
);
```

#### `metrics_aggregate`

Pre-aggregated metrics for each time granularity.

```sql
CREATE TABLE metrics_aggregate (
  id                    TEXT PRIMARY KEY,
  granularity           TEXT NOT NULL,    -- "hourly", "daily", "weekly", "monthly"
  period_start          TEXT NOT NULL,    -- ISO 8601
  period_end            TEXT NOT NULL,    -- ISO 8601
  request_count         INTEGER NOT NULL,
  pre_opt_tokens        INTEGER NOT NULL,
  post_opt_tokens       INTEGER NOT NULL,
  tokens_saved          INTEGER NOT NULL,
  baseline_cost_usd     REAL NOT NULL,
  actual_cost_usd       REAL NOT NULL,
  cost_saved_usd        REAL NOT NULL,
  pii_entity_count      INTEGER NOT NULL,
  pii_by_type           TEXT,             -- JSON map (summed)
  pii_by_sensitivity    TEXT,             -- JSON map (summed)
  local_requests        INTEGER NOT NULL,
  cloud_requests        INTEGER NOT NULL,
  companion_requests    INTEGER NOT NULL,
  cache_hits            INTEGER NOT NULL,
  cache_queries         INTEGER NOT NULL,
  saving_by_stage       TEXT,             -- JSON map (summed)

  UNIQUE(granularity, period_start)
);
```

### 7.2 Retention Policy

| Granularity | Retention | Pruning schedule |
|-------------|-----------|------------------|
| Raw (per-request) | 7 days | Daily at midnight |
| Hourly | 30 days | Daily at midnight |
| Daily | 365 days | Weekly |
| Weekly | 2 years | Monthly |
| Monthly | Unlimited | Never pruned |

Users can change retention periods in settings. Enterprise policy can mandate minimum retention (for audit purposes) or maximum retention (for data minimisation).

### 7.3 Aggregation

Aggregation is idempotent. Re-running aggregation for a period that already has an aggregate row replaces it. This allows correction if metrics are retroactively adjusted (e.g. pricing updates).

---

## 8. Export

### 8.1 Formats

| Format | Description |
|--------|-------------|
| CSV | Flat table, one row per period. Suitable for spreadsheet analysis. |
| JSON | Structured object matching the metric schema. Suitable for programmatic consumption. |

### 8.2 Browser Mode

Export button on the dashboard toolbar. User selects format, date range, and granularity. File is saved via the system file picker.

### 8.3 Terminal Mode

```
loke stats export --format csv --from 2026-01-01 --to 2026-03-31 --granularity daily --output ./stats.csv
loke stats export --format json --period monthly --output ./stats.json
```

If `--output` is omitted, output is written to stdout (useful for piping).

### 8.4 Privacy of Exports

Exported data contains the same metrics visible in the dashboard — counts, costs, percentages, model names, entity types. It never contains the actual PII values, prompt text, or response text.

---

## 9. Budget Integration

The savings dashboard integrates with the F4.5 token budget manager to provide a unified cost and usage view.

### 9.1 Budget Status Card

An additional card (or section within the cost card) shows:

| Field | Description |
|-------|-------------|
| Current spend | Actual cost for the current budget period |
| Budget limit | Configured limit for the period (daily, weekly, or monthly) |
| Burn rate | Average spend per hour/day for the current period |
| Projected spend | Extrapolated total spend for the period at current burn rate |
| Projected overage | If projected spend exceeds limit, show the estimated overage amount |
| Time remaining | Time until budget period resets |

### 9.2 Terminal Budget Display

Included in the default `loke stats` output as a progress bar (see section 5.2 example).

Detailed budget view:

```
loke budget
────────────────────────────────────────────────

  Period: Daily (resets at midnight)
  Spent:     $3.82 of $10.00 (38.2%)  ██████████░░░░░░░░░░░░░░░░
  Burn rate: $0.48/hour
  Projected: $7.64 (within budget)

  Period: Monthly (resets 2026-05-01)
  Spent:     $47.20 of $200.00 (23.6%) ██████░░░░░░░░░░░░░░░░░░░░
  Burn rate: $9.44/day
  Projected: $188.80 (within budget)
```

### 9.3 Overage Warnings

When projected spend exceeds the budget limit, the dashboard shows an advisory (not a warning — the budget manager itself handles warnings and blocks). The advisory includes:

- Projected overage amount
- Suggestion to adjust usage or increase the budget
- Link to budget settings

---

## 10. Privacy of the Dashboard

The dashboard itself must not become a privacy leak.

### 10.1 Constraints

- **No PII values.** The dashboard stores and displays entity counts and types, never the actual values. The string "john.smith@acme.com" is counted as one `email_address` entity — the address itself is never stored in metrics tables.
- **No prompt or response text.** Metrics reference requests by ID only. The request content is in the audit trail (F6.2), not in the metrics store.
- **No entity identifiers.** The dashboard does not distinguish between different people or entities. "3 person names detected" does not indicate whose names.
- **Screen lock.** If the OS session is locked, the dashboard is not visible on the lock screen or in task switcher previews. The Electron window uses `visibilityState` handling to blank sensitive panels.
- **Export warning.** When exporting metrics, a brief note reminds the user that while the export contains no PII, usage patterns may be considered sensitive by their organisation's data policy.

### 10.2 Audit Trail

Dashboard access and export events are logged in the audit trail:

- `dashboard.viewed` — timestamp only
- `dashboard.exported` — timestamp, format, date range
- `dashboard.reset` — timestamp, confirmation

---

## 11. Gamification (Optional)

Lightweight, opt-in gamification elements that reinforce the value of loke without being annoying.

### 11.1 Milestones

Users receive a brief, non-modal notification when they reach milestones:

| Milestone | Trigger |
|-----------|---------|
| First save | First request processed with token savings > 0 |
| 1,000 PII entities protected | Cumulative PII entity count reaches 1,000 |
| 10,000 PII entities protected | Cumulative PII entity count reaches 10,000 |
| 100,000 PII entities protected | Cumulative PII entity count reaches 100,000 |
| $100 saved | Cumulative cost savings reaches $100 |
| $1,000 saved | Cumulative cost savings reaches $1,000 |
| 1M tokens saved | Cumulative token savings reaches 1,000,000 |
| Privacy streak: 7 days | 7 consecutive days with zero PII leaked to cloud unprotected |
| Local champion | 90%+ local ratio sustained for 30 days |
| Cache master | 50%+ cache hit rate sustained for 7 days |

### 11.2 Streaks

A "privacy streak" counter tracks consecutive days where all PII was successfully anonymised before leaving the device. The streak is displayed on the dashboard as a small badge.

### 11.3 Opt-Out

Gamification is enabled by default but can be disabled entirely in settings. When disabled, no milestone notifications are shown and streak tracking stops. Milestone data is not deleted — it is simply not displayed.

### 11.4 Terminal Mode

Milestones are shown as a one-line message after the stats output:

```
  ✦ Milestone: 10,000 PII entities protected
```

Streaks appear in the stats summary:

```
  Privacy streak    │  14 days
```

---

## 12. Implementation Notes

### 12.1 Dependencies

| Dependency | Purpose | Story |
|------------|---------|-------|
| Privacy pipeline (F3.6) | PII entity counts and types | Must emit structured events per entity detected |
| Token optimisation pipeline (F4.1-F4.4) | Token counts and stage breakdowns | Must record pre/post counts per stage |
| Token budget manager (F4.5) | Budget limits and spend tracking | Dashboard reads budget state; budget manager is the source of truth |
| LLM Router (F5.3) | Routing decisions and model selections | Must emit routing events with destination and model |
| Semantic cache (F4.4) | Cache hit/miss events | Must emit cache query results |
| SQLite database (F6.1) | Metrics storage | Tables defined in section 7.1 |
| Audit trail (F6.2) | Dashboard access logging | Dashboard emits audit events |

### 12.2 Event-Driven Architecture

The dashboard does not poll the pipeline. Each pipeline stage emits structured events (via an in-process event bus) that the metrics collector subscribes to. The collector writes to `metrics_raw` and triggers aggregation as needed.

### 12.3 Performance

- Metrics write must not add perceptible latency to the pipeline. Writes are batched and flushed asynchronously.
- Dashboard rendering targets < 100ms for the summary view and < 500ms for full drill-down including chart rendering.
- Aggregation queries are indexed on `(granularity, period_start)`.

### 12.4 Testing Strategy

- Unit tests for all calculation methods (token counting, cost calculation, savings formula, aggregation)
- Integration tests for the metrics collector against a real SQLite instance
- Visual regression tests for the browser dashboard layout
- CLI snapshot tests for `loke stats` output formatting
