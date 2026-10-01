/**
 * MK9.8 — Connection Manager for Moke
 *
 * Manages saved API connections: list, test, fetch, schedule refresh,
 * health monitoring, and export/import of configs (excluding secrets).
 *
 * Connections are stored in localStorage, without their secrets. Every
 * request goes MokeApiCache -> MokeRateLimiter -> moke's own /api/proxy
 * (moke-proxy.js), so the operator's allowlist (MOKE_PROXY_ALLOW) decides what
 * is fetched, and a refusal is reported with its reason (MK19.8).
 *
 * Live refresh (setSchedule) is a separate feature and never the demo path: it
 * is off on every page load, is not persisted, and runs only while the page
 * that started it is open. A connection's saved `schedule` is ignored.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  var STORAGE_KEY = 'moke_api_connections';

  /** Schedule options in minutes, mapped to human labels. */
  var SCHEDULE_OPTIONS = [
    { value: 0,    label: 'Off' },
    { value: 5,    label: '5 min' },
    { value: 15,   label: '15 min' },
    { value: 30,   label: '30 min' },
    { value: 60,   label: '1 h' },
    { value: 360,  label: '6 h' },
    { value: 1440, label: '24 h' }
  ];

  /** Keys whose values are considered secrets and stripped on export. */
  var SECRET_KEYS = [
    'authorization', 'x-api-key', 'api-key', 'apikey',
    'token', 'secret', 'password', 'credential', 'bearer'
  ];

  /** One hour in milliseconds — threshold between green and amber health. */
  var ONE_HOUR_MS = 60 * 60 * 1000;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /** Read connections array from localStorage. */
  function loadAll() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      console.error('[MokeConnectionManager] Failed to load connections:', e);
      return [];
    }
  }

  /** Write connections array to localStorage. */
  function persist(connections) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(connections));
    } catch (e) {
      console.error('[MokeConnectionManager] Failed to persist connections:', e);
    }
  }

  /** Find a connection by name (case-sensitive). Returns index or -1. */
  function findIndex(connections, name) {
    for (var i = 0; i < connections.length; i++) {
      if (connections[i].name === name) return i;
    }
    return -1;
  }

  /** Return true if a header key looks like it holds a secret. */
  function isSecretHeader(key) {
    var lower = (key || '').toLowerCase();
    for (var i = 0; i < SECRET_KEYS.length; i++) {
      if (lower.indexOf(SECRET_KEYS[i]) !== -1) return true;
    }
    return false;
  }

  /** Sanitise a headers object by masking secret values. */
  function stripSecrets(headers) {
    if (!headers || typeof headers !== 'object') return headers;
    var clean = {};
    var keys = Object.keys(headers);
    for (var i = 0; i < keys.length; i++) {
      clean[keys[i]] = isSecretHeader(keys[i]) ? '***REDACTED***' : headers[keys[i]];
    }
    return clean;
  }

  /** Format a timestamp (ms since epoch) as a human-friendly string. */
  function formatTime(ts) {
    if (!ts) return 'never';
    var d = new Date(ts);
    var now = Date.now();
    var diff = now - ts;
    if (diff < 60000) return 'just now';
    if (diff < ONE_HOUR_MS) return Math.floor(diff / 60000) + ' min ago';
    if (diff < ONE_HOUR_MS * 24) return Math.floor(diff / ONE_HOUR_MS) + ' h ago';
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  /** Show (or clear) a failure reason under the card a button belongs to. */
  function showMsg(btn, text) {
    var card = btn.closest('.mcm-card');
    var m = card && card.querySelector('.mcm-msg');
    if (m) m.textContent = text || '';
  }

  /** Create a DOM element with optional class and text content. */
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // ---------------------------------------------------------------------------
  // Build request options from a connection record
  // ---------------------------------------------------------------------------

  /**
   * Key/value pairs as a plain object. The Connections page saves headers and
   * params as [{key, value}]; imported configs may hold an object. Both are read.
   */
  function pairs(v) {
    var out = {};
    if (Array.isArray(v)) {
      for (var i = 0; i < v.length; i++) {
        var k = v[i] && (v[i].key || v[i].name);
        if (k) out[k] = v[i].value == null ? '' : String(v[i].value);
      }
    } else if (v && typeof v === 'object') {
      var keys = Object.keys(v);
      for (var j = 0; j < keys.length; j++) out[keys[j]] = v[keys[j]];
    }
    return out;
  }

  /** Secrets for this page's session only, by connection name; never stored. */
  var _sessionAuth = {};

  function buildFetchOptions(conn) {
    var opts = { method: (conn.method || 'GET').toUpperCase() };
    var hdrs = pairs(conn.headers);

    if (Object.keys(hdrs).length > 0) opts.headers = hdrs;

    // Body for non-GET methods
    if (conn.body && opts.method !== 'GET' && opts.method !== 'HEAD') {
      opts.body = typeof conn.body === 'string' ? conn.body : JSON.stringify(conn.body);
      if (!hdrs['Content-Type']) {
        opts.headers = opts.headers || {};
        opts.headers['Content-Type'] = 'application/json';
      }
    }

    return opts;
  }

  /** Build the full URL including any query params. */
  function buildUrl(conn, extraParams) {
    var url = conn.url || '';
    var params = Object.assign(pairs(conn.params), extraParams || {});
    var keys = Object.keys(params);
    if (keys.length > 0) {
      var parts = [];
      for (var i = 0; i < keys.length; i++) {
        parts.push(encodeURIComponent(keys[i]) + '=' + encodeURIComponent(params[keys[i]]));
      }
      url += (url.indexOf('?') === -1 ? '?' : '&') + parts.join('&');
    }
    return url;
  }

  /**
   * The request for a connection: its URL, method, headers and body, with this
   * session's credentials applied by MokeAuth (auth-methods.js) when it is
   * loaded. An OAuth token is fetched, through moke's proxy, when it is needed.
   */
  async function buildRequest(conn) {
    var opts = buildFetchOptions(conn);
    var auth = _sessionAuth[conn.name];
    var extra = {};
    if (auth && auth.type && auth.type !== 'none' && window.MokeAuth) {
      if (auth.type === 'oauth2') await window.MokeAuth.ensureValidToken(auth);
      var rc = window.MokeAuth.applyAuth({ headers: Object.assign({}, opts.headers || {}), params: {} }, auth);
      opts.headers = rc.headers;
      extra = rc.params;
    }
    return { url: buildUrl(conn, extra), options: opts };
  }

  /**
   * Send a connection's request: through the response cache unless `fresh`,
   * and always through the rate limiter, whose transport is moke's proxy. There
   * is no path here to a bare fetch of the target.
   */
  async function send(conn, fresh) {
    var req = await buildRequest(conn);
    if (!fresh && window.MokeApiCache) return window.MokeApiCache.cachedFetch(req.url, req.options, conn.name);
    if (!window.MokeRateLimiter) throw new Error('rate-limiter.js is not loaded on this page');
    return window.MokeRateLimiter.fetch(req.url, req.options);
  }

  function contentTypeOf(resp) {
    var h = resp.headers;
    if (h && typeof h.get === 'function') return h.get('content-type') || '';
    return (h && h['content-type']) || '';
  }

  // ---------------------------------------------------------------------------
  // Core module
  // ---------------------------------------------------------------------------

  var MokeConnectionManager = {
    STORAGE_KEY: STORAGE_KEY,

    // -----------------------------------------------------------------------
    // CRUD
    // -----------------------------------------------------------------------

    /**
     * Get all saved connections.
     * @returns {Array} Array of connection objects.
     */
    getAll: function () {
      return loadAll();
    },

    /**
     * Save (create or update) a connection. Matches on `connection.name`.
     * @param {Object} connection - Connection config object.
     */
    save: function (connection) {
      if (!connection || !connection.name) {
        console.warn('[MokeConnectionManager] Cannot save connection without a name.');
        return;
      }
      var all = loadAll();
      var idx = findIndex(all, connection.name);
      if (idx !== -1) {
        // Preserve runtime fields when updating
        connection.lastTested  = connection.lastTested  || all[idx].lastTested;
        connection.lastFetched = connection.lastFetched || all[idx].lastFetched;
        connection.lastStatus  = connection.lastStatus  != null ? connection.lastStatus : all[idx].lastStatus;
        connection.schedule    = connection.schedule     != null ? connection.schedule    : all[idx].schedule;
        all[idx] = connection;
      } else {
        all.push(connection);
      }
      persist(all);
    },

    /**
     * Delete a connection by name.
     * Also clears any active scheduler timer for it.
     * @param {string} name
     */
    delete: function (name) {
      var all = loadAll();
      var idx = findIndex(all, name);
      if (idx === -1) return;
      all.splice(idx, 1);
      persist(all);
      // Clear timer if running
      if (MokeConnectionManager._timers[name]) {
        clearInterval(MokeConnectionManager._timers[name]);
        delete MokeConnectionManager._timers[name];
      }
    },

    // -----------------------------------------------------------------------
    // Test & Fetch
    // -----------------------------------------------------------------------

    /**
     * Test a connection by sending a request and recording the result.
     * @param {string} name - Connection name.
     * @returns {Promise<{ok: boolean, status: number, responseTime: number, error: string|null}>}
     */
    test: async function (name) {
      var all = loadAll();
      var idx = findIndex(all, name);
      if (idx === -1) return { ok: false, status: 0, responseTime: 0, error: 'Connection not found' };

      var conn = all[idx];
      var start = performance.now();

      try {
        var resp = await send(conn, true);
        var elapsed = Math.round(performance.now() - start);
        conn.lastTested = Date.now();
        conn.lastStatus = resp.status;
        persist(all);
        return { ok: resp.ok, status: resp.status, responseTime: elapsed,
                 error: resp.ok ? null : 'the upstream answered ' + resp.status };
      } catch (err) {
        var elapsed2 = Math.round(performance.now() - start);
        conn.lastTested = Date.now();
        conn.lastStatus = 0;
        persist(all);
        return { ok: false, status: 0, responseTime: elapsed2, error: err.message || String(err) };
      }
    },

    /**
     * Fetch data from a connection and return it as a table:
     * {name, headers, rows, url, connection, meta}. JSON goes through
     * MokeJsonParser.toDataset (json-parser.js; this used to call a
     * MokeJSONParser.parse that never existed), CSV through MokeData.parseCSV.
     * The table is not stored here: the caller hands it to MokeActive.load.
     * @param {string} name
     * @param {{fresh: boolean}} [opts] - fresh skips the response cache.
     */
    fetch: async function (name, opts) {
      var all = loadAll();
      var idx = findIndex(all, name);
      if (idx === -1) throw new Error('Connection not found: ' + name);

      var conn = all[idx];
      var resp = await send(conn, !!(opts && opts.fresh));
      if (!resp.ok) throw new Error('the upstream answered ' + resp.status);

      var text = await resp.text();

      // Update tracking
      conn.lastFetched = Date.now();
      conn.lastTested  = Date.now();
      conn.lastStatus  = resp.status;
      persist(all);

      return MokeConnectionManager.toTable(text, contentTypeOf(resp), conn);
    },

    /**
     * A response body as a table. JSON first (it parses), then CSV by content
     * type; anything else is an error naming what arrived.
     */
    toTable: function (text, contentType, conn) {
      var name = (conn && conn.name) || 'API dataset';
      var json, isJson = false;
      try { json = JSON.parse(text); isJson = true; } catch (e) { isJson = false; }
      var table;
      if (isJson) {
        table = window.MokeJsonParser
          ? window.MokeJsonParser.toDataset(json, { name: name, flatten: true })
          : MokeConnectionManager._basicParse(json);
      } else if (/csv|text\/plain|tab-separated/i.test(contentType || '') && window.MokeData) {
        var parsed = window.MokeData.parseCSV(text);
        table = { headers: parsed.headers, rows: parsed.rows, meta: { delimiter: parsed.delimiter } };
      } else {
        throw new Error('the response is neither JSON nor CSV (' + (contentType || 'no content type') + ')');
      }
      table.name = name;
      table.url = (conn && conn.url) || '';
      table.connection = (conn && conn.name) || '';
      return table;
    },

    /**
     * This page session's credentials for a connection. Kept in memory only:
     * never written to localStorage and never exported.
     */
    setSessionAuth: function (name, authConfig) {
      if (!name) return;
      if (!authConfig || !authConfig.type || authConfig.type === 'none') delete _sessionAuth[name];
      else _sessionAuth[name] = authConfig;
    },

    /**
     * Simple JSON-to-tabular fallback when MokeJSONParser is unavailable.
     * @private
     */
    _basicParse: function (json) {
      var data = json;

      // Unwrap common wrapper keys
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        var wrappers = ['data', 'results', 'items', 'records', 'rows'];
        for (var i = 0; i < wrappers.length; i++) {
          if (Array.isArray(data[wrappers[i]])) { data = data[wrappers[i]]; break; }
        }
      }

      if (!Array.isArray(data)) data = [data];

      // Collect headers
      var seenH = {};
      var headers = [];
      for (var r = 0; r < data.length; r++) {
        if (data[r] && typeof data[r] === 'object') {
          var keys = Object.keys(data[r]);
          for (var k = 0; k < keys.length; k++) {
            if (!seenH[keys[k]]) { seenH[keys[k]] = true; headers.push(keys[k]); }
          }
        }
      }

      // Build rows
      var rows = [];
      for (var r2 = 0; r2 < data.length; r2++) {
        var row = [];
        for (var h = 0; h < headers.length; h++) {
          var val = data[r2] ? data[r2][headers[h]] : undefined;
          row.push(val !== undefined && val !== null ? String(val) : '');
        }
        rows.push(row);
      }

      return {
        headers: headers,
        rows: rows,
        meta: { source: 'connection-manager', rowCount: rows.length, colCount: headers.length }
      };
    },

    // -----------------------------------------------------------------------
    // Health
    // -----------------------------------------------------------------------

    /**
     * Determine health colour for a connection.
     * @param {Object} connection
     * @returns {'green'|'amber'|'red'}
     */
    getHealth: function (connection) {
      if (!connection.lastTested || connection.lastStatus === 0) return 'red';

      var age = Date.now() - connection.lastTested;
      var status = connection.lastStatus;

      if (status >= 500) return 'red';
      if (status >= 200 && status < 300 && age < ONE_HOUR_MS) return 'green';
      // 3xx, 4xx, or stale 2xx
      return 'amber';
    },

    // -----------------------------------------------------------------------
    // Schedule
    // -----------------------------------------------------------------------

    /**
     * Set a refresh schedule for a connection.
     * @param {string} name
     * @param {number} intervalMinutes - 0 means off.
     */
    setSchedule: function (name, intervalMinutes) {
      var all = loadAll();
      var idx = findIndex(all, name);
      if (idx === -1) return;

      // Not persisted: live refresh never starts by itself on a page load.
      MokeConnectionManager._schedules[name] = intervalMinutes || 0;

      // Reset timer
      if (MokeConnectionManager._timers[name]) {
        clearInterval(MokeConnectionManager._timers[name]);
        delete MokeConnectionManager._timers[name];
      }

      if (intervalMinutes > 0) {
        MokeConnectionManager._timers[name] = setInterval(function () {
          MokeConnectionManager.refresh(name);
        }, intervalMinutes * 60 * 1000);
      }
    },

    /**
     * One live refresh: a fresh fetch (no cache), announced as a
     * 'moke:live-refresh' event with the table, or with the error. What to do
     * with it is the page's decision; this module stores nothing.
     */
    refresh: function (name) {
      return MokeConnectionManager.fetch(name, { fresh: true }).then(function (table) {
        document.dispatchEvent(new CustomEvent('moke:live-refresh', { detail: { name: name, table: table, at: Date.now() } }));
        return table;
      }, function (err) {
        document.dispatchEvent(new CustomEvent('moke:live-refresh', { detail: { name: name, error: err.message || String(err), at: Date.now() } }));
        return null;
      });
    },

    /** Stop all scheduled timers. */
    stopScheduler: function () {
      var names = Object.keys(MokeConnectionManager._timers);
      for (var i = 0; i < names.length; i++) {
        clearInterval(MokeConnectionManager._timers[names[i]]);
      }
      MokeConnectionManager._timers = {};
      MokeConnectionManager._schedules = {};
    },

    // -----------------------------------------------------------------------
    // Export / Import
    // -----------------------------------------------------------------------

    /**
     * Export all connections as a JSON string with auth secrets stripped.
     * @returns {string} JSON string.
     */
    exportConfig: function () {
      var all = loadAll();
      var exported = [];
      for (var i = 0; i < all.length; i++) {
        var c = all[i];
        exported.push({
          name:     c.name,
          url:      c.url,
          method:   c.method,
          headers:  stripSecrets(pairs(c.headers)),
          params:   stripSecrets(pairs(c.params)),
          body:     c.body || null,
          auth:     c.auth || c.authType || 'none'
          // credentials are never stored, so none can be exported
        });
      }
      return JSON.stringify(exported, null, 2);
    },

    /**
     * Import connections from a JSON string. Skips duplicates (by name).
     * @param {string} jsonString
     * @returns {{imported: number, skipped: number}}
     */
    importConfig: function (jsonString) {
      var incoming;
      try {
        incoming = JSON.parse(jsonString);
      } catch (e) {
        throw new Error('Invalid JSON: ' + e.message);
      }
      if (!Array.isArray(incoming)) {
        throw new Error('Expected a JSON array of connections.');
      }

      var all = loadAll();
      var imported = 0;
      var skipped = 0;

      for (var i = 0; i < incoming.length; i++) {
        var conn = incoming[i];
        if (!conn.name) { skipped++; continue; }
        if (findIndex(all, conn.name) !== -1) { skipped++; continue; }
        all.push(conn);
        imported++;
      }
      persist(all);
      return { imported: imported, skipped: skipped };
    },

    // -----------------------------------------------------------------------
    // Rendering
    // -----------------------------------------------------------------------

    /**
     * Render a full connection list into a container element.
     * @param {string} containerId - DOM element ID.
     */
    renderConnectionList: function (containerId) {
      var container = document.getElementById(containerId);
      if (!container) {
        console.warn('[MokeConnectionManager] Container not found: #' + containerId);
        return;
      }
      container.innerHTML = '';

      var all = loadAll();
      if (all.length === 0) {
        var empty = el('div', 'mcm-empty', 'No saved connections. Add one from the API data source panel.');
        empty.style.cssText = 'color:var(--muted);text-align:center;padding:2rem;';
        container.appendChild(empty);
        return;
      }

      for (var i = 0; i < all.length; i++) {
        container.appendChild(MokeConnectionManager.renderConnectionCard(all[i]));
      }
    },

    /**
     * Render a single connection card.
     * @param {Object} connection
     * @returns {HTMLElement}
     */
    renderConnectionCard: function (connection) {
      var health = MokeConnectionManager.getHealth(connection);

      // Card wrapper
      var card = el('div', 'mcm-card');
      card.style.cssText = [
        'background:var(--surface)',
        'border:1px solid var(--border)',
        'border-radius:6px',
        'padding:0.75rem 1rem',
        'margin-bottom:0.5rem',
        'display:flex',
        'align-items:center',
        'gap:0.75rem',
        'flex-wrap:wrap'
      ].join(';') + ';';

      // Health dot
      var dot = el('span', 'mcm-health-dot');
      var dotColor = health === 'green' ? 'var(--green)' :
                     health === 'amber' ? 'var(--amber)' : 'var(--red)';
      dot.style.cssText = [
        'width:10px', 'height:10px', 'border-radius:50%',
        'display:inline-block', 'flex-shrink:0',
        'background:' + dotColor
      ].join(';') + ';';
      dot.title = health + ' — last tested ' + formatTime(connection.lastTested);
      card.appendChild(dot);

      // Name
      var nameEl = el('strong', 'mcm-name', connection.name);
      nameEl.style.cssText = 'color:var(--text);flex:1;min-width:120px;';
      card.appendChild(nameEl);

      // Method badge
      var method = (connection.method || 'GET').toUpperCase();
      var badge = el('span', 'mcm-method', method);
      badge.style.cssText = [
        'background:var(--teal)', 'color:var(--bg)',
        'font-size:0.7rem', 'font-weight:700',
        'padding:2px 6px', 'border-radius:3px',
        'text-transform:uppercase', 'flex-shrink:0'
      ].join(';') + ';';
      card.appendChild(badge);

      // URL (truncated)
      var urlText = (connection.url || '').length > 50
        ? connection.url.substring(0, 47) + '...'
        : (connection.url || '');
      var urlEl = el('span', 'mcm-url', urlText);
      urlEl.style.cssText = 'color:var(--muted);font-size:0.8rem;flex:2;min-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
      urlEl.title = connection.url || '';
      card.appendChild(urlEl);

      // Last tested
      var testedEl = el('span', 'mcm-tested', formatTime(connection.lastTested));
      testedEl.style.cssText = 'color:var(--muted);font-size:0.75rem;min-width:80px;text-align:right;';
      card.appendChild(testedEl);

      // Schedule dropdown
      var schedSelect = document.createElement('select');
      schedSelect.className = 'mcm-schedule';
      schedSelect.style.cssText = [
        'background:var(--bg)', 'color:var(--text)',
        'border:1px solid var(--border)', 'border-radius:3px',
        'font-size:0.75rem', 'padding:2px 4px', 'cursor:pointer'
      ].join(';') + ';';
      for (var s = 0; s < SCHEDULE_OPTIONS.length; s++) {
        var opt = document.createElement('option');
        opt.value = SCHEDULE_OPTIONS[s].value;
        opt.textContent = SCHEDULE_OPTIONS[s].label;
        if ((MokeConnectionManager._schedules[connection.name] || 0) === SCHEDULE_OPTIONS[s].value) opt.selected = true;
        schedSelect.appendChild(opt);
      }
      (function (connName) {
        schedSelect.addEventListener('change', function () {
          MokeConnectionManager.setSchedule(connName, parseInt(this.value, 10));
        });
      })(connection.name);
      var schedLabel = el('label', 'mcm-schedule-label', 'Live refresh ');
      schedLabel.style.cssText = 'color:var(--muted);font-size:0.72rem;';
      schedLabel.title = 'Off by default and on every page load; runs only while this page is open';
      schedLabel.appendChild(schedSelect);
      card.appendChild(schedLabel);

      // Action buttons
      var actions = el('span', 'mcm-actions');
      actions.style.cssText = 'display:flex;gap:0.35rem;flex-shrink:0;';

      var btnStyle = [
        'background:var(--bg)', 'color:var(--text)',
        'border:1px solid var(--border)', 'border-radius:3px',
        'font-size:0.7rem', 'padding:3px 8px', 'cursor:pointer'
      ].join(';') + ';';

      // Test button
      var testBtn = el('button', 'mcm-btn-test', 'Test');
      testBtn.style.cssText = btnStyle;
      (function (connName, btn, dotEl) {
        btn.addEventListener('click', function () {
          btn.textContent = '...';
          btn.disabled = true;
          MokeConnectionManager.test(connName).then(function (result) {
            btn.textContent = result.ok ? result.status + ' OK' : 'Err ' + (result.status || '');
            btn.disabled = false;
            showMsg(btn, result.ok ? '' : result.error);
            // Update dot colour
            var all = loadAll();
            var ix = findIndex(all, connName);
            if (ix !== -1) {
              var h = MokeConnectionManager.getHealth(all[ix]);
              var c = h === 'green' ? 'var(--green)' : h === 'amber' ? 'var(--amber)' : 'var(--red)';
              dotEl.style.background = c;
            }
            setTimeout(function () { btn.textContent = 'Test'; }, 3000);
          });
        });
      })(connection.name, testBtn, dot);
      actions.appendChild(testBtn);

      // Load (fetch) button
      var loadBtn = el('button', 'mcm-btn-load', 'Load');
      loadBtn.style.cssText = btnStyle;
      (function (connName, btn) {
        btn.addEventListener('click', function () {
          btn.textContent = '...';
          btn.disabled = true;
          MokeConnectionManager.fetch(connName).then(function (dataset) {
            btn.textContent = dataset.rows.length + ' rows';
            btn.disabled = false;
            showMsg(btn, '');
            // Dispatch custom event so moke can pick up the dataset
            var evt = new CustomEvent('moke:dataset', { detail: { name: connName, dataset: dataset } });
            document.dispatchEvent(evt);
            setTimeout(function () { btn.textContent = 'Load'; }, 3000);
          }).catch(function (err) {
            btn.textContent = 'Error';
            btn.disabled = false;
            showMsg(btn, err.message || String(err));
            setTimeout(function () { btn.textContent = 'Load'; }, 3000);
          });
        });
      })(connection.name, loadBtn);
      actions.appendChild(loadBtn);

      // Delete button
      var delBtn = el('button', 'mcm-btn-del', 'Del');
      delBtn.style.cssText = btnStyle + 'color:var(--red);border-color:var(--red);';
      (function (connName, cardEl) {
        delBtn.addEventListener('click', function () {
          if (confirm('Delete connection "' + connName + '"?')) {
            MokeConnectionManager.delete(connName);
            cardEl.remove();
          }
        });
      })(connection.name, card);
      actions.appendChild(delBtn);

      card.appendChild(actions);

      // Why the last Test or Load failed: the proxy's reason, in full.
      var msg = el('div', 'mcm-msg');
      msg.setAttribute('role', 'status');
      msg.style.cssText = 'flex-basis:100%;color:var(--red);font-size:0.75rem;';
      card.appendChild(msg);
      return card;
    },

    // -----------------------------------------------------------------------
    // Internal state
    // -----------------------------------------------------------------------

    /** Active setInterval timer IDs keyed by connection name. */
    _timers: {},

    /** Live-refresh intervals (minutes) set in this page session. */
    _schedules: {}
  };

  // ---------------------------------------------------------------------------
  // Expose on window
  // ---------------------------------------------------------------------------

  window.MokeConnectionManager = MokeConnectionManager;

})();
