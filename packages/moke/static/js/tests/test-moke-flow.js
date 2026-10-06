/*
 * test-moke-flow.js — tests for the demo flow interpreter (MK20.1, MK20.2).
 *
 * Run: node packages/moke/static/js/tests/test-moke-flow.js
 *
 * Imports the real module and the real flows.json, not a simplified restatement.
 *
 * The two load-bearing groups are the two defects the interpreter replaced:
 *
 *   1. THE OFF-BY-ONE. Three of the eight original steps wrote the next step
 *      index before navigating, so arriving at /dashboard displayed the Insight
 *      Lab instruction and the final step completed the walkthrough on the spot.
 *      The tests assert the property that makes that impossible: a step off its
 *      page yields NAVIGATE and nothing else, and its index does not move.
 *
 *   2. DRIFTING COPY. "48 servers across SYD and MEL data centres" outlived a
 *      fourfold growth in the dataset. An unresolved placeholder must be reported
 *      and rendered as a visible gap, never as a plausible default.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const F = require('../moke-flow.js');

const FLOWS = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../../data/flows.json'), 'utf8'));

let failures = 0;
let checks = 0;

function ok(cond, msg) {
  checks++;
  if (!cond) { failures++; console.error('  FAIL: ' + msg); }
}
function eq(a, b, msg) {
  ok(a === b, msg + ' (got ' + JSON.stringify(a) + ', expected ' + JSON.stringify(b) + ')');
}

// ── The shipped flow is valid ──────────────────────────────────────────────
ok(Array.isArray(FLOWS.flows) && FLOWS.flows.length >= 1, 'flows.json has at least one flow');
FLOWS.flows.forEach(function (flow) {
  const problems = F.validateFlow(flow);
  ok(problems.length === 0,
     'flow ' + flow.id + ' is valid' + (problems.length ? ': ' + problems.join('; ') : ''));
});

const flow = FLOWS.flows[0];
eq(flow.steps.length, 8, 'the ported flow keeps all eight steps');

// ── validateFlow rejects what it should ────────────────────────────────────
ok(F.validateFlow(null).length > 0, 'null is not a flow');
ok(F.validateFlow({ id: 'x' }).length > 0, 'a flow with no steps is rejected');
ok(F.validateFlow({ id: 'x', steps: [{ kind: 'teleport', page: '/', narration: 'n' }] })
   .some(function (p) { return p.indexOf('unknown kind') !== -1; }),
   'an unknown step kind is reported');
ok(F.validateFlow({ id: 'x', steps: [{ kind: 'load', page: '/', narration: 'n' }] })
   .some(function (p) { return p.indexOf('needs a dataset') !== -1; }),
   'a load step without a dataset is reported');
ok(F.validateFlow({ id: 'x', steps: [{ kind: 'prompt', page: '/chat', narration: 'n' }] })
   .some(function (p) { return p.indexOf('needs a prompt') !== -1; }),
   'a prompt step without a prompt is reported');
ok(F.validateFlow({ id: 'x', steps: [{ kind: 'note', page: '/', narration: '' }] })
   .some(function (p) { return p.indexOf('no narration') !== -1; }),
   'a step with no narration is reported');

// ── THE OFF-BY-ONE, as a property over every step of the real flow ─────────
// Off its page, a step may only navigate. It may never also advance, which is
// exactly what the three broken closures did.
flow.steps.forEach(function (step, i) {
  const elsewhere = step.page === '/nowhere' ? '/other' : '/nowhere';
  const plan = F.planStep(flow, i, elsewhere);
  eq(plan.action, F.NAVIGATE, 'step ' + i + ' off its page navigates');
  eq(plan.to, step.page, 'step ' + i + ' navigates to its own page');
  eq(plan.index, i, 'step ' + i + ' does not advance while navigating');
});

// And on its page, the plan is the step's own action — so the narration the user
// reads is the narration for the thing they are about to do.
flow.steps.forEach(function (step, i) {
  const plan = F.planStep(flow, i, step.page);
  const expected = { load: F.LOAD, prompt: F.FILL, dashboard: F.GENERATE,
                     navigate: F.ADVANCE, note: F.ADVANCE }[step.kind];
  eq(plan.action, expected, 'step ' + i + ' (' + step.kind + ') on its page plans ' + expected);
});

// The specific three that were broken. Step 3 is the dashboard, 4 the Insight
// Lab, 7 governance — each of which used to show the *next* step's text.
[3, 4, 7].forEach(function (i) {
  const narration = F.stepNarration(flow, i, {});
  const onOwnPage = F.planStep(flow, i, flow.steps[i].page);
  eq(onOwnPage.index, i, 'step ' + i + ' shows its own index on its own page');
  ok(narration.title.length > 0, 'step ' + i + ' has its own title to show');
  eq(narration.indicator, 'Step ' + (i + 1) + ' of 8', 'step ' + i + ' indicator is right');
});

// The last step completes only after it has been performed, not on arrival.
eq(F.planStep(flow, 7, '/governance').action, F.ADVANCE,
   'the final step is performable rather than instantly complete');
eq(F.planStep(flow, 8, '/governance').action, F.DONE, 'past the end is done');
eq(F.planStep(flow, -1, '/').action, F.DONE, 'a negative index is done, not a crash');

// ── waitFor ───────────────────────────────────────────────────────────────
const promptStep = flow.steps.findIndex(function (s) { return s.waitFor; });
ok(promptStep >= 0, 'at least one step waits for a selector');
eq(F.planStep(flow, promptStep, flow.steps[promptStep].page, function () { return false; }).action,
   F.WAIT, 'a step whose selector is absent waits instead of acting');
eq(F.planStep(flow, promptStep, flow.steps[promptStep].page, function () { return true; }).action,
   flow.steps[promptStep].kind === 'prompt' ? F.FILL : F.ADVANCE,
   'and acts once the selector is present');
// Absent a present() function the pure path must not block.
ok(F.planStep(flow, promptStep, flow.steps[promptStep].page).action !== F.WAIT,
   'with no DOM probe supplied the interpreter does not wait forever');

// ── Path handling ─────────────────────────────────────────────────────────
ok(F.samePath('/', ''), 'empty path is the root');
ok(F.samePath('/chat/', '/chat'), 'a trailing slash does not change the page');
ok(F.samePath('/chat?x=1', '/chat'), 'a query string does not change the page');
ok(F.samePath('/chat#top', '/chat'), 'a fragment does not change the page');
ok(!F.samePath('/chat', '/chatter'), 'a prefix is not a match');

// ── Narration templating ──────────────────────────────────────────────────
const ctx = {
  dataset: { name: 'IT Server Hardware', rowcount: 200, columncount: 34,
             sensitivity: 'CONFIDENTIAL' }
};
const first = F.stepNarration(flow, 0, ctx);
eq(first.missing.length, 0, 'step 0 resolves against a full context');
ok(first.narration === undefined, 'stepNarration returns text, not a narration field');
ok(first.text.indexOf('200') !== -1, 'the real row count is rendered');
ok(first.text.indexOf('48') === -1, 'the stale 48 cannot come back — it is not in the flow');
ok(first.title.indexOf('IT Server Hardware') !== -1, 'the dataset name is templated into the title');

// The important half: a missing value is reported and visibly absent.
const partial = F.stepNarration(flow, 0, { dataset: { name: 'X' } });
ok(partial.missing.indexOf('dataset.rowcount') !== -1, 'a missing count is reported');
ok(partial.text.indexOf('[dataset.rowcount unavailable]') !== -1,
   'and rendered as a visible gap rather than a plausible number');
ok(!/\b\d{2,}\b/.test(partial.text.replace(/unavailable/g, '')),
   'no invented figure appears when the context is incomplete');

const empty = F.stepNarration(flow, 0, {});
ok(empty.missing.length >= 3, 'an empty context reports every placeholder');

// render() directly
eq(F.render('{{a.b}}', { a: { b: 'x' } }).text, 'x', 'nested lookup');
eq(F.render('no placeholders', {}).text, 'no placeholders', 'plain text passes through');
eq(F.render('{{ a }}', { a: 'spaced' }).text, 'spaced', 'whitespace in the braces is tolerated');
eq(F.render(null, {}).text, '', 'null text renders empty, not "null"');
eq(F.render('{{a}}', { a: 0 }).text, '0', 'zero is a value, not a missing one');
ok(F.render('{{a}}', { a: '' }).missing.length === 1, 'an empty string counts as missing');

// ── Progress and labels ───────────────────────────────────────────────────
eq(F.stepNarration(flow, 7, ctx).progress, 1, 'the last step is 100% progress');
ok(F.stepNarration(flow, 0, ctx).progress > 0, 'the first step shows some progress');
eq(F.stepNarration(flow, 2, ctx).prompt, 'Show servers with expired warranties',
   'a prompt step exposes its prompt for the chip');
eq(F.stepNarration(flow, 1, ctx).prompt, null, 'a non-prompt step exposes no chip');


// ── MK20.3: the cross-domain flow must actually contrast ──────────────────
// Its whole point is one pipeline over two datasets with opposite redaction
// outcomes. A flow that loaded two similar datasets would look the same and
// demonstrate nothing, so the contrast is asserted rather than assumed.
const cross = FLOWS.flows.find(function (f) { return f.id === 'cross-domain'; });
ok(!!cross, 'a cross-domain flow exists');
if (cross) {
  ok(F.validateFlow(cross).length === 0, 'the cross-domain flow is valid');
  const loads = cross.steps.filter(function (s) { return s.kind === 'load'; });
  eq(loads.length, 2, 'it loads exactly two datasets');
  ok(loads[0].dataset !== loads[1].dataset, 'and they are different datasets');

  // One public, one with people in it. Checked on the narration, because that is
  // what the presenter says out loud and what a viewer will hold us to.
  const all = cross.steps.map(function (s) { return s.narration; }).join(' ');
  ok(/CC BY|public/i.test(all), 'the first half is identified as public data');
  ok(/SYNTHETIC/.test(all),
     'the patient fixture is called synthetic in capitals — it imitates MBS claims '
     + 'and must never read as real health data');
  ok(/fabricated/i.test(all), 'and the narration says the values are fabricated');

  // The flow must not overclaim. These are the exact phrases withdrawn from the
  // website, and a demo script is as public as a web page.
  ['architecturally impossible', 'never sees real data', 'cannot be bypassed',
   'no data leaves'].forEach(function (phrase) {
    ok(all.toLowerCase().indexOf(phrase) === -1,
       'the narration does not contain the withdrawn claim "' + phrase + '"');
  });
  ok(/bypass/i.test(all), 'and it names the bypass limitation rather than omitting it');

  // Every flow needs a duration for the picker to list.
  FLOWS.flows.forEach(function (f) {
    ok(typeof f.duration_mins === 'number' && f.duration_mins > 0,
       'flow ' + f.id + ' states a duration the picker can show');
    ok(typeof f.title === 'string' && f.title.length > 10,
       'flow ' + f.id + ' has a title worth listing');
  });
}

// ── MK20.3: every flow's claims checked against the real data ─────────────
// The manifest gives each dataset's sensitivity, declared PII, kind and
// provenance; its columns are the header of the CSV the store actually serves,
// read through the production parser. checkClaims (moke-flow.js) is what judges.
require('../moke-data.js');
const MD = globalThis.MokeData;
const STATIC = path.resolve(__dirname, '../..');
const MANIFEST = JSON.parse(fs.readFileSync(path.join(STATIC, 'data/manifest.json'), 'utf8'));
const CLAIMS_DATA = {};
MANIFEST.datasets.forEach(function (m) {
  const file = path.join(STATIC, m.data.path.replace(/^\/static\//, ''));
  const headers = MD.parseCSV(fs.readFileSync(file, 'utf8')).headers;
  CLAIMS_DATA[m.id] = { sensitivity: m.sensitivity, pii: m.pii || [], kind: m.kind,
                     columns: headers, provenance: m.provenance || {}, listed: m.listed !== false };
});

// The mechanism the "redacted" claims rest on: moke's request names the dataset's
// declared PII columns for redaction. If chat.tkt stopped doing that, every
// flow's redaction claim would be false, so the claim is tied to the code.
const CHAT = fs.readFileSync(path.resolve(STATIC, '../templates/chat.tkt'), 'utf8');
ok(/PII columns \(will be redacted\): ' \+ dataset\.pii\.join/.test(CHAT),
   'chat.tkt still names the declared PII columns for redaction, which every redaction claim relies on');

FLOWS.flows.forEach(function (f) {
  const problems = F.checkClaims(f, CLAIMS_DATA);
  ok(problems.length === 0, 'flow ' + f.id + ' says only what is true of its data'
     + (problems.length ? ':\n      ' + problems.join('\n      ') : ''));
  // The withdrawn claims, over every flow (titles, narration and prompts).
  const text = f.steps.map(function (s) { return [s.title, s.narration, s.prompt].join(' '); })
    .join(' ').toLowerCase();
  F.WITHDRAWN.forEach(function (phrase) {
    ok(text.indexOf(phrase) === -1, 'flow ' + f.id + ' does not contain the withdrawn claim "' + phrase + '"');
  });
  ok(typeof f.duration_mins === 'number' && f.duration_mins > 0,
     'flow ' + f.id + ' states a duration the picker can show');
  ok(f.steps.some(function (s) { return s.kind === 'load'; }), 'flow ' + f.id + ' loads a dataset');
});
eq(new Set(FLOWS.flows.map(function (f) { return f.id; })).size, FLOWS.flows.length, 'flow ids are unique');

// A flow for every listed dataset. A gap is allowed only while the reason for it
// is still true, so fixing the reason forces the flow to be written.
const KNOWN_GAPS = {
  // MK20.3a: labelled PUBLIC yet declares operator_name as PII. A flow must say a
  // PUBLIC dataset has nothing redacted, and here that would be false.
  'au.water': function (d) { return d.sensitivity === 'PUBLIC' && d.pii.length > 0; }
};
const covered = {};
FLOWS.flows.forEach(function (f) {
  f.steps.forEach(function (s) { if (s.kind === 'load') covered[s.dataset] = true; });
});
Object.keys(CLAIMS_DATA).filter(function (id) { return CLAIMS_DATA[id].listed; }).forEach(function (id) {
  if (KNOWN_GAPS[id]) {
    ok(!covered[id] && KNOWN_GAPS[id](CLAIMS_DATA[id]),
       'listed dataset ' + id + ' is a known gap only while its reason holds — if it no longer does, write its flow');
  } else {
    ok(!!covered[id], 'listed dataset ' + id + ' has a flow');
  }
});
Object.keys(covered).forEach(function (id) {
  ok(CLAIMS_DATA[id] && CLAIMS_DATA[id].listed, 'flows load only listed datasets (' + id + ')');
});

// checkClaims itself fails what it should. Each case is a real flow with one
// claim made false, so these hold however the shipped flows change.
function mutated(id, edit) {
  const f = JSON.parse(JSON.stringify(FLOWS.flows.find(function (x) { return x.id === id; })));
  edit(f);
  return F.checkClaims(f, CLAIMS_DATA);
}
function fails(problems, needle, msg) {
  ok(problems.some(function (p) { return p.indexOf(needle) !== -1; }),
     msg + ' (got ' + JSON.stringify(problems) + ')');
}
fails(mutated('wc-users', function (f) { f.steps[1].narration = f.steps[1].narration.replace('full_name', 'fullname_x'); }),
      'names column fullname_x', 'a flow naming a column its dataset lacks fails');
fails(mutated('cross-domain', function (f) { f.steps[4].narration += ' The request also names claim_ref for redaction.'; }),
      'names column claim_ref', 'a column borrowed from nowhere fails even in a dataset with PII');
fails(mutated('au-employment', function (f) { f.steps[0].outcome.redacted = ['industry_name']; }),
      'claims redaction on PUBLIC dataset au.employment', 'a PUBLIC flow claiming redaction in its outcome fails');
fails(mutated('au-employment', function (f) { f.steps[1].narration = 'The request names industry_name for redaction.'; }),
      'claims redaction on au.employment', 'a PUBLIC flow claiming redaction in its narration fails');
fails(mutated('au-employment', function (f) { f.steps[1].narration = 'Read the schema panel.'; }),
      'never says that nothing in au.employment is redacted', 'a PUBLIC flow that does not say nothing is redacted fails');
fails(mutated('au-property', function (f) { f.steps[0].outcome.sensitivity = 'PUBLIC'; }),
      'claims sensitivity PUBLIC', 'a wrong sensitivity fails');
fails(mutated('au-property', function (f) { f.steps[0].outcome.redacted = ['vendor_name']; }),
      'but au.property declares', 'claiming fewer redacted columns than declared fails');
fails(mutated('au-property', function (f) { f.steps[1].narration = f.steps[1].narration.replace('vendor_name and purchaser_name', 'vendor_name, purchaser_name and property_address'); }),
      'claims property_address of au.property is redacted', 'claiming redaction of an undeclared column fails');
fails(mutated('wc-orders', function (f) { f.steps[0].narration = f.steps[0].narration.replace('SYNTHETIC', 'real'); }),
      'must say SYNTHETIC', 'a synthetic dataset not badged synthetic fails');
fails(mutated('cross-domain', function (f) { f.steps[0].narration = f.steps[0].narration.replace('CC BY', 'an open licence'); }),
      'must name its licence', 'a real dataset without its licence fails');
fails(mutated('cross-domain', function (f) { f.steps[0].narration = f.steps[0].narration.replace('Bureau of Infrastructure and Transport Research Economics', 'the government'); }),
      'must name its publisher', 'a real dataset without its publisher fails');
fails(mutated('wc-users', function (f) { f.steps[0].narration += ' Redaction cuts disclosure by 40%.'; }),
      'states a figure', 'a figure in narration fails');
fails(mutated('wc-users', function (f) { f.steps[3].narration += ' No data leaves the device.'; }),
      'withdrawn claim "no data leaves"', 'a withdrawn claim fails');

if (failures) {
  console.error('\ntest-moke-flow: ' + failures + ' of ' + checks + ' checks FAILED');
  process.exit(1);
}
console.log('test-moke-flow: ' + checks + ' checks passed (every flow\'s claims checked against its data)');
