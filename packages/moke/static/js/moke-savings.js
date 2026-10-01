/*
 * moke-savings.js — the savings ledger, from what loke measured and nothing else (GA1.5c)
 *
 * WHY THIS EXISTS
 *
 * The A4.3 ledger in chat.tkt counted "tokens saved" as the text's length over four
 * minus the provider's tokens_in, and "cost saved" by pricing that difference, or a
 * local request's whole prompt, at one hard-coded rate per 1K tokens described as
 * "the most expensive model". None of the three was measured: length / 4 is not a
 * tokeniser, tokens_in counts a different text (the anonymised, possibly optimised
 * prompt plus the system prompt), and the rate was not the price of any model the
 * request could have used. The governance page then showed those figures as savings.
 *
 * What loke does measure is its optimiser's outcome: since GA1.5 every /api/pipeline
 * reply carries an `optimisation` object with the method, whether it was applied, the
 * reason when it was not, and the octets and UTF-8 characters before and after. No
 * token count, because no tokeniser is named. So the ledger records those, and token
 * and cost savings are shown as "not measured" until a named tokeniser and a real
 * price table exist (docs/metrics-baseline.md publishes no such figure).
 *
 * The provider's tokens_in / tokens_out and loke's cost_usd are carried through as
 * loke reported them; this module computes nothing from them.
 *
 * Run the tests: node packages/moke/static/js/tests/test-moke-savings.js
 */
(function (root) {
  'use strict';

  var NOT_MEASURED = 'not measured';
  var LEDGER_KEY = 'moke_savings';
  var HISTORY_KEY = 'moke_savings_history';

  function count(v) {
    return typeof v === 'number' && isFinite(v) && v >= 0 && Math.floor(v) === v;
  }

  // loke's `optimisation` object, or null when the reply carries no complete one.
  // Every size must be a whole, non-negative number as loke wrote it: a partial or
  // malformed object is not a measurement, and is not repaired into one.
  function optimisationOf(reply) {
    var o = reply && typeof reply === 'object' ? reply.optimisation : null;
    if (!o || typeof o !== 'object' || typeof o.method !== 'string' || o.method === '') return null;
    if (!count(o.bytes_before) || !count(o.bytes_after) ||
        !count(o.chars_before) || !count(o.chars_after)) return null;
    return {
      method: o.method,
      applied: o.applied === true,
      reason: typeof o.reason === 'string' ? o.reason : '',
      bytesBefore: o.bytes_before,
      bytesAfter: o.bytes_after,
      charsBefore: o.chars_before,
      charsAfter: o.chars_after
    };
  }

  function num(v) { return typeof v === 'number' && isFinite(v) ? v : 0; }

  // One history row for one reply. ctx: { request, timestamp, model, isLocal }.
  function entryFor(reply, ctx) {
    var c = ctx || {};
    var opt = optimisationOf(reply);
    var e = {
      request: c.request || 0,
      timestamp: c.timestamp || '',
      model: c.model || (reply && reply.model) || '',
      route: c.isLocal ? 'local' : 'cloud',
      tokensIn: num(reply && reply.tokens_in),
      tokensOut: num(reply && reply.tokens_out),
      cost: num(reply && reply.cost_usd),
      measured: !!opt
    };
    if (opt) {
      e.method = opt.method;
      e.applied = opt.applied;
      e.reason = opt.reason;
      e.bytesBefore = opt.bytesBefore;
      e.bytesAfter = opt.bytesAfter;
      e.charsBefore = opt.charsBefore;
      e.charsAfter = opt.charsAfter;
    }
    return e;
  }

  function emptyTotals() {
    return { requests: 0, measuredRequests: 0, bytesBefore: 0, bytesAfter: 0,
             charsBefore: 0, charsAfter: 0, piiIntercepted: 0, localRequests: 0, cloudRequests: 0 };
  }

  // A stored ledger, keeping only the measured fields. A ledger written before GA1.5c
  // holds tokensSaved and costSaved; those were invented, so they are dropped, not shown.
  function cleanTotals(t) {
    var out = emptyTotals();
    if (!t || typeof t !== 'object') return out;
    Object.keys(out).forEach(function (k) { if (count(t[k])) out[k] = t[k]; });
    return out;
  }

  function accumulate(totals, entry, entities) {
    var t = cleanTotals(totals);
    t.requests++;
    if (entry.route === 'local') t.localRequests++; else t.cloudRequests++;
    if (count(entities)) t.piiIntercepted += entities;
    if (entry.measured) {
      t.measuredRequests++;
      t.bytesBefore += entry.bytesBefore;
      t.bytesAfter += entry.bytesAfter;
      t.charsBefore += entry.charsBefore;
      t.charsAfter += entry.charsAfter;
    }
    return t;
  }

  // What the savings view shows. Only measured octets and characters carry a number.
  function summary(totals) {
    var t = cleanTotals(totals);
    var s = { tokensSaved: NOT_MEASURED, costSaved: NOT_MEASURED,
              bytesSaved: NOT_MEASURED, bytesDetail: 'loke reported no optimisation measurement' };
    if (t.measuredRequests > 0) {
      s.bytesSaved = String(t.bytesBefore - t.bytesAfter);
      s.bytesDetail = t.bytesBefore + ' → ' + t.bytesAfter + ' bytes over ' + t.measuredRequests +
        ' request' + (t.measuredRequests === 1 ? '' : 's') + ', measured by loke';
    }
    return s;
  }

  // One table cell describing a row's optimisation.
  function optimisationCell(e) {
    if (!e || e.measured !== true) return NOT_MEASURED;
    if (e.applied) return e.method + ': ' + e.bytesBefore + ' → ' + e.bytesAfter + ' bytes';
    return 'none (' + (e.reason || 'no reason given') + '): ' + e.bytesBefore + ' bytes';
  }

  function read(storage, key, fallback) {
    try { var v = JSON.parse(storage.getItem(key) || 'null'); return v == null ? fallback : v; }
    catch (_) { return fallback; }
  }

  // Record one reply in storage (sessionStorage in the page). Returns the new entry.
  function record(storage, reply, ctx, entities) {
    var history = read(storage, HISTORY_KEY, []);
    if (!Array.isArray(history)) history = [];
    var c = {};
    Object.keys(ctx || {}).forEach(function (k) { c[k] = ctx[k]; });
    c.request = history.length + 1;
    var e = entryFor(reply, c);
    var totals = accumulate(read(storage, LEDGER_KEY, null), e, entities);
    history.push(e);
    storage.setItem(LEDGER_KEY, JSON.stringify(totals));
    storage.setItem(HISTORY_KEY, JSON.stringify(history));
    return e;
  }

  function load(storage) {
    var h = read(storage, HISTORY_KEY, []);
    return { totals: cleanTotals(read(storage, LEDGER_KEY, null)), history: Array.isArray(h) ? h : [] };
  }

  function utf8Bytes(text) {
    if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(text).length;
    return Buffer.byteLength(text, 'utf8');
  }

  // The pre-send line (GA3.4). What can be known before sending is the size of the
  // question as typed; tokens and cost are counted by the provider after it answers.
  function preSend(text) {
    var chars = Array.from(text).length;
    return chars + ' characters, ' + utf8Bytes(text) + ' bytes as typed. Tokens and cost: ' +
      NOT_MEASURED + ' before sending (the provider reports them with its answer).';
  }

  var api = {
    NOT_MEASURED: NOT_MEASURED,
    optimisationOf: optimisationOf,
    entryFor: entryFor,
    accumulate: accumulate,
    summary: summary,
    optimisationCell: optimisationCell,
    record: record,
    load: load,
    preSend: preSend
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.mokeSavings = api;
})(typeof window !== 'undefined' ? window : this);
