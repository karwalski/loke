/*
 * moke-data.js — the dataset data layer (story MK19.1)
 *
 * WHY THIS EXISTS
 *
 * moke had two divergent dataset stores. The backend — data/*.tk plus
 * data/registry.tk, served by pages/api/datasets.tk — is orphaned: grepping for
 * its endpoint across every page and template returns nothing. What the demo
 * actually used was a `var DATASETS` object inline in templates/index.tkt, which
 * is 230KB of data and UI fused into one file, re-parsed by the browser on every
 * visit to the landing page.
 *
 * This module is the third option, and the one that does not make either problem
 * worse: a static manifest plus CSV snapshots under static/data/, fetched lazily.
 * No recompilation to add a dataset, diffable and reviewable snapshots, and the
 * landing page stops carrying every row of every dataset.
 *
 * MIGRATION POSITION, STATED HONESTLY
 *
 * This does not yet replace the inline object. Both paths coexist deliberately:
 * manifest datasets flow through here, the original 15 still flow through
 * index.tkt. That is a real hazard rather than a tidy transition — consumers that
 * assume `.rows` is present on the active dataset will behave differently
 * depending on which store a dataset came from. MokeActive.get() below is what
 * contains that, and it is not optional.
 *
 * ON THE CSV PARSER
 *
 * There are already three parseCSV implementations in this package
 * (templates/upload.tkt, static/js/datagov-source.js, static/js/url-import.js).
 * Adding a fourth divergent one would be indefensible, so the one here is
 * written to be the canonical one and the other three should delegate to it.
 * That migration is a separate story rather than bundled here, because changing
 * upload.tkt's parser in the same change as introducing this module would make
 * both harder to review. Until then this is the fourth implementation, which is
 * a debt this comment exists to keep visible.
 */

(function (global) {
  'use strict';

  var MANIFEST_URL = '/static/data/manifest.json';

  var _manifest = null;      // parsed manifest, once fetched
  var _rowCache = {};        // id -> {headers, rows}
  var _dashCache = {};       // path -> parsed dashboard definition

  /* ---------------------------------------------------------------------
   * CSV parsing
   * ------------------------------------------------------------------ */

  /* Parse one record starting at `pos`, honouring RFC 4180 quoting so a
   * quoted field may contain the delimiter or a newline. Returns the fields
   * and the position after the record's line break. */
  function parseRecord(text, pos, delim) {
    var fields = [];
    var field = '';
    var inQuotes = false;
    var len = text.length;

    while (pos < len) {
      var ch = text[pos];

      if (inQuotes) {
        if (ch === '"') {
          if (text[pos + 1] === '"') { field += '"'; pos += 2; continue; }
          inQuotes = false; pos++; continue;
        }
        field += ch; pos++; continue;
      }

      if (ch === '"' && field === '') { inQuotes = true; pos++; continue; }
      if (ch === delim) { fields.push(field); field = ''; pos++; continue; }
      if (ch === '\n') { fields.push(field); return { fields: fields, nextPos: pos + 1 }; }
      if (ch === '\r') {
        fields.push(field);
        return { fields: fields, nextPos: text[pos + 1] === '\n' ? pos + 2 : pos + 1 };
      }
      field += ch; pos++;
    }

    fields.push(field);
    return { fields: fields, nextPos: len };
  }

  /* Pick a delimiter by which candidate gives the most consistent field count
   * across the first few records. Counting occurrences alone is wrong: a comma
   * inside quoted descriptions can outnumber real semicolon delimiters. */
  function detectDelimiter(text) {
    var candidates = [',', ';', '\t', '|'];
    var best = ',';
    var bestScore = -1;

    for (var i = 0; i < candidates.length; i++) {
      var d = candidates[i];
      var counts = [];
      var pos = 0;
      for (var r = 0; r < 5 && pos < text.length; r++) {
        var res = parseRecord(text, pos, d);
        pos = res.nextPos;
        counts.push(res.fields.length);
      }
      if (!counts.length || counts[0] < 2) continue;
      var consistent = counts.every(function (c) { return c === counts[0]; });
      // Consistency first, then field count as a tie-break.
      var score = (consistent ? 1000 : 0) + counts[0];
      if (score > bestScore) { bestScore = score; best = d; }
    }
    return best;
  }

  /* Parse a whole CSV. Returns {headers, rows, ragged} where rows are arrays,
   * matching what every existing consumer in this package expects.
   *
   * `ragged` lists records whose field count differs from the header's. They are
   * reported rather than silently padded, because a short row in a bank or
   * government export usually means something was dropped, and padding it turns
   * a detectable problem into a wrong answer. */
  function parseCSV(text, opts) {
    opts = opts || {};
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);   // strip a BOM

    var delim = opts.delimiter || detectDelimiter(text);
    var records = [];
    var pos = 0;
    while (pos < text.length) {
      var res = parseRecord(text, pos, delim);
      pos = res.nextPos;
      if (res.fields.length === 1 && res.fields[0].trim() === '') continue;  // blank
      records.push(res.fields);
    }
    if (!records.length) return { headers: [], rows: [], ragged: [], delimiter: delim };

    var headers = records[0].map(function (h) { return String(h).trim(); });
    var rows = [];
    var ragged = [];
    for (var i = 1; i < records.length; i++) {
      if (records[i].length !== headers.length) {
        ragged.push({ record: i + 1, fields: records[i].length, expected: headers.length });
      }
      rows.push(records[i]);
    }
    return { headers: headers, rows: rows, ragged: ragged, delimiter: delim };
  }

  /* ---------------------------------------------------------------------
   * Manifest access
   * ------------------------------------------------------------------ */

  function loadManifest() {
    if (_manifest) return Promise.resolve(_manifest);
    return fetch(MANIFEST_URL)
      .then(function (r) {
        if (!r.ok) throw new Error('manifest HTTP ' + r.status);
        return r.json();
      })
      .then(function (m) { _manifest = m; return m; });
  }

  function catalogue() {
    return loadManifest().then(function (m) { return (m.datasets || []).slice(); });
  }

  function meta(id) {
    return loadManifest().then(function (m) {
      var found = (m.datasets || []).filter(function (d) { return d.id === id; })[0];
      if (!found) throw new Error('no manifest entry for ' + id);
      return found;
    });
  }

  /* Fetch and parse a dataset's rows, memoised. Returns
   * {headers, rows, ragged, meta}. */
  function rows(id) {
    if (_rowCache[id]) return Promise.resolve(_rowCache[id]);
    return meta(id).then(function (m) {
      var path = m.data && m.data.path;
      if (!path) throw new Error(id + ' has no data path; it may be live-fetch only');
      return fetch(path).then(function (r) {
        if (!r.ok) throw new Error('snapshot HTTP ' + r.status + ' for ' + path);
        return r.text();
      }).then(function (text) {
        var parsed = parseCSV(text);
        parsed.meta = m;
        // A row-count mismatch against the manifest means the snapshot and its
        // record have diverged, which invalidates the provenance.
        if (m.data.rowcount && parsed.rows.length !== m.data.rowcount) {
          parsed.rowcountMismatch = {
            manifest: m.data.rowcount, actual: parsed.rows.length
          };
        }
        _rowCache[id] = parsed;
        return parsed;
      });
    });
  }

  function prompts(id, surface) {
    return meta(id).then(function (m) {
      var p = m.prompts || {};
      return surface ? (p[surface] || []) : p;
    });
  }

  /* Pre-baked dashboard definitions, so a demo never depends on a live model
   * call succeeding (MK19.7). */
  function dashboards(id) {
    return meta(id).then(function (m) { return (m.dashboards || []).slice(); });
  }

  function dashboard(path) {
    if (_dashCache[path]) return Promise.resolve(_dashCache[path]);
    return fetch(path).then(function (r) {
      if (!r.ok) throw new Error('dashboard HTTP ' + r.status + ' for ' + path);
      return r.json();
    }).then(function (d) { _dashCache[path] = d; return d; });
  }

  /* Build a value-free schema profile: names, types, cardinality, null rate.
   * No sample values, no min, max or mean — those are real data (NC1.2). This
   * is what may be disclosed to a model; the rows never are. */
  function schemaProfile(parsed) {
    var headers = parsed.headers;
    var rowsArr = parsed.rows;
    var cols = headers.map(function (name, i) {
      var seen = {};
      var distinct = 0;
      var nulls = 0;
      var numeric = 0;
      var nonEmpty = 0;
      for (var r = 0; r < rowsArr.length; r++) {
        var v = i < rowsArr[r].length ? String(rowsArr[r][i]).trim() : '';
        if (v === '') { nulls++; continue; }
        nonEmpty++;
        if (seen[v] === undefined) { seen[v] = 1; distinct++; }
        if (v !== '' && isFinite(Number(v.replace(/[$,%\s]/g, '')))) numeric++;
      }
      // `seen` holds values only to count them and goes out of scope here. It is
      // never returned, logged or transmitted.
      var type = 'categorical';
      if (nonEmpty > 0 && numeric / nonEmpty > 0.9) type = 'numeric';
      else if (/^(date|month|year|time|day)/i.test(name)) type = 'temporal';
      else if (distinct === 2) type = 'boolean';
      else if (nonEmpty > 0 && distinct / nonEmpty > 0.9) type = 'identifier';
      return {
        name: name,
        type: type,
        distinct_count: distinct,
        null_rate: rowsArr.length ? +(nulls / rowsArr.length).toFixed(4) : 0
      };
    });
    return { row_count: rowsArr.length, columns: cols };
  }

  global.MokeData = {
    catalogue: catalogue,
    meta: meta,
    rows: rows,
    prompts: prompts,
    dashboards: dashboards,
    dashboard: dashboard,
    schemaProfile: schemaProfile,
    parseCSV: parseCSV,
    detectDelimiter: detectDelimiter,
    manifestUrl: MANIFEST_URL,
    _resetCaches: function () { _manifest = null; _rowCache = {}; _dashCache = {}; }
  };

  /* ---------------------------------------------------------------------
   * MokeActive — the compatibility shim, and the reason this file is safe
   *
   * There are two dataset stores during the migration. A consumer reading
   * sessionStorage directly gets rows for one and not the other. Every consumer
   * should go through here instead, so that a manifest-backed dataset and an
   * inline one look the same.
   *
   * Seventeen call sites across eight templates read sessionStorage directly
   * today. Migrating them is a separate story; this shim is what makes the two
   * stores coexist safely until then.
   * ------------------------------------------------------------------ */

  global.MokeActive = {
    /* The active dataset with its rows, whichever store it came from. */
    get: function () {
      var raw = null;
      try { raw = sessionStorage.getItem('moke_dataset'); } catch (e) { return null; }
      if (!raw) return null;

      var handle;
      try { handle = JSON.parse(raw); } catch (e) { return null; }
      if (!handle) return null;

      // Inline store: rows are already present.
      if (handle.rows && handle.rows.length) return Promise.resolve(handle);

      // Manifest store: a handle without rows. Fetch them.
      if (handle.source === 'manifest' && handle.id) {
        return rows(handle.id).then(function (parsed) {
          return Object.assign({}, handle, {
            headers: parsed.headers,
            rows: parsed.rows,
            ragged: parsed.ragged
          });
        });
      }

      // Neither: a dataset was selected but carries no data. Say so rather than
      // returning an empty row set that reads as "no results".
      return Promise.resolve(Object.assign({}, handle, { rows: [], unavailable: true }));
    },

    /* Store a manifest-backed dataset as a handle rather than inline, so
     * sessionStorage does not have to hold every row. The per-origin quota is
     * around 5MB and setItem throws uncaught when exceeded, which kills a demo
     * mid-presentation. */
    setFromManifest: function (m) {
      var handle = {
        source: 'manifest',
        id: m.id,
        name: m.name,
        description: m.description,
        category: m.category,
        kind: m.kind,
        sensitivity: m.sensitivity,
        pii: m.pii || [],
        pii_note: m.pii_note || '',
        headers: [],
        rowcount: (m.data && m.data.rowcount) || 0,
        provenance: m.provenance || null
      };
      try {
        sessionStorage.setItem('moke_dataset', JSON.stringify(handle));
      } catch (e) {
        return { ok: false, error: String(e) };
      }
      return { ok: true, handle: handle };
    }
  };
}(typeof window !== 'undefined' ? window : globalThis));
