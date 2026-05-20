/**
 * MK9.9 — API Response Caching for Moke
 *
 * Caches API responses locally in sessionStorage to reduce repeated calls
 * during analysis. Configurable TTL per connection (default 5 minutes).
 * Shows cache hit/miss in pipeline console. Manual cache clear button.
 * No external dependencies.
 */
(function () {
  'use strict';

  // -------------------------------------------------------------------
  // Constants
  // -------------------------------------------------------------------

  var STORAGE_KEY  = 'moke_api_cache';
  var TTL_STORAGE_KEY = 'moke_cache_ttl';
  var DEFAULT_TTL  = 300000; // 5 minutes in milliseconds

  // Auto-prune interval: every 60 seconds
  var PRUNE_INTERVAL = 60000;

  // -------------------------------------------------------------------
  // Internal state (per-session, not persisted)
  // -------------------------------------------------------------------

  var _hits   = 0;
  var _misses = 0;

  // -------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------

  /**
   * Simple deterministic string hash (djb2 variant).
   * Produces a hex string suitable for use as a cache key.
   */
  function hashString(str) {
    var hash = 5381;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash + str.charCodeAt(i)) & 0xffffffff;
    }
    // Convert to unsigned hex
    return (hash >>> 0).toString(16);
  }

  /**
   * Sort object keys and return a stable JSON string.
   * Returns empty string for null/undefined.
   */
  function stableStringify(obj) {
    if (obj == null) { return ''; }
    if (typeof obj === 'string') { return obj; }
    var keys = Object.keys(obj).sort();
    var parts = [];
    for (var i = 0; i < keys.length; i++) {
      parts.push(JSON.stringify(keys[i]) + ':' + JSON.stringify(obj[keys[i]]));
    }
    return '{' + parts.join(',') + '}';
  }

  /**
   * Read the full cache object from sessionStorage.
   * Returns empty object if nothing stored or parse fails.
   */
  function readStore() {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  /**
   * Write the full cache object to sessionStorage.
   * Handles quota errors by pruning then retrying.
   */
  function writeStore(store) {
    var json = JSON.stringify(store);
    try {
      sessionStorage.setItem(STORAGE_KEY, json);
    } catch (e) {
      // Likely quota exceeded — prune expired first, then evict oldest
      pruneExpired(store);
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      } catch (e2) {
        evictOldest(store);
        try {
          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
        } catch (e3) {
          console.warn('[MokeApiCache] sessionStorage quota exceeded, cache write failed');
        }
      }
    }
  }

  /**
   * Remove all expired entries from a store object (mutates in place).
   */
  function pruneExpired(store) {
    var now = Date.now();
    var keys = Object.keys(store);
    for (var i = 0; i < keys.length; i++) {
      var entry = store[keys[i]];
      if (entry && entry.cachedAt && entry.ttl) {
        if (now - entry.cachedAt > entry.ttl) {
          delete store[keys[i]];
        }
      }
    }
  }

  /**
   * Evict the oldest entry from a store object (LRU by cachedAt).
   */
  function evictOldest(store) {
    var keys = Object.keys(store);
    if (keys.length === 0) { return; }
    var oldestKey = keys[0];
    var oldestTime = store[keys[0]].cachedAt || Infinity;
    for (var i = 1; i < keys.length; i++) {
      var t = store[keys[i]].cachedAt || Infinity;
      if (t < oldestTime) {
        oldestTime = t;
        oldestKey = keys[i];
      }
    }
    delete store[oldestKey];
  }

  /**
   * Read per-connection TTL overrides from localStorage.
   */
  function readTTLOverrides() {
    try {
      var raw = localStorage.getItem(TTL_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  /**
   * Write per-connection TTL overrides to localStorage.
   */
  function writeTTLOverrides(overrides) {
    try {
      localStorage.setItem(TTL_STORAGE_KEY, JSON.stringify(overrides));
    } catch (e) {
      console.warn('[MokeApiCache] Could not persist TTL overrides');
    }
  }

  // -------------------------------------------------------------------
  // Periodic pruning
  // -------------------------------------------------------------------

  setInterval(function () {
    var store = readStore();
    var before = Object.keys(store).length;
    pruneExpired(store);
    var after = Object.keys(store).length;
    if (after < before) {
      writeStore(store);
    }
  }, PRUNE_INTERVAL);

  // -------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------

  var MokeApiCache = {

    STORAGE_KEY: STORAGE_KEY,
    TTL_STORAGE_KEY: TTL_STORAGE_KEY,
    DEFAULT_TTL: DEFAULT_TTL,

    // Expose counters (read-only access via stats())
    _hits: _hits,
    _misses: _misses,

    // -----------------------------------------------------------------
    // cacheKey — generate a deterministic key from request config
    // -----------------------------------------------------------------

    /**
     * Generate a deterministic cache key from request parameters.
     *
     * @param {string} url      — request URL
     * @param {string} method   — HTTP method (GET, POST, etc.)
     * @param {*}      body     — request body (string, object, or null)
     * @param {Object} headers  — request headers object
     * @returns {string} hex hash string
     */
    cacheKey: function (url, method, body, headers) {
      var parts = [
        (method || 'GET').toUpperCase(),
        url || '',
        stableStringify(headers),
        typeof body === 'string' ? body : stableStringify(body)
      ];
      return hashString(parts.join('|'));
    },

    // -----------------------------------------------------------------
    // get — retrieve cached response if still valid
    // -----------------------------------------------------------------

    /**
     * Get a cached response by key. Returns null if missing or expired.
     *
     * @param {string} key — cache key from cacheKey()
     * @returns {Object|null} {data, headers, status, cachedAt, ttl} or null
     */
    get: function (key) {
      var store = readStore();

      // Prune expired entries opportunistically
      pruneExpired(store);

      var entry = store[key];
      if (!entry) { return null; }

      var now = Date.now();
      if (now - entry.cachedAt > entry.ttl) {
        delete store[key];
        writeStore(store);
        return null;
      }

      return entry;
    },

    // -----------------------------------------------------------------
    // set — store a response in the cache
    // -----------------------------------------------------------------

    /**
     * Store a response in the cache.
     *
     * @param {string} key       — cache key
     * @param {Object} response  — {data, headers, status}
     * @param {number} [ttl]     — time-to-live in ms (defaults to DEFAULT_TTL)
     */
    set: function (key, response, ttl) {
      var store = readStore();
      store[key] = {
        data:     response.data,
        headers:  response.headers || {},
        status:   response.status || 200,
        cachedAt: Date.now(),
        ttl:      (typeof ttl === 'number' && ttl > 0) ? ttl : DEFAULT_TTL
      };
      writeStore(store);
    },

    // -----------------------------------------------------------------
    // has — check if a valid (non-expired) entry exists
    // -----------------------------------------------------------------

    /**
     * @param {string} key
     * @returns {boolean}
     */
    has: function (key) {
      return this.get(key) !== null;
    },

    // -----------------------------------------------------------------
    // remove — delete a specific cache entry
    // -----------------------------------------------------------------

    /**
     * @param {string} key
     */
    remove: function (key) {
      var store = readStore();
      delete store[key];
      writeStore(store);
    },

    // -----------------------------------------------------------------
    // clearAll — wipe the entire cache
    // -----------------------------------------------------------------

    clearAll: function () {
      try {
        sessionStorage.removeItem(STORAGE_KEY);
      } catch (e) {
        // ignore
      }
      _hits = 0;
      _misses = 0;
      MokeApiCache._hits = 0;
      MokeApiCache._misses = 0;
      console.log('[MokeApiCache] Cache cleared');
    },

    // -----------------------------------------------------------------
    // prune — remove all expired entries
    // -----------------------------------------------------------------

    prune: function () {
      var store = readStore();
      var before = Object.keys(store).length;
      pruneExpired(store);
      var after = Object.keys(store).length;
      if (after < before) {
        writeStore(store);
      }
      return before - after;
    },

    // -----------------------------------------------------------------
    // stats — return current session statistics
    // -----------------------------------------------------------------

    /**
     * @returns {Object} {entries, totalSize, hits, misses, hitRate}
     */
    stats: function () {
      var store = readStore();
      var keys = Object.keys(store);
      var totalSize = JSON.stringify(store).length;
      var total = _hits + _misses;
      return {
        entries:   keys.length,
        totalSize: totalSize,
        hits:      _hits,
        misses:    _misses,
        hitRate:   total > 0 ? Math.round((_hits / total) * 100) : 0
      };
    },

    // -----------------------------------------------------------------
    // setTTL / getTTL — per-connection TTL management
    // -----------------------------------------------------------------

    /**
     * Set a custom TTL for a specific connection.
     * Persisted in localStorage so it survives page reloads.
     *
     * @param {string} connectionName
     * @param {number} ttlMs — time-to-live in milliseconds
     */
    setTTL: function (connectionName, ttlMs) {
      var overrides = readTTLOverrides();
      overrides[connectionName] = ttlMs;
      writeTTLOverrides(overrides);
    },

    /**
     * Get the TTL for a connection. Falls back to DEFAULT_TTL.
     *
     * @param {string} connectionName
     * @returns {number} TTL in milliseconds
     */
    getTTL: function (connectionName) {
      if (!connectionName) { return DEFAULT_TTL; }
      var overrides = readTTLOverrides();
      return (typeof overrides[connectionName] === 'number')
        ? overrides[connectionName]
        : DEFAULT_TTL;
    },

    // -----------------------------------------------------------------
    // cachedFetch — drop-in fetch wrapper with caching
    // -----------------------------------------------------------------

    /**
     * Fetch with caching. Checks cache first; on miss, performs the
     * fetch, caches the response, and returns it.
     *
     * @param {string} url             — request URL
     * @param {Object} [options]       — fetch options (method, headers, body)
     * @param {string} [connectionName] — connection name for TTL lookup
     * @returns {Promise<Response>} resolves with a Response-like object
     */
    cachedFetch: function (url, options, connectionName) {
      var self = this;
      options = options || {};
      var method  = (options.method || 'GET').toUpperCase();
      var headers = options.headers || {};
      var body    = options.body || null;
      var ttl     = self.getTTL(connectionName);

      var key = self.cacheKey(url, method, body, headers);

      // Check cache
      var cached = self.get(key);
      if (cached) {
        _hits++;
        self._hits = _hits;
        console.log('[cache HIT] ' + method + ' ' + url);
        return Promise.resolve({
          ok:      cached.status >= 200 && cached.status < 300,
          status:  cached.status,
          headers: cached.headers,
          json:    function () { return Promise.resolve(cached.data); },
          text:    function () { return Promise.resolve(
            typeof cached.data === 'string' ? cached.data : JSON.stringify(cached.data)
          ); },
          _fromCache: true
        });
      }

      // Cache miss — perform real fetch
      _misses++;
      self._misses = _misses;
      console.log('[cache MISS] ' + method + ' ' + url);

      return fetch(url, options).then(function (response) {
        var status = response.status;
        var respHeaders = {};

        // Extract headers into plain object
        if (response.headers && typeof response.headers.forEach === 'function') {
          response.headers.forEach(function (value, name) {
            respHeaders[name] = value;
          });
        }

        // Clone and read body
        return response.clone().text().then(function (text) {
          var data;
          try {
            data = JSON.parse(text);
          } catch (e) {
            data = text;
          }

          // Only cache successful responses
          if (status >= 200 && status < 300) {
            self.set(key, {
              data:    data,
              headers: respHeaders,
              status:  status
            }, ttl);
          }

          return response;
        });
      });
    },

    // -----------------------------------------------------------------
    // renderCacheStatus — render a compact status panel
    // -----------------------------------------------------------------

    /**
     * Render a cache status panel into the given container element.
     * Shows entry count, total size, hit/miss ratio, and a clear button.
     *
     * @param {string} containerId — ID of the DOM element to render into
     */
    renderCacheStatus: function (containerId) {
      var self = this;
      var container = document.getElementById(containerId);
      if (!container) {
        console.warn('[MokeApiCache] Container not found: ' + containerId);
        return;
      }

      var s = self.stats();
      var sizeKB = (s.totalSize / 1024).toFixed(1);

      var html = ''
        + '<div class="moke-cache-status" style="'
        + 'font-family:monospace;font-size:12px;padding:8px 12px;'
        + 'background:#1a1a2e;color:#a0a0b8;border:1px solid #2a2a3e;'
        + 'border-radius:4px;margin:4px 0;">'
        + '<div style="display:flex;align-items:center;justify-content:space-between;">'
        + '<span style="font-weight:600;color:#c0c0d8;">API Cache</span>'
        + '<button id="moke-cache-clear-btn" style="'
        + 'background:#2a2a3e;color:#e0e0f0;border:1px solid #3a3a4e;'
        + 'border-radius:3px;padding:2px 8px;cursor:pointer;font-size:11px;'
        + 'font-family:monospace;"'
        + '>Clear Cache</button>'
        + '</div>'
        + '<div style="margin-top:6px;display:flex;gap:16px;flex-wrap:wrap;">'
        + '<span>Entries: <b>' + s.entries + '</b></span>'
        + '<span>Size: <b>' + sizeKB + ' KB</b></span>'
        + '<span>Hits: <b>' + s.hits + '</b></span>'
        + '<span>Misses: <b>' + s.misses + '</b></span>'
        + '<span>Hit rate: <b>' + s.hitRate + '%</b></span>'
        + '</div>'
        + '</div>';

      container.innerHTML = html;

      // Attach clear button handler
      var btn = document.getElementById('moke-cache-clear-btn');
      if (btn) {
        btn.addEventListener('click', function () {
          self.clearAll();
          self.renderCacheStatus(containerId);
        });
      }
    }
  };

  // -------------------------------------------------------------------
  // Expose on window
  // -------------------------------------------------------------------

  window.MokeApiCache = MokeApiCache;

})();
