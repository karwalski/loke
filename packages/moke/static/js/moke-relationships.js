/*
 * moke-relationships.js — cross-dataset relationships and prompt suggestions
 * (stories MK8.7, MK20.5)
 *
 * WHY THIS EXISTS
 *
 * MK8.7 was marked Done. Its two functions — getRelatedDatasets() and
 * suggestCrossQueries() — were defined in templates/index.tkt and called from
 * nowhere, and the relationships structure they read rendered nowhere at all. Four
 * datasets' worth of genuinely good suggested prompts sat dead in the landing page.
 *
 * Meanwhile the chat page showed five hardcoded chips, the same five whatever was
 * loaded: "Find anomalies in the revenue data" and "Cluster customers by spending
 * behaviour" offered over a server inventory that has neither revenue nor
 * customers. So the suggestions that fitted the data were unreachable and the ones
 * on screen did not fit.
 *
 * Moving both out of the landing page is what makes either usable: the chat page
 * cannot call a function defined in index.tkt.
 *
 * WHAT A SUGGESTION IS AND IS NOT
 *
 * A suggested prompt is a question, not an answer. Nothing here computes, asserts
 * or displays a figure, so none of it touches the provenance rules in
 * moke-provenance.js. A prompt naming a specific row (SRV-037, say) is a question
 * about that row, not a disclosure of it — the value still has to be looked up
 * locally when the query runs.
 *
 * Run the tests: node packages/moke/static/js/tests/test-moke-relationships.js
 */
(function (global) {
  'use strict';

  // Which datasets join to which, and on what. Data, so it can move to the
  // manifest when MK19.1 lands without changing a caller.
  var RELATIONSHIPS = {
    'it_hardware.server_inventory': {
      primary_key: 'server_id',
      relationships: [
        { target: 'it_hardware.performance_metrics', foreign_key: 'server_id',
          type: 'one_to_many', label: 'Performance metrics' }
      ]
    },
    'it_hardware.performance_metrics': {
      primary_key: ['server_id', 'timestamp'],
      relationships: [
        { target: 'it_hardware.server_inventory', foreign_key: 'server_id',
          type: 'many_to_one', label: 'Server hardware' }
      ]
    },
    'it_platform.wc_users': {
      primary_key: 'user_id',
      relationships: [
        { target: 'it_platform.wc_orders', foreign_key: 'user_id',
          type: 'one_to_many', label: 'Customer orders' }
      ]
    },
    'it_platform.wc_orders': {
      primary_key: 'order_id',
      relationships: [
        { target: 'it_platform.wc_users', foreign_key: 'user_id',
          type: 'many_to_one', label: 'Customer profile' }
      ]
    }
  };

  var CROSS_QUERIES = {
    'it_hardware.server_inventory': [
      'Show servers with critical CPU or RAM alerts in the latest metrics',
      'List servers where warranty has expired and performance is degraded',
      'Compare average CPU utilisation between data centres',
      'Which servers have the highest load average in the most recent readings?',
      'Show all servers with warning or critical alert levels and their hardware specs'
    ],
    'it_hardware.performance_metrics': [
      'Show the 09:00 CPU spike pattern — which servers are most affected?',
      'Identify servers with gradual memory leaks over the 7-day window',
      'Plot disk latency trend for one server — is there degradation before failure?',
      'Which servers show correlated network throughput and error rate spikes?',
      'Compare average response times between data centres'
    ],
    'it_platform.wc_users': [
      'Show total order value by customer segment',
      'Which VIP customers have placed orders in the last 30 days?',
      'List users with high lifetime value but no recent orders',
      'Compare average order size between new and loyal customers',
      'Show inactive users who have outstanding orders'
    ],
    'it_platform.wc_orders': [
      'Show customer details for orders over $500',
      'Which customer segment generates the most revenue?',
      'List orders from VIP customers with coupon codes applied',
      'Compare order frequency between states for loyal customers',
      'Show orders from customers who joined in the last 6 months'
    ],
    // Merged from DEMO_PROMPTS in templates/chat.tkt, which was a third copy of
    // this idea covering a different set of datasets. Two tables in two templates
    // meant a dataset could have suggestions in one and not the other.
    'au.medicare': [
      'Top 10 specialties by total benefit paid',
      'Show claims over time by month'
    ],
    'au.water': [
      'Alert on pH readings below 6.5',
      'Compare turbidity across locations'
    ],
    'au.opal': [
      'Busiest tap-on stations by hour',
      'Average journey time by route'
    ],
    'customer_intelligence': [
      'Identify high-value customer segments',
      'Churn risk by region'
    ],
    'bitre.road_fatalities': [
      'Fatalities by state and year',
      'Compare weekday and weekend crash counts',
      'Which age group appears most often?'
    ]
  };

  // Prompts that are true of any tabular dataset. The old chat page offered five
  // chips of which three assumed revenue or customers, so these are the ones that
  // survived that filter — a prompt is only a fallback if it cannot be wrong.
  var GENERIC_PROMPTS = [
    'Summarise this dataset for me',
    'Which columns contain potential PII?',
    'Generate a dashboard for this dataset'
  ];

  /* Datasets that join to this one, resolved against a catalogue for display names.
   *
   * @param catalogue optional map of id -> {name}. Missing entries fall back to the
   *        id, which is ugly and honest, rather than to a guessed label.
   */
  function relatedDatasets(datasetKey, catalogue) {
    var entry = RELATIONSHIPS[datasetKey];
    if (!entry) return [];
    var cat = catalogue || {};
    return entry.relationships.map(function (rel) {
      var target = cat[rel.target];
      return {
        dataset: rel.target,
        name: (target && target.name) || rel.target,
        foreign_key: rel.foreign_key,
        type: rel.type,
        label: rel.label
      };
    });
  }

  function crossQueries(datasetKey) {
    return (CROSS_QUERIES[datasetKey] || []).slice();
  }

  /* The chips a page should offer for this dataset.
   *
   * Dataset-specific prompts first, then generic ones to fill out the list. A
   * prompt is never offered because it looks impressive: if there is nothing
   * specific to say, the generic three are what is true.
   */
  function promptsFor(datasetKey, limit) {
    var max = limit || 5;
    var specific = crossQueries(datasetKey);
    var out = specific.slice(0, max);
    for (var i = 0; i < GENERIC_PROMPTS.length && out.length < max; i++) {
      if (out.indexOf(GENERIC_PROMPTS[i]) === -1) out.push(GENERIC_PROMPTS[i]);
    }
    return out;
  }

  /* Does a join described here actually exist in the two datasets' columns?
   *
   * Checked rather than assumed, because a relationship that names a column the
   * data does not have would render a join suggestion that cannot run. Returns
   * the subset that checks out, plus what was dropped and why.
   */
  function verifyRelationships(datasetKey, catalogue) {
    var cat = catalogue || {};
    var kept = [];
    var dropped = [];
    relatedDatasets(datasetKey, cat).forEach(function (rel) {
      var a = cat[datasetKey], b = cat[rel.dataset];
      var aCols = (a && a.headers) || null;
      var bCols = (b && b.headers) || null;
      if (!aCols || !bCols) {
        dropped.push({ rel: rel, reason: 'a dataset is not in the catalogue' });
        return;
      }
      if (aCols.indexOf(rel.foreign_key) === -1) {
        dropped.push({ rel: rel, reason: datasetKey + ' has no column ' + rel.foreign_key });
        return;
      }
      if (bCols.indexOf(rel.foreign_key) === -1) {
        dropped.push({ rel: rel, reason: rel.dataset + ' has no column ' + rel.foreign_key });
        return;
      }
      kept.push(rel);
    });
    return { kept: kept, dropped: dropped };
  }

  var api = {
    RELATIONSHIPS: RELATIONSHIPS,
    GENERIC_PROMPTS: GENERIC_PROMPTS,
    relatedDatasets: relatedDatasets,
    crossQueries: crossQueries,
    promptsFor: promptsFor,
    verifyRelationships: verifyRelationships
  };

  global.MokeRelationships = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof window !== 'undefined' ? window : globalThis));
