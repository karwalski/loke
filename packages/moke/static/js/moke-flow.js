/*
 * moke-flow.js — the declarative demo flow interpreter (stories MK20.1, MK20.2)
 *
 * WHY THIS EXISTS
 *
 * The guided walkthrough was eight imperative closures in templates/base.tkt,
 * each hand-writing sessionStorage and navigation. Two problems followed from the
 * shape rather than from any one line of it.
 *
 * 1. A THREE-STEP OFF-BY-ONE. Each closure wrote the next step index itself, and
 *    three of them wrote it *before* navigating. The dashboard step set index 4
 *    and went to /dashboard, where step 4 is "Run clustering in Insight Lab" — so
 *    arriving at the dashboard displayed the clustering instruction. The same
 *    happened on /insight, and the governance step set index 8 against a
 *    length-8 flow, completing the walkthrough the moment it was started. Three
 *    of eight steps never showed their own text on their own page.
 *
 *    The interpreter makes that unrepresentable: a step advances only once the
 *    browser is already on its page. Navigation and advancement are separate
 *    outcomes of planStep(), never the same one.
 *
 * 2. COPY THAT DRIFTS FROM DATA. Step one read "48 servers across SYD and MEL
 *    data centres" long after the dataset had grown to 200 servers across four.
 *    Narration is now a template resolved against the live dataset, and an
 *    unresolved placeholder is reported rather than rendered — so the failure mode
 *    is a visible gap, not a confident wrong number.
 *
 * THE FIVE STEP KINDS
 *
 *   load       load a dataset by id, on the page that owns the loader
 *   navigate   go to a page and narrate what to look at
 *   prompt     fill the chat input with a suggested prompt
 *   dashboard  go to the dashboard and generate
 *   note       narration only, no action
 *
 * Every step carries `page` (where it must happen), `narration`, an optional
 * `waitFor` CSS selector so a flow cannot race a slow page, and an optional
 * `actionLabel`.
 *
 * Run the tests: node packages/moke/static/js/tests/test-moke-flow.js
 */
(function (global) {
  'use strict';

  var KINDS = ['load', 'navigate', 'prompt', 'dashboard', 'note'];

  // Outcomes planStep can return. Deliberately small, and deliberately does not
  // include "navigate and advance": that combination is the original bug.
  var NAVIGATE = 'navigate';   // go to step.page, stay on this step
  var LOAD = 'load';           // load step.dataset, then advance
  var FILL = 'fill';           // put step.prompt in the input, then advance
  var GENERATE = 'generate';   // trigger dashboard generation, then advance
  var ADVANCE = 'advance';     // nothing to do here but move on
  var WAIT = 'wait';           // step.waitFor is not present yet
  var DONE = 'done';           // past the end of the flow

  var PLACEHOLDER = /\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g;

  function get(ctx, path) {
    var parts = String(path).split('.');
    var cur = ctx;
    for (var i = 0; i < parts.length; i++) {
      if (cur === null || cur === undefined) return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }

  /* Resolve {{placeholders}} in narration against a context.
   *
   * Returns { text, missing } rather than throwing, because a flow with one stale
   * placeholder should still run — but the caller is told, and the rendered text
   * says so where the number would have been. Silently substituting a default is
   * how "48 servers" survived a fourfold change in the data.
   */
  function render(text, ctx) {
    var missing = [];
    var out = String(text === null || text === undefined ? '' : text)
      .replace(PLACEHOLDER, function (_, path) {
        var v = get(ctx || {}, path);
        if (v === undefined || v === null || v === '') {
          missing.push(path);
          return '[' + path + ' unavailable]';
        }
        return String(v);
      });
    return { text: out, missing: missing };
  }

  /* Validate a flow before it is ever run.
   *
   * A flow is data, and may come from a manifest, so it is checked rather than
   * trusted. Returns an array of problems; empty means usable.
   */
  function validateFlow(flow) {
    var problems = [];
    if (!flow || typeof flow !== 'object') return ['flow is not an object'];
    if (!flow.id) problems.push('flow has no id');
    if (!Array.isArray(flow.steps) || !flow.steps.length) {
      problems.push('flow has no steps');
      return problems;
    }
    flow.steps.forEach(function (step, i) {
      var at = 'step ' + i + (step && step.title ? ' (' + step.title + ')' : '');
      if (!step || typeof step !== 'object') { problems.push(at + ' is not an object'); return; }
      if (KINDS.indexOf(step.kind) === -1) {
        problems.push(at + ': unknown kind ' + JSON.stringify(step.kind));
      }
      if (!step.page) problems.push(at + ': no page');
      if (!step.narration) problems.push(at + ': no narration');
      if (step.kind === 'load' && !step.dataset) problems.push(at + ': load step needs a dataset');
      if (step.kind === 'prompt' && !step.prompt) problems.push(at + ': prompt step needs a prompt');
    });
    return problems;
  }

  /* What should happen right now?
   *
   * Pure: takes the flow, the step index and the current path, and returns what to
   * do. All the sessionStorage and window.location handling lives in the caller,
   * which is what makes the step semantics testable at all — the old closures
   * could not be tested without a browser.
   *
   * @param present optional function(selector) -> bool, for waitFor. Defaults to
   *        treating every selector as present, so the pure path needs no DOM.
   */
  function planStep(flow, index, currentPath, present) {
    var steps = (flow && flow.steps) || [];
    if (index < 0 || index >= steps.length) return { action: DONE };
    var step = steps[index];

    // Not on the step's page yet: go there and stay on this step. The step's own
    // narration is then shown on its own page, which is the whole fix.
    if (samePath(currentPath, step.page) === false) {
      return { action: NAVIGATE, to: step.page, step: step, index: index };
    }

    // On the right page, but the thing the step needs has not rendered yet.
    if (step.waitFor && typeof present === 'function' && !present(step.waitFor)) {
      return { action: WAIT, selector: step.waitFor, step: step, index: index };
    }

    switch (step.kind) {
      case 'load':      return { action: LOAD, dataset: step.dataset, step: step, index: index };
      case 'prompt':    return { action: FILL, prompt: step.prompt, step: step, index: index };
      case 'dashboard': return { action: GENERATE, step: step, index: index };
      default:          return { action: ADVANCE, step: step, index: index };
    }
  }

  /* Path comparison that treats '/' and '' alike and ignores a trailing slash. */
  function samePath(a, b) {
    var na = normalisePath(a), nb = normalisePath(b);
    return na === nb;
  }

  function normalisePath(p) {
    var s = String(p === null || p === undefined ? '' : p);
    s = s.split('?')[0].split('#')[0];
    if (s.length > 1 && s.charAt(s.length - 1) === '/') s = s.slice(0, -1);
    return s === '' ? '/' : s;
  }

  /* The narration a step should display, with its context resolved. */
  function stepNarration(flow, index, ctx) {
    var steps = (flow && flow.steps) || [];
    var step = steps[index];
    if (!step) return { title: '', text: '', missing: [] };
    var t = render(step.title || '', ctx);
    var n = render(step.narration || '', ctx);
    return {
      title: t.text,
      text: n.text,
      missing: t.missing.concat(n.missing),
      actionLabel: step.actionLabel || defaultLabel(step.kind),
      prompt: step.kind === 'prompt' ? step.prompt : null,
      progress: steps.length ? ((index + 1) / steps.length) : 0,
      indicator: 'Step ' + (index + 1) + ' of ' + steps.length
    };
  }

  function defaultLabel(kind) {
    switch (kind) {
      case 'load': return 'Load dataset';
      case 'prompt': return 'Fill the prompt';
      case 'dashboard': return 'Generate dashboard';
      case 'navigate': return 'Go there';
      default: return 'Next';
    }
  }

  var api = {
    KINDS: KINDS,
    NAVIGATE: NAVIGATE, LOAD: LOAD, FILL: FILL, GENERATE: GENERATE,
    ADVANCE: ADVANCE, WAIT: WAIT, DONE: DONE,
    render: render,
    validateFlow: validateFlow,
    planStep: planStep,
    stepNarration: stepNarration,
    samePath: samePath,
    normalisePath: normalisePath
  };

  global.MokeFlow = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof window !== 'undefined' ? window : globalThis));
