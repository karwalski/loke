/**
 * MK9.2 — REST/JSON Data Source Parser for Moke
 *
 * Parses JSON API responses into tabular datasets.
 * Handles array-of-objects, wrapped/nested arrays, and paginated responses.
 * No external dependencies.
 */
(function () {
  'use strict';

  // -------------------------------------------------------------------
  // Common wrapper keys that APIs use to nest the actual data array.
  // -------------------------------------------------------------------
  var WRAPPER_PATTERNS = [
    'data', 'results', 'items', 'records', 'rows',
    'entries', 'content', 'hits', 'documents'
  ];

  // -------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------

  /** Shallow type check — distinguishes plain objects from arrays/null. */
  function isPlainObject(v) {
    return v !== null && typeof v === 'object' && !Array.isArray(v);
  }

  /** Return true if `arr` is a non-empty array whose first element is a plain object. */
  function isArrayOfObjects(arr) {
    return Array.isArray(arr) && arr.length > 0 && isPlainObject(arr[0]);
  }

  /**
   * Collect every unique key that appears in an array of objects,
   * preserving first-seen order.
   */
  function collectHeaders(rows) {
    var seen = {};
    var headers = [];
    for (var i = 0; i < rows.length; i++) {
      var keys = Object.keys(rows[i]);
      for (var k = 0; k < keys.length; k++) {
        if (!seen[keys[k]]) {
          seen[keys[k]] = true;
          headers.push(keys[k]);
        }
      }
    }
    return headers;
  }

  // -------------------------------------------------------------------
  // flatten(obj, prefix)
  // -------------------------------------------------------------------
  /**
   * Recursively flatten a nested object using dot-notation keys.
   * Arrays are serialised to JSON strings so every value is a scalar.
   *
   *   flatten({a: {b: 1}, c: [2,3]})
   *   // → {'a.b': 1, 'c': '[2,3]'}
   *
   * @param {Object} obj    — the object to flatten
   * @param {string} [prefix] — key prefix (used during recursion)
   * @returns {Object} flat key/value map
   */
  function flatten(obj, prefix) {
    var result = {};
    if (!isPlainObject(obj)) {
      return result;
    }
    var pre = prefix ? prefix + '.' : '';
    var keys = Object.keys(obj);
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var val = obj[key];
      var fullKey = pre + key;

      if (isPlainObject(val)) {
        // Recurse into nested objects
        var nested = flatten(val, fullKey);
        var nk = Object.keys(nested);
        for (var j = 0; j < nk.length; j++) {
          result[nk[j]] = nested[nk[j]];
        }
      } else if (Array.isArray(val)) {
        // Arrays become JSON strings
        result[fullKey] = JSON.stringify(val);
      } else {
        result[fullKey] = val;
      }
    }
    return result;
  }

  // -------------------------------------------------------------------
  // extractPath(data, path)
  // -------------------------------------------------------------------
  /**
   * Walk a dot-separated path into a data structure and return the value.
   *
   *   extractPath({data: {items: [1,2]}}, 'data.items')  // → [1,2]
   *   extractPath({a: 1}, '')                             // → {a: 1}
   *
   * @param {*} data
   * @param {string} path — dot-separated (e.g. 'data.items')
   * @returns {*} the value at that path, or undefined
   */
  function extractPath(data, path) {
    if (!path || path === '') {
      return data;
    }
    var parts = path.split('.');
    var cur = data;
    for (var i = 0; i < parts.length; i++) {
      if (cur === null || cur === undefined) {
        return undefined;
      }
      cur = cur[parts[i]];
    }
    return cur;
  }

  // -------------------------------------------------------------------
  // detect(jsonData)
  // -------------------------------------------------------------------
  /**
   * Detect the structure of a JSON response and extract tabular rows.
   *
   * Detection order:
   *   1. Top-level array of objects  → type 'array'
   *   2. Wrapped array (common key) → type 'wrapped'
   *   3. Single object              → type 'array' (wrapped in [])
   *   4. Empty / unrecognised       → type 'empty'
   *
   * @param {*} jsonData — parsed JSON (object, array, or primitive)
   * @returns {{ type: string, path: string, rows: Array, headers: string[] }}
   */
  function detect(jsonData) {
    // Null / undefined / primitive
    if (jsonData === null || jsonData === undefined || typeof jsonData !== 'object') {
      return { type: 'empty', path: '', rows: [], headers: [] };
    }

    // 1. Top-level array of objects
    if (isArrayOfObjects(jsonData)) {
      var rows = jsonData;
      return {
        type: 'array',
        path: '',
        rows: rows,
        headers: collectHeaders(rows)
      };
    }

    // Top-level array but NOT of objects (e.g. array of primitives)
    if (Array.isArray(jsonData)) {
      if (jsonData.length === 0) {
        return { type: 'empty', path: '', rows: [], headers: [] };
      }
      // Wrap primitives: [{value: x}, ...]
      var wrapped = jsonData.map(function (v) { return { value: v }; });
      return { type: 'array', path: '', rows: wrapped, headers: ['value'] };
    }

    // 2. Check each WRAPPER_PATTERN for a nested array of objects
    for (var i = 0; i < WRAPPER_PATTERNS.length; i++) {
      var key = WRAPPER_PATTERNS[i];
      var candidate = jsonData[key];
      if (isArrayOfObjects(candidate)) {
        return {
          type: 'wrapped',
          path: key,
          rows: candidate,
          headers: collectHeaders(candidate)
        };
      }
    }

    // Deep scan: look one level deeper for nested arrays (e.g. {response: {data: [...]}})
    var topKeys = Object.keys(jsonData);
    for (var t = 0; t < topKeys.length; t++) {
      var topVal = jsonData[topKeys[t]];
      if (isPlainObject(topVal)) {
        for (var w = 0; w < WRAPPER_PATTERNS.length; w++) {
          var deepCandidate = topVal[WRAPPER_PATTERNS[w]];
          if (isArrayOfObjects(deepCandidate)) {
            var deepPath = topKeys[t] + '.' + WRAPPER_PATTERNS[w];
            return {
              type: 'wrapped',
              path: deepPath,
              rows: deepCandidate,
              headers: collectHeaders(deepCandidate)
            };
          }
        }
      }
    }

    // 3. Single object — treat as a one-row table
    if (isPlainObject(jsonData) && topKeys.length > 0) {
      return {
        type: 'array',
        path: '',
        rows: [jsonData],
        headers: topKeys
      };
    }

    // 4. Give up
    return { type: 'empty', path: '', rows: [], headers: [] };
  }

  // -------------------------------------------------------------------
  // detectPagination(jsonData, responseHeaders)
  // -------------------------------------------------------------------
  /**
   * Inspect a JSON response (and optional HTTP headers) for pagination clues.
   *
   * Checks (in order):
   *   - `next` / `nextPage` / `next_page_url` / `next_url` fields
   *   - RFC 5988 `Link` header with rel="next"
   *   - `offset` + `limit` + `total` / `totalCount` arithmetic
   *   - `page` + `total_pages` / `totalPages` / `last_page`
   *
   * @param {*} jsonData         — parsed JSON body
   * @param {Object} [responseHeaders] — key/value map of HTTP response headers
   * @returns {{ hasNext: boolean, nextUrl: string|null, nextPage: number|null, nextOffset: number|null }}
   */
  function detectPagination(jsonData, responseHeaders) {
    var result = { hasNext: false, nextUrl: null, nextPage: null, nextOffset: null };

    if (!isPlainObject(jsonData)) {
      return result;
    }

    // --- Direct "next" URL fields ---
    var urlFields = ['next', 'nextPage', 'next_page_url', 'next_url', 'next_link'];
    for (var i = 0; i < urlFields.length; i++) {
      var val = jsonData[urlFields[i]];
      if (typeof val === 'string' && val.length > 0) {
        result.hasNext = true;
        result.nextUrl = val;
        return result;
      }
    }

    // Also check inside common meta/pagination wrappers
    var metaKeys = ['meta', 'pagination', 'paging', 'page_info', 'pageInfo', 'links', '_links'];
    for (var m = 0; m < metaKeys.length; m++) {
      var meta = jsonData[metaKeys[m]];
      if (isPlainObject(meta)) {
        for (var u = 0; u < urlFields.length; u++) {
          var mval = meta[urlFields[u]];
          if (typeof mval === 'string' && mval.length > 0) {
            result.hasNext = true;
            result.nextUrl = mval;
            return result;
          }
        }
      }
    }

    // --- RFC 5988 Link header ---
    var headers = responseHeaders || {};
    var linkHeader = headers['Link'] || headers['link'] || '';
    if (linkHeader) {
      var nextMatch = linkHeader.match(/<([^>]+)>;\s*rel="next"/);
      if (nextMatch) {
        result.hasNext = true;
        result.nextUrl = nextMatch[1];
        return result;
      }
    }

    // --- Offset / limit arithmetic ---
    var offset = toNumber(jsonData.offset);
    var limit  = toNumber(jsonData.limit);
    var total  = toNumber(jsonData.total || jsonData.totalCount || jsonData.total_count);
    if (offset !== null && limit !== null && total !== null) {
      var nextOffset = offset + limit;
      if (nextOffset < total) {
        result.hasNext = true;
        result.nextOffset = nextOffset;
        return result;
      }
      // We've reached the end
      return result;
    }

    // --- Page number arithmetic ---
    var page       = toNumber(jsonData.page || jsonData.current_page || jsonData.currentPage);
    var totalPages = toNumber(jsonData.total_pages || jsonData.totalPages || jsonData.last_page || jsonData.lastPage);
    if (page !== null && totalPages !== null) {
      if (page < totalPages) {
        result.hasNext = true;
        result.nextPage = page + 1;
        return result;
      }
      return result;
    }

    return result;
  }

  /** Safe coercion to a non-negative integer, or null. */
  function toNumber(v) {
    if (v === null || v === undefined) return null;
    var n = Number(v);
    if (isNaN(n) || n < 0) return null;
    return n;
  }

  // -------------------------------------------------------------------
  // toDataset(jsonData, options)
  // -------------------------------------------------------------------
  /**
   * Convert a JSON response into moke's dataset format.
   *
   * Options:
   *   path     {string}   — explicit JSON path to the data array
   *   flatten  {boolean}  — flatten nested objects via dot notation (default false)
   *   columns  {string[]} — keep only these columns (after flattening)
   *   rename   {Object}   — map of oldName → newName for columns
   *   name     {string}   — dataset name (default 'Untitled')
   *
   * @param {*} jsonData
   * @param {Object} [options]
   * @returns {{ name: string, headers: string[], rows: Array<Object>, meta: Object }}
   */
  function toDataset(jsonData, options) {
    var opts = options || {};

    // If an explicit path was given, extract first
    var data = opts.path ? extractPath(jsonData, opts.path) : jsonData;

    // Detect structure
    var detected = detect(data);

    var rows = detected.rows;
    var headers = detected.headers;

    // Flatten nested objects if requested
    if (opts.flatten) {
      rows = rows.map(function (row) { return flatten(row); });
      headers = collectHeaders(rows);
    }

    // Select specific columns
    if (opts.columns && opts.columns.length > 0) {
      var colSet = {};
      for (var c = 0; c < opts.columns.length; c++) {
        colSet[opts.columns[c]] = true;
      }
      headers = headers.filter(function (h) { return colSet[h]; });
      rows = rows.map(function (row) {
        var filtered = {};
        for (var c = 0; c < opts.columns.length; c++) {
          var col = opts.columns[c];
          if (row[col] !== undefined) {
            filtered[col] = row[col];
          }
        }
        return filtered;
      });
    }

    // Rename columns
    if (opts.rename && isPlainObject(opts.rename)) {
      var renameMap = opts.rename;
      headers = headers.map(function (h) { return renameMap[h] || h; });
      rows = rows.map(function (row) {
        var renamed = {};
        var keys = Object.keys(row);
        for (var k = 0; k < keys.length; k++) {
          var newKey = renameMap[keys[k]] || keys[k];
          renamed[newKey] = row[keys[k]];
        }
        return renamed;
      });
    }

    // Normalise every row so all headers are present (fill missing with null)
    rows = rows.map(function (row) {
      var normalised = {};
      for (var h = 0; h < headers.length; h++) {
        var key = headers[h];
        normalised[key] = row[key] !== undefined ? row[key] : null;
      }
      return normalised;
    });

    return {
      name: opts.name || 'Untitled',
      headers: headers,
      rows: rows,
      meta: {
        detectedType: detected.type,
        detectedPath: detected.path,
        rowCount: rows.length,
        columnCount: headers.length
      }
    };
  }

  // -------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------
  window.MokeJsonParser = {
    detect: detect,
    flatten: flatten,
    extractPath: extractPath,
    toDataset: toDataset,
    detectPagination: detectPagination,
    WRAPPER_PATTERNS: WRAPPER_PATTERNS
  };

})();
