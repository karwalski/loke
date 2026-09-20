/*
 * test-moke-provenance.js — tests for the provenance vocabulary (NC1.5, NC1.6, MK20.4).
 *
 * Run: node packages/moke/static/js/tests/test-moke-provenance.js
 *
 * These import the real module rather than restating its logic. That distinction
 * matters here: 54 of the toke test files re-declare the module under test instead
 * of importing it, and a test that re-declares its subject cannot fail when the
 * subject breaks.
 *
 * The load-bearing assertions are the two that were actually violated in shipped
 * code:
 *
 *   1. A card with no provenance must NOT be treated as resolved. If the default
 *      were 'resolved', every model-supplied number would render.
 *   2. Only a resolved card may carry a caption claiming local computation. The
 *      presentation slides said "Count computed locally — no data left the
 *      device" over a hardcoded string, so this is tested as a property of the
 *      caption function rather than left to each caller's discipline.
 */
'use strict';

const P = require('../moke-provenance.js');

let failures = 0;
let checks = 0;

function ok(cond, msg) {
  checks++;
  if (!cond) {
    failures++;
    console.error('  FAIL: ' + msg);
  }
}

function eq(actual, expected, msg) {
  ok(actual === expected, msg + ' (got ' + JSON.stringify(actual) + ', expected ' +
     JSON.stringify(expected) + ')');
}

// ── Default state ──────────────────────────────────────────────────────────
// The single most important behaviour in the file.
eq(P.cardState({}), 'unresolved', 'a card with no provenance is unresolved');
eq(P.cardState(null), 'unresolved', 'null is unresolved, not a crash');
eq(P.cardState({ provenance: {} }), 'unresolved', 'empty provenance is unresolved');
eq(P.cardState({ provenance: { state: 'RESOLVED' } }), 'unresolved',
   'state matching is case-sensitive, so a near-miss does not pass as resolved');
eq(P.cardState({ provenance: { state: 'computed' } }), 'unresolved',
   'an invented state name is unresolved');
ok(!P.mayDisplayValue({}), 'a card with no provenance may not display a value');
ok(!P.mayDisplayValue({ metric: { resolved_value: '12,489' } }),
   'carrying a value is not permission to display it — this is NC1.5 in one line');

// ── The three legal states ─────────────────────────────────────────────────
P.STATES.forEach(function (s) {
  eq(P.cardState({ provenance: { state: s } }), s, 'state ' + s + ' round-trips');
});
ok(P.mayDisplayValue({ provenance: { state: 'resolved' } }), 'resolved may display');
ok(!P.mayDisplayValue({ provenance: { state: 'no-data' } }), 'no-data may not display');
ok(!P.mayDisplayValue({ provenance: { state: 'unresolved' } }), 'unresolved may not display');

// ── stripUnverifiedValues ──────────────────────────────────────────────────
const ddl = {
  cards: [
    {
      title: 'Total customers',
      provenance: { state: 'resolved' },
      metric: {
        label: 'Total customers [12,483]',
        value: 12483, resolved_value: '12,483', delta: '+8.4%',
        resolved_delta: '+8.4%', data: [1, 2, 3], resolved_label: 'Total customers'
      }
    },
    {
      title: 'Revenue trend',
      chart: {
        chart_type: 'line',
        resolved_data: { labels: ['a'], values: [1] },
        data: [1, 2], labels: ['a', 'b'], values: [1, 2], datasets: [{}]
      }
    },
    {
      title: 'Top customers',
      table: { rows: [['C-0047', '$184,200']], resolved_rows: [['x']],
               resolved_columns: ['a'], data: [[1]] }
    },
    null
  ]
};
P.stripUnverifiedValues(ddl);

const m = ddl.cards[0].metric;
['value', 'resolved_value', 'delta', 'resolved_delta', 'data', 'resolved_label'].forEach(function (k) {
  ok(!(k in m), 'metric.' + k + ' is deleted');
});
eq(m.label, 'Total customers', 'the bracketed number is stripped from the label');
ok(!('provenance' in ddl.cards[0]), 'provenance is cleared so it must be re-established');

const c = ddl.cards[1].chart;
['resolved_data', 'data', 'labels', 'values', 'datasets'].forEach(function (k) {
  ok(!(k in c), 'chart.' + k + ' is deleted');
});
eq(c.chart_type, 'line', 'chart_type survives — it is a shape, not a value');

const t = ddl.cards[2].table;
['rows', 'resolved_rows', 'resolved_columns', 'data'].forEach(function (k) {
  ok(!(k in t), 'table.' + k + ' is deleted');
});
ok(true, 'a null card does not throw');

// A label with no bracket must be left exactly alone.
const plain = { cards: [{ metric: { label: 'Median order value' } }] };
P.stripUnverifiedValues(plain);
eq(plain.cards[0].metric.label, 'Median order value', 'a label without a bracket is untouched');

// ── chartHasLocalData ──────────────────────────────────────────────────────
ok(P.chartHasLocalData({ resolved_data: { labels: ['jan'], values: [1] } }),
   'a resolved series counts as local');
ok(!P.chartHasLocalData({ resolved_data: { labels: [], values: [] } }),
   'an empty resolved series does not');
ok(!P.chartHasLocalData({ data: [1, 2, 3], chart_type: 'line' }),
   'a bare data array on a line chart is not evidence of local computation');
ok(P.chartHasLocalData({ chart_type: 'scatter', data: [{ x: 1, y: 2 }] }),
   'Insight Lab scatter points are locally computed');
ok(P.chartHasLocalData({ chart_type: 'SCATTER', data: [{ x: 1, y: 2 }] }),
   'chart_type comparison is case-insensitive');
ok(!P.chartHasLocalData(null), 'null chart is not local data');

// ── provenanceCaption ──────────────────────────────────────────────────────
// The regression this function exists to prevent: a caption asserting local
// computation over a card that computed nothing.
const CLAIMS_COMPUTATION = /computed locally/i;
ok(CLAIMS_COMPUTATION.test(P.provenanceCaption({ provenance: { state: 'resolved' } })),
   'a resolved card may say it was computed locally');
[{}, { provenance: {} }, { provenance: { state: 'unresolved' } },
 { provenance: { state: 'no-data' } }].forEach(function (card, i) {
  ok(!CLAIMS_COMPUTATION.test(P.provenanceCaption(card)),
     'card ' + i + ' does not claim local computation');
});
ok(P.provenanceCaption({ provenance: { state: 'unresolved', reason: 'no column order_date' } })
   .indexOf('no column order_date') !== -1,
   'the unresolved caption names the reason');
ok(P.cardReason({}) === P.DEFAULT_REASON, 'a reasonless card gets the default reason');

// ── resolvedCards ──────────────────────────────────────────────────────────
const mixed = {
  cards: [
    { provenance: { state: 'resolved' } },
    { provenance: { state: 'unresolved' } },
    {},
    { provenance: { state: 'no-data' } },
    { provenance: { state: 'resolved' } }
  ]
};
eq(P.resolvedCards(mixed).length, 2, 'only resolved cards are presentable');
eq(P.resolvedCards({}).length, 0, 'an empty DDL has nothing to present');
eq(P.resolvedCards(null).length, 0, 'a null DDL has nothing to present');

// ── markAllCards ───────────────────────────────────────────────────────────
const all = { cards: [{}, {}, {}] };
P.markAllCards(all, 'no-data', 'no dataset loaded');
ok(all.cards.every(function (card) { return P.cardState(card) === 'no-data'; }),
   'markAllCards sets every card');
ok(all.cards.every(function (card) { return !P.mayDisplayValue(card); }),
   'and none of them may display a value');

// ── presentableKind ────────────────────────────────────────────────────────
// The slide-admission predicate. Every case below was a way presentation mode
// could put a figure on a screen that nobody computed.
function resolved(extra) { return Object.assign({ provenance: { state: 'resolved' } }, extra); }

eq(P.presentableKind(resolved({ metric: { resolved_value: '12,483' } })), 'metric',
   'a resolved metric with a value is presentable');
eq(P.presentableKind(resolved({ metric: { resolved_value: 0 } })), 'metric',
   'zero is a real value and must not be filtered out as falsy');
eq(P.presentableKind(resolved({ metric: { resolved_value: '' } })), null,
   'an empty string is not a value');
eq(P.presentableKind(resolved({ metric: { resolved_value: null } })), null,
   'null is not a value');
eq(P.presentableKind(resolved({ metric: { label: 'Total' } })), null,
   'a resolved metric with no value is left out, not rendered empty');

eq(P.presentableKind(resolved({
  chart: { chart_type: 'line', resolved_data: { labels: ['jan'], values: [1] } }
})), 'chart', 'a resolved chart with a local series is presentable');
eq(P.presentableKind(resolved({ chart: { chart_type: 'line', data: [1, 2, 3] } })), null,
   'a chart with only a bare data array is not presentable');
eq(P.presentableKind(resolved({
  chart: { chart_type: 'scatter', data: [{ x: 1, y: 2 }] }
})), 'chart', 'Insight Lab scatter points are presentable');

eq(P.presentableKind(resolved({ table: { resolved_rows: [['a']] } })), 'table',
   'a resolved table with rows is presentable');
eq(P.presentableKind(resolved({ table: { resolved_rows: [] } })), null,
   'an empty table is not presentable');
eq(P.presentableKind(resolved({ table: { rows: [['C-0047', '$184,200']] } })), null,
   'unresolved rows are not presentable however real they look');

// Unresolved and no-data cards are never presentable, whatever they carry.
[{ state: 'unresolved' }, { state: 'no-data' }].forEach(function (prov) {
  eq(P.presentableKind({ provenance: prov, metric: { resolved_value: '99' } }), null,
     'a ' + prov.state + ' card is not presentable even carrying a resolved_value');
});
eq(P.presentableKind({ metric: { resolved_value: '99' } }), null,
   'a card with NO provenance is not presentable — the default that stops invented figures');

// A DDL of entirely unresolved cards yields nothing to present, which is what
// makes "Nothing to present yet" reachable instead of a deck of fabrications.
eq(((({ cards: [{}, {}, {}] }).cards) || []).filter(P.presentableKind).length, 0,
   'nothing in an unprovenanced DDL is presentable');

if (failures) {
  console.error('\ntest-moke-provenance: ' + failures + ' of ' + checks + ' checks FAILED');
  process.exit(1);
}
console.log('test-moke-provenance: ' + checks + ' checks passed (including presentableKind)');
