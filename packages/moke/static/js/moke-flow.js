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

  /* ── MK20.3: is what a flow SAYS true of the data it loads? ──────────────
   *
   * A flow is presenter narration, said out loud to an audience, and a demo of a
   * privacy product that misdescribes its own data is worse than no demo. So the
   * claims a flow makes are checked against the dataset rather than trusted:
   *
   *   - every load step states its outcome as data, `outcome: { sensitivity,
   *     redacted }`, and that must equal the dataset's sensitivity and its
   *     declared PII columns — the columns moke's request names "PII columns (will
   *     be redacted)" (templates/chat.tkt). A PUBLIC dataset may claim nothing;
   *   - every snake_case column a step names must be a column of the dataset that
   *     step is about (the most recent load), so a misspelt or borrowed column fails;
   *   - a sentence that talks about redaction, masking or placeholders is a claim of
   *     redaction unless it is negated, and is allowed only where the dataset has
   *     columns to redact. Where it has none, the narration must say so;
   *   - a synthetic dataset is called SYNTHETIC and fabricated; a real one names its
   *     publisher and licence from the manifest;
   *   - no figures (they live in docs/metrics-baseline.md), and none of the claims
   *     withdrawn from the website.
   *
   * `datasets` maps id -> { sensitivity, pii, kind, columns, provenance }. Pure, so
   * the gate runs it over flows.json and the real CSV headers with no browser.
   * Returns an array of problems; empty means every claim checked out. */
  var WITHDRAWN = ['architecturally impossible', 'never sees real data',
                   'cannot be bypassed', 'no data leaves'];
  var REDACTION_WORD = /\b(redact\w*|mask\w*|placeholders?)\b/i;
  var NEGATION = /\b(no|not|nothing|none|never|neither|nor|zero)\b/i;
  var COLUMN_TOKEN = /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g;
  var STORY_ID = /\b[A-Z]{1,4}\d+(?:\.\d+)*[a-z]?\b/g;
  var NUMBER_WORD = /\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|hundred|thousand|million|dozen|percent)\b/i;
  var LICENCE_WORDS = { 'cc-by': /\bCC BY\b/, 'apache-2.0': /\bApache-2\.0\b/ };

  function sentencesOf(text) {
    return String(text || '').replace(PLACEHOLDER, 'X')
      .split(/[.!?;:](?:\s+|$)|\s—\s/)
      .filter(function (s) { return s.trim().length > 0; });
  }

  function namedColumns(text, extra) {
    var plain = String(text || '').replace(PLACEHOLDER, ' ');
    var found = plain.match(COLUMN_TOKEN) || [];
    (extra || []).forEach(function (c) {
      if (c.indexOf('_') === -1 && new RegExp('\\b' + c + '\\b').test(plain)) found.push(c);
    });
    return found;
  }

  function sameSet(a, b) {
    var x = (a || []).slice().sort(), y = (b || []).slice().sort();
    return x.length === y.length && x.every(function (v, i) { return v === y[i]; });
  }

  function checkClaims(flow, datasets) {
    var problems = [];
    var fid = (flow && flow.id) || '?';
    var steps = (flow && flow.steps) || [];
    var current = null;     // the id of the dataset the narration is about
    var said = {};          // id -> all text said while it was current

    steps.forEach(function (step, i) {
      var at = 'flow ' + fid + ' step ' + i;
      var words = [step.title, step.narration, step.prompt].filter(Boolean).join(' — ');
      var lower = words.toLowerCase();

      WITHDRAWN.forEach(function (phrase) {
        if (lower.indexOf(phrase) !== -1) problems.push(at + ': carries the withdrawn claim "' + phrase + '"');
      });
      var spoken = [step.title, step.narration].filter(Boolean).join(' ')
        .replace(PLACEHOLDER, ' ').replace(STORY_ID, ' ');
      if (/\d|%/.test(spoken) || NUMBER_WORD.test(spoken)) {
        problems.push(at + ': narration states a figure (figures live only in docs/metrics-baseline.md)');
      }

      if (step.kind === 'load') {
        var d = datasets[step.dataset];
        if (!d) { problems.push(at + ': loads ' + step.dataset + ', which the manifest does not list'); current = null; return; }
        current = step.dataset;
        var o = step.outcome;
        if (!o) {
          problems.push(at + ': load step states no outcome to check');
        } else {
          if (o.sensitivity !== d.sensitivity) {
            problems.push(at + ': claims sensitivity ' + o.sensitivity + ' but ' + step.dataset + ' is ' + d.sensitivity);
          }
          (o.redacted || []).forEach(function (c) {
            if ((d.columns || []).indexOf(c) === -1) problems.push(at + ': claims redaction of ' + c + ', which ' + step.dataset + ' does not have');
          });
          if (d.sensitivity === 'PUBLIC' && (o.redacted || []).length) {
            problems.push(at + ': claims redaction on PUBLIC dataset ' + step.dataset);
          }
          if (!sameSet(o.redacted, d.pii)) {
            problems.push(at + ': claims redaction of [' + (o.redacted || []).join(', ') + '] but '
                          + step.dataset + ' declares [' + (d.pii || []).join(', ') + ']');
          }
        }
        if (String(step.narration || '').indexOf('{{dataset.sensitivity}}') === -1 && String(step.narration || '').indexOf(d.sensitivity) === -1) {
          problems.push(at + ': does not state the sensitivity of ' + step.dataset);
        }
        if (d.kind === 'synthetic') {
          if (!/SYNTHETIC/.test(step.narration) || !/fabricated/i.test(step.narration)) {
            problems.push(at + ': ' + step.dataset + ' is synthetic and the narration must say SYNTHETIC and fabricated');
          }
        } else {
          var pv = d.provenance || {};
          var lic = LICENCE_WORDS[String(pv.licence || '').toLowerCase()];
          if (!pv.publisher || step.narration.indexOf(pv.publisher) === -1) {
            problems.push(at + ': real dataset ' + step.dataset + ' must name its publisher (' + pv.publisher + ')');
          }
          if (!lic || !lic.test(step.narration)) {
            problems.push(at + ': real dataset ' + step.dataset + ' must name its licence (' + pv.licence + ')');
          }
        }
      }
      if (!current) return;
      var cd = datasets[current];
      namedColumns(words, cd.pii).forEach(function (c) {
        if ((cd.columns || []).indexOf(c) === -1) {
          problems.push(at + ': names column ' + c + ', which ' + current + ' does not have');
        }
      });
      said[current] = (said[current] || '') + ' ' + [step.title, step.narration].filter(Boolean).join('. ');
    });

    Object.keys(said).forEach(function (id) {
      var d = datasets[id];
      var pii = (d.pii || []);
      var claims = sentencesOf(said[id]).filter(function (s) { return REDACTION_WORD.test(s); });
      var affirmative = claims.filter(function (s) { return !NEGATION.test(s); });
      var negated = claims.filter(function (s) { return NEGATION.test(s); });
      if (!pii.length) {
        affirmative.forEach(function (s) {
          problems.push('flow ' + fid + ': claims redaction on ' + id + ', which has no column to redact: "' + s.trim() + '"');
        });
        if (!negated.length) problems.push('flow ' + fid + ': never says that nothing in ' + id + ' is redacted');
      } else {
        if (!affirmative.length) problems.push('flow ' + fid + ': never says which columns of ' + id + ' are redacted');
        affirmative.forEach(function (s) {
          namedColumns(s, pii).forEach(function (c) {
            if (pii.indexOf(c) === -1) problems.push('flow ' + fid + ': claims ' + c + ' of ' + id + ' is redacted, but it is not declared');
          });
        });
        pii.forEach(function (c) {
          if (namedColumns(said[id], pii).indexOf(c) === -1) problems.push('flow ' + fid + ': never names ' + c + ', a redacted column of ' + id);
        });
      }
    });
    return problems;
  }

  var api = {
    KINDS: KINDS,
    WITHDRAWN: WITHDRAWN,
    checkClaims: checkClaims,
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
