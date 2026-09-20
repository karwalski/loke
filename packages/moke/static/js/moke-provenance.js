/*
 * moke-provenance.js — one definition of what a card's number is allowed to claim
 * (stories NC1.5, NC1.6, MK20.4)
 *
 * WHY THIS EXISTS
 *
 * The rule it enforces was already written, correctly, inside
 * templates/dashboard.tkt: the model receives a schema profile and no rows, so
 * any value-shaped field in its reply is invented, and a card may only say it was
 * "computed locally" when it actually was.
 *
 * The rule lived in one template and the presentation page did not have it. What
 * presentation mode did instead was render four hardcoded slides asserting
 * "12,489 unique customers", "+8.4% vs prior period", "inertia 142.3, 23
 * iterations" and "Count computed locally — no data left the device" over figures
 * produced by Math.random() and a literal array. It showed those slides *whether
 * or not* a real dashboard was loaded, so loading your own data and pressing
 * Present produced someone else's invented numbers under a local-computation
 * claim. A presentation is the surface most likely to be shown to other people,
 * which makes it the worst place in the product for that to be true.
 *
 * Copying the rule into a second template would have produced two definitions
 * that drift. This module is the single one. dashboard.tkt binds its local names
 * to these functions; presentation.tkt calls them directly.
 *
 * THE VOCABULARY
 *
 *   resolved    computed here from the loaded rows. The ONLY state that may
 *               carry a number, and the only one that may say it was computed.
 *   unresolved  the artifact referenced a column or operation that could not be
 *               matched against the loaded data. The reason names it.
 *   no-data     no dataset is loaded, so nothing could be computed at all.
 *
 * Unknown provenance is never treated as resolved. That default is the reason a
 * missing field degrades to "not computed" rather than to a number.
 *
 * Run the tests: node packages/moke/static/js/tests/test-moke-provenance.js
 */
(function (global) {
  'use strict';

  var RESOLVED = 'resolved';
  var UNRESOLVED = 'unresolved';
  var NO_DATA = 'no-data';
  var STATES = [RESOLVED, UNRESOLVED, NO_DATA];

  var DEFAULT_REASON =
    'This card was not resolved against the loaded data in this session, ' +
    'so no value is shown.';

  // A label of the form 'Total customers [12,483]' smuggles a number out through
  // the display channel, so the bracketed tail is removed with the value fields.
  var BRACKETED_TAIL = /\s*\[.*?\]\s*$/;

  /* NC1.5 — delete every value-shaped field a model could have supplied.
   *
   * Runs before anything can read them, and over saved templates too: a stored
   * value was computed in some earlier session against possibly some other
   * dataset, and cannot be attested to now.
   */
  function stripUnverifiedValues(ddlObj) {
    ((ddlObj && ddlObj.cards) || []).forEach(function (card) {
      if (!card) return;
      delete card.provenance;
      var m = card.metric, c = card.chart, t = card.table;
      if (m) {
        delete m.resolved_value; delete m.resolved_label;
        delete m.value; delete m.data; delete m.delta; delete m.resolved_delta;
        if (typeof m.label === 'string') m.label = m.label.replace(BRACKETED_TAIL, '');
      }
      if (c) {
        delete c.resolved_data; delete c.data;
        delete c.labels; delete c.values; delete c.datasets;
      }
      if (t) {
        delete t.resolved_rows; delete t.resolved_columns;
        delete t.rows; delete t.data;
      }
    });
    return ddlObj;
  }

  function setProvenance(card, state, reason, note) {
    card.provenance = { state: state, reason: reason || '', note: note || '' };
    return card;
  }

  function cardState(card) {
    var p = card && card.provenance;
    if (p && STATES.indexOf(p.state) !== -1) return p.state;
    return UNRESOLVED;
  }

  function cardReason(card) {
    var p = card && card.provenance;
    if (p && p.reason) return p.reason;
    return DEFAULT_REASON;
  }

  function cardNote(card) {
    var p = card && card.provenance;
    return (p && p.note) ? p.note : '';
  }

  function markAllCards(ddlObj, state, reason) {
    ((ddlObj && ddlObj.cards) || []).forEach(function (card) {
      setProvenance(card, state, reason);
    });
    return ddlObj;
  }

  /* Does this chart carry a series computed on this device? */
  function chartHasLocalData(c) {
    if (!c) return false;
    if (c.resolved_data && Array.isArray(c.resolved_data.labels)
        && c.resolved_data.labels.length) return true;
    // Scatter cards handed over by the Insight Lab carry locally computed points.
    if (String(c.chart_type || '').toLowerCase() === 'scatter'
        && Array.isArray(c.data) && c.data.length) return true;
    return false;
  }

  /* May this card display a number at all?
   *
   * The single question every render slot should ask. It is deliberately not
   * "does the card have a value" — a card can carry a value and still be
   * inadmissible, which is the whole point of NC1.5.
   */
  function mayDisplayValue(card) {
    return cardState(card) === RESOLVED;
  }

  /* The wording a card is allowed to use about where its number came from.
   *
   * Only a resolved card may say "computed locally". Everything else gets a
   * phrase that does not assert computation, so a caption cannot drift away from
   * the card's actual state — which is how the presentation slides came to say
   * "Count computed locally" about a hardcoded string.
   */
  function provenanceCaption(card) {
    switch (cardState(card)) {
      case RESOLVED:
        return 'Computed locally from the loaded rows. No row values were sent.';
      case NO_DATA:
        return 'No dataset is loaded, so nothing was computed.';
      default:
        return 'Not computed against the loaded data. ' + cardReason(card);
    }
  }

  /* Which slide shape, if any, may this card become?
   *
   * Two conditions, and both matter. The card must be allowed to display a value
   * at all, and the specific shape it needs must actually be present. A card
   * marked resolved whose resolved_value is missing is a bug upstream, and the
   * honest response is to leave it out rather than render an empty figure or
   * substitute one — substituting one is exactly what presentation mode used to
   * do.
   *
   * Returns 'metric' | 'chart' | 'table' | null.
   */
  function presentableKind(card) {
    if (!mayDisplayValue(card)) return null;
    var m = card.metric, c = card.chart, t = card.table;
    if (m && m.resolved_value !== undefined && m.resolved_value !== null
        && m.resolved_value !== '') return 'metric';
    if (c && chartHasLocalData(c)) return 'chart';
    if (t && Array.isArray(t.resolved_rows) && t.resolved_rows.length) return 'table';
    return null;
  }

  /* Would this DDL render as a presentation with any real content?
   *
   * Used by presentation mode to decide between showing slides and showing the
   * empty state. A DDL whose every card is unresolved has nothing to present, and
   * saying so is better than presenting a deck of "not computed" cards.
   */
  function resolvedCards(ddlObj) {
    return ((ddlObj && ddlObj.cards) || []).filter(mayDisplayValue);
  }

  var api = {
    RESOLVED: RESOLVED,
    UNRESOLVED: UNRESOLVED,
    NO_DATA: NO_DATA,
    STATES: STATES,
    DEFAULT_REASON: DEFAULT_REASON,
    stripUnverifiedValues: stripUnverifiedValues,
    setProvenance: setProvenance,
    cardState: cardState,
    cardReason: cardReason,
    cardNote: cardNote,
    markAllCards: markAllCards,
    chartHasLocalData: chartHasLocalData,
    mayDisplayValue: mayDisplayValue,
    presentableKind: presentableKind,
    provenanceCaption: provenanceCaption,
    resolvedCards: resolvedCards
  };

  global.MokeProvenance = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof window !== 'undefined' ? window : globalThis));
