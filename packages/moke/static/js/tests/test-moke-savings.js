/*
 * test-moke-savings.js — the savings ledger records only what loke measured (GA1.5c).
 *
 * Run: node packages/moke/static/js/tests/test-moke-savings.js
 *
 * Imports the real module. The replies below have the shape page.api.pipeline writes
 * (core.optimiser.prompt.reportjson): method, applied, reason, bytes_before/after and
 * chars_before/after, and no token field.
 *
 * The load-bearing assertions are that a row and the totals carry loke's octets exactly,
 * that nothing is derived from the text's length, and that token and cost savings read
 * "not measured" whatever the reply says, including a ledger stored by the old code.
 */
'use strict';

const S = require('../moke-savings.js');

let failures = 0;
let checks = 0;
function ok(cond, msg) { checks++; if (!cond) { failures++; console.error('  FAIL: ' + msg); } }
function eq(a, b, msg) { ok(a === b, msg + ' (got ' + JSON.stringify(a) + ', expected ' + JSON.stringify(b) + ')'); }

function memStore(init) {
  const m = Object.assign({}, init || {});
  return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, m };
}

const applied = {
  response: 'ok', model: 'fake', provider: 'ollama', tokens_in: 311, tokens_out: 40, cost_usd: 0,
  optimisation: { method: 'llmlingua', applied: true, reason: '', bytes_before: 2412,
                  bytes_after: 1377, chars_before: 2400, chars_after: 1370 }
};
const notApplied = {
  response: 'ok', model: 'fake', tokens_in: 9, tokens_out: 3, cost_usd: 0.000123,
  optimisation: { method: 'none', applied: false, reason: 'llmlingua_not_configured',
                  bytes_before: 57, bytes_after: 57, chars_before: 55, chars_after: 55 }
};
const noOpt = { response: 'ok', model: 'fake', tokens_in: 9, tokens_out: 3 };

// ── A row carries loke's measurement, exactly ──────────────────────────────
const e1 = S.entryFor(applied, { request: 1, model: 'fake', isLocal: true });
eq(e1.measured, true, 'a complete optimisation object is a measurement');
eq(e1.bytesBefore, 2412, 'bytes before are loke\'s');
eq(e1.bytesAfter, 1377, 'bytes after are loke\'s');
eq(e1.charsBefore, 2400, 'characters before are loke\'s');
eq(e1.charsAfter, 1370, 'characters after are loke\'s');
eq(e1.method, 'llmlingua', 'the method is loke\'s');
eq(e1.tokensIn, 311, 'tokens in are the provider\'s, as reported');
ok(!('tokensSaved' in e1) && !('costSaved' in e1), 'a row has no token or cost saving');
eq(S.optimisationCell(e1), 'llmlingua: 2412 → 1377 bytes', 'the row shows the measured octets');

const e2 = S.entryFor(notApplied, { request: 2, isLocal: false });
eq(e2.measured, true, 'a refused optimisation is still measured');
eq(S.optimisationCell(e2), 'none (llmlingua_not_configured): 57 bytes', 'and shows why, with its size');

// ── No measurement: say so, invent nothing ─────────────────────────────────
const e3 = S.entryFor(noOpt, { request: 3, isLocal: false });
eq(e3.measured, false, 'a reply without an optimisation object is not a measurement');
ok(!('bytesBefore' in e3), 'and no size is invented for it');
eq(S.optimisationCell(e3), 'not measured', 'its row says not measured');
eq(S.entryFor(null, {}).measured, false, 'no reply at all is not a measurement');
const partial = { optimisation: { method: 'toon', applied: true, bytes_before: 100, bytes_after: 60 } };
eq(S.entryFor(partial, {}).measured, false, 'a partial object (no characters) is not repaired into one');
const bad = { optimisation: { method: 'toon', applied: true, bytes_before: '100', bytes_after: 60,
                              chars_before: 100, chars_after: 60 } };
eq(S.entryFor(bad, {}).measured, false, 'a size that is not a number is not a measurement');

// ── Totals and the view ────────────────────────────────────────────────────
let t = S.accumulate(null, e1, 2);
t = S.accumulate(t, e2, 0);
t = S.accumulate(t, e3, 1);
eq(t.requests, 3, 'three requests');
eq(t.measuredRequests, 2, 'two of them measured');
eq(t.bytesBefore, 2412 + 57, 'bytes before sum the measured rows only');
eq(t.bytesAfter, 1377 + 57, 'bytes after sum the measured rows only');
eq(t.piiIntercepted, 3, 'entities are summed');
eq(t.localRequests + t.cloudRequests, 3, 'every request is routed somewhere');
const v = S.summary(t);
eq(v.bytesSaved, String(2412 - 1377), 'bytes saved is before minus after, measured');
eq(v.tokensSaved, 'not measured', 'tokens saved is not measured');
eq(v.costSaved, 'not measured', 'cost saved is not measured');
ok(/measured by loke/.test(v.bytesDetail), 'and the byte figure is attributed to loke');

const none = S.summary(S.accumulate(null, e3, 0));
eq(none.bytesSaved, 'not measured', 'with nothing measured, bytes saved says so');

// ── A ledger written by the old code ───────────────────────────────────────
const legacy = { tokensSaved: 1234, costSaved: 0.0185, piiIntercepted: 4, localRequests: 2, cloudRequests: 1 };
const lt = S.accumulate(legacy, e3, 0);
ok(!('tokensSaved' in lt) && !('costSaved' in lt), 'an old ledger\'s invented savings are dropped');
eq(lt.piiIntercepted, 4, 'and its counts are kept');
eq(S.summary(legacy).tokensSaved, 'not measured', 'and the view never shows them');

// ── record() through storage, as the chat page calls it ───────────────────
const st = memStore({ moke_savings: JSON.stringify(legacy) });
const r1 = S.record(st, applied, { model: 'fake', isLocal: true, timestamp: 'x' }, 1);
eq(r1.request, 1, 'the first row is request 1');
const stored = JSON.parse(st.m.moke_savings);
ok(!('tokensSaved' in stored) && !('costSaved' in stored), 'the stored ledger holds no invented saving');
eq(stored.bytesBefore, 2412, 'the stored ledger holds loke\'s octets');
const hist = JSON.parse(st.m.moke_savings_history);
eq(hist.length, 1, 'one history row');
eq(hist[0].bytesAfter, 1377, 'the history row holds loke\'s octets');
S.record(st, noOpt, { isLocal: false }, 0);
eq(JSON.parse(st.m.moke_savings_history)[1].measured, false, 'a reply with no measurement is recorded as unmeasured');
eq(S.load(st).totals.measuredRequests, 1, 'load reads the totals back');

// ── Pre-send: the question's size, and no token or cost figure ─────────────
const ps = S.preSend('summarise the weather data for the week please');
ok(/^46 characters, 46 bytes as typed\./.test(ps), 'pre-send gives characters and bytes as typed: ' + ps);
ok(/not measured/.test(ps), 'and says tokens and cost are not measured');
ok(!/\$|~\d+ tokens/.test(ps), 'and shows no token count or price');
eq(S.preSend('café').indexOf('4 characters, 5 bytes'), 0, 'characters and UTF-8 bytes are counted separately');

console.log((failures ? 'FAILED ' : 'ok ') + (checks - failures) + '/' + checks + ' savings ledger checks');
process.exit(failures ? 1 : 0);
