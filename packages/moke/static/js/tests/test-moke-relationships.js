/*
 * test-moke-relationships.js — tests for cross-dataset suggestions (MK8.7, MK20.5).
 *
 * Run: node packages/moke/static/js/tests/test-moke-relationships.js
 *
 * The load-bearing test is verifyRelationships against the REAL column lists from
 * templates/index.tkt. A declared join is a claim about the data, and this is the
 * only thing in the module that can be wrong in a way a user would notice: a chip
 * offering a join on a column that does not exist produces a query that cannot run.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const R = require('../moke-relationships.js');

let failures = 0;
let checks = 0;
function ok(cond, msg) {
  checks++;
  if (!cond) { failures++; console.error('  FAIL: ' + msg); }
}
function eq(a, b, msg) {
  ok(a === b, msg + ' (got ' + JSON.stringify(a) + ', expected ' + JSON.stringify(b) + ')');
}

// ── Build a catalogue from the real template, not a hand-written stand-in ──
// index.tkt holds the dataset definitions as a JS object literal. Only the id and
// headers are needed, so they are extracted rather than the file evaluated.
const INDEX = fs.readFileSync(
  path.resolve(__dirname, '../../../templates/index.tkt'), 'utf8');

function extractCatalogue(src) {
  const cat = {};
  const entry = /'([a-z0-9_]+\.[a-z0-9_]+)':\s*\{\s*\n\s*name:\s*'([^']*)'/g;
  let m;
  while ((m = entry.exec(src)) !== null) {
    const id = m[1];
    if (cat[id]) continue;
    // headers: [...] within the next stretch of this entry
    const rest = src.slice(m.index, m.index + 8000);
    const h = /headers:\s*\[([^\]]*)\]/.exec(rest);
    cat[id] = {
      name: m[2],
      headers: h ? h[1].split(',').map(function (s) { return s.trim().replace(/^'|'$/g, ''); })
                  : null
    };
  }
  return cat;
}

const catalogue = extractCatalogue(INDEX);
ok(Object.keys(catalogue).length >= 4,
   'extracted at least four datasets from index.tkt (got ' + Object.keys(catalogue).length + ')');

// ── Every declared relationship must hold against the real columns ─────────
let anyVerified = false;
Object.keys(R.RELATIONSHIPS).forEach(function (key) {
  if (!catalogue[key] || !catalogue[key].headers) {
    // Not a failure of the module: the dataset is not in this template. Recorded
    // so the test says which, rather than silently passing on zero work.
    console.log('  note: ' + key + ' not found in index.tkt with headers — skipped');
    return;
  }
  const v = R.verifyRelationships(key, catalogue);
  const usable = v.kept.length + v.dropped.filter(function (d) {
    return d.reason.indexOf('not in the catalogue') !== -1;
  }).length;
  eq(v.dropped.filter(function (d) { return d.reason.indexOf('has no column') !== -1; }).length, 0,
     key + ': every declared join names a column both datasets have' +
     (v.dropped.length ? ' — dropped: ' + v.dropped.map(function (d) { return d.reason; }).join('; ') : ''));
  ok(usable > 0, key + ' declares at least one relationship');
  if (v.kept.length) anyVerified = true;
});
ok(anyVerified, 'at least one relationship verified against real columns');

// ── relatedDatasets ───────────────────────────────────────────────────────
const rel = R.relatedDatasets('it_hardware.server_inventory', catalogue);
eq(rel.length, 1, 'server inventory has one related dataset');
eq(rel[0].dataset, 'it_hardware.performance_metrics', 'and it is the metrics table');
eq(rel[0].foreign_key, 'server_id', 'joined on server_id');
ok(rel[0].name !== 'it_hardware.performance_metrics',
   'the display name comes from the catalogue, not the id');
eq(R.relatedDatasets('nope.nothing', catalogue).length, 0, 'an unknown dataset has no relations');
eq(R.relatedDatasets('it_hardware.server_inventory', {})[0].name,
   'it_hardware.performance_metrics',
   'with no catalogue the id is shown — ugly and honest, not a guessed label');
eq(R.relatedDatasets(undefined).length, 0, 'undefined key does not throw');

// ── crossQueries ──────────────────────────────────────────────────────────
ok(R.crossQueries('it_hardware.server_inventory').length === 5, 'five suggestions for servers');
eq(R.crossQueries('nope.nothing').length, 0, 'no suggestions for an unknown dataset');
// Returned array must be a copy: a caller that sorts or splices it must not
// corrupt the table for the next page view.
const q1 = R.crossQueries('it_hardware.server_inventory');
q1.push('mutated');
eq(R.crossQueries('it_hardware.server_inventory').length, 5, 'the suggestion list is copied');

// The suggestions must not assume columns the dataset lacks — the exact defect
// the old chat chips had, offering "revenue" over a server inventory.
const serverCols = (catalogue['it_hardware.server_inventory'] || {}).headers || [];
if (serverCols.length) {
  const forbidden = ['revenue', 'spending behaviour', 'customers by'];
  R.crossQueries('it_hardware.server_inventory').forEach(function (q) {
    forbidden.forEach(function (word) {
      ok(q.toLowerCase().indexOf(word) === -1,
         'a server-inventory suggestion does not mention "' + word + '": ' + q);
    });
  });
}

// ── promptsFor ────────────────────────────────────────────────────────────
const p = R.promptsFor('it_hardware.server_inventory');
eq(p.length, 5, 'five chips offered');
eq(p[0], R.crossQueries('it_hardware.server_inventory')[0],
   'dataset-specific prompts come first');

const generic = R.promptsFor('nope.nothing');
eq(generic.length, R.GENERIC_PROMPTS.length,
   'an unknown dataset falls back to only the generic prompts');
generic.forEach(function (g) {
  ok(R.GENERIC_PROMPTS.indexOf(g) !== -1, 'fallback prompt is from the generic set: ' + g);
});
// The generic set must be true of ANY tabular dataset. That is the whole reason
// three of the original five chips were dropped.
R.GENERIC_PROMPTS.forEach(function (g) {
  ['revenue', 'customer', 'spending', 'server'].forEach(function (word) {
    ok(g.toLowerCase().indexOf(word) === -1,
       'generic prompt assumes nothing about the data ("' + word + '"): ' + g);
  });
});

eq(R.promptsFor('it_hardware.server_inventory', 2).length, 2, 'the limit is respected');
eq(R.promptsFor('nope.nothing', 2).length, 2, 'the limit applies to fallbacks too');
ok(new Set(R.promptsFor('it_hardware.server_inventory', 8)).size ===
   R.promptsFor('it_hardware.server_inventory', 8).length,
   'no prompt is offered twice');

// ── Report ────────────────────────────────────────────────────────────────
if (failures) {
  console.error('\ntest-moke-relationships: ' + failures + ' of ' + checks + ' checks FAILED');
  process.exit(1);
}
console.log('test-moke-relationships: ' + checks + ' checks passed');
