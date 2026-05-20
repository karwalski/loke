/**
 * MokeRateLimiter — Rate limiting and retry for moke API connections (MK9.10)
 *
 * Provides per-host request queuing, 429/5xx retry with exponential backoff,
 * Retry-After header parsing, and a status panel for the connection manager.
 *
 * Usage:
 *   const response = await MokeRateLimiter.fetch(url, fetchOptions, {
 *     maxRetries: 3,
 *     baseDelay: 1000,
 *     maxConcurrent: 3
 *   });
 */
window.MokeRateLimiter = (function () {

  // ── Defaults ──────────────────────────────────────────────────────────

  var DEFAULT_MAX_RETRIES   = 3;
  var DEFAULT_BASE_DELAY    = 1000;   // 1 second
  var DEFAULT_MAX_CONCURRENT = 3;     // per host

  // ── Internal state (per-session, not persisted) ───────────────────────

  var _queues      = {};   // host -> [{resolve, reject, url, options, config}]
  var _active      = {};   // host -> number of in-flight requests
  var _stats       = {};   // host -> {requests, retries, rateLimits}
  var _rateLimited = {};   // host -> timestamp when rate limit expires

  // ── Helpers ───────────────────────────────────────────────────────────

  /**
   * Extract the host portion from a URL string.
   * Falls back to the raw URL if parsing fails.
   */
  function getHost(url) {
    try {
      return new URL(url).host;
    } catch (_e) {
      // Relative URL or unparseable — treat the whole string as the key.
      return url;
    }
  }

  /**
   * Parse a Retry-After header value.
   * Supports both delta-seconds ("120") and HTTP-date formats.
   * Returns the delay in milliseconds, minimum 1000 ms.
   */
  function parseRetryAfter(headerValue) {
    if (!headerValue) {
      return DEFAULT_BASE_DELAY;
    }

    // Try numeric seconds first.
    var seconds = Number(headerValue);
    if (!isNaN(seconds) && isFinite(seconds)) {
      return Math.max(seconds * 1000, 1000);
    }

    // Try HTTP-date.
    var date = new Date(headerValue);
    if (!isNaN(date.getTime())) {
      var delay = date.getTime() - Date.now();
      return Math.max(delay, 1000);
    }

    return DEFAULT_BASE_DELAY;
  }

  /**
   * Calculate exponential backoff with jitter.
   * delay = baseDelay * 2^attempt + random(0..500) ms
   */
  function calculateBackoff(attempt, baseDelay) {
    var base   = (baseDelay || DEFAULT_BASE_DELAY) * Math.pow(2, attempt);
    var jitter = Math.floor(Math.random() * 500);
    return base + jitter;
  }

  /**
   * Ensure internal tracking structures exist for a host.
   */
  function _ensureHost(host) {
    if (!_queues[host])  _queues[host]  = [];
    if (_active[host] === undefined) _active[host] = 0;
    if (!_stats[host])   _stats[host]   = { requests: 0, retries: 0, rateLimits: 0 };
  }

  // ── Core request execution ────────────────────────────────────────────

  /**
   * Execute a single fetch with retry logic.
   * - 429: honour Retry-After, then retry.
   * - 5xx: exponential backoff retry.
   * - 4xx (non-429): return immediately (no retry).
   */
  async function _executeWithRetry(url, options, config) {
    var maxRetries = (config && config.maxRetries !== undefined) ? config.maxRetries : DEFAULT_MAX_RETRIES;
    var baseDelay  = (config && config.baseDelay  !== undefined) ? config.baseDelay  : DEFAULT_BASE_DELAY;
    var host       = getHost(url);

    _ensureHost(host);
    _stats[host].requests++;

    for (var attempt = 0; attempt <= maxRetries; attempt++) {

      // If the host is currently rate-limited, wait until the window expires.
      if (_rateLimited[host] && Date.now() < _rateLimited[host]) {
        var waitMs = _rateLimited[host] - Date.now();
        if (waitMs > 0) {
          await _sleep(waitMs);
        }
      }

      var response;
      try {
        response = await fetch(url, options);
      } catch (networkError) {
        // Network-level failure — retry with backoff if attempts remain.
        if (attempt < maxRetries) {
          _stats[host].retries++;
          await _sleep(calculateBackoff(attempt, baseDelay));
          continue;
        }
        throw networkError;
      }

      // Success or non-retryable client error.
      if (response.ok || (response.status >= 400 && response.status < 500 && response.status !== 429)) {
        return response;
      }

      // 429 Too Many Requests — respect Retry-After.
      if (response.status === 429) {
        _stats[host].rateLimits++;

        if (attempt < maxRetries) {
          _stats[host].retries++;
          var retryAfterHeader = response.headers ? response.headers.get("Retry-After") : null;
          var delay = parseRetryAfter(retryAfterHeader);
          _rateLimited[host] = Date.now() + delay;
          await _sleep(delay);
          continue;
        }
        return response;
      }

      // 5xx Server Error — exponential backoff.
      if (response.status >= 500) {
        if (attempt < maxRetries) {
          _stats[host].retries++;
          await _sleep(calculateBackoff(attempt, baseDelay));
          continue;
        }
        return response;
      }

      // Anything else — return as-is.
      return response;
    }

    // Should not reach here, but safety net.
    return response;
  }

  /**
   * Simple async sleep helper.
   */
  function _sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  // ── Per-host queue management ─────────────────────────────────────────

  /**
   * Process the next item in a host's queue if a concurrency slot is open.
   */
  async function _processQueue(host) {
    var maxConcurrent = DEFAULT_MAX_CONCURRENT;

    // If the host is rate-limited, defer processing until the window expires.
    if (_rateLimited[host] && Date.now() < _rateLimited[host]) {
      var waitMs = _rateLimited[host] - Date.now();
      setTimeout(function () { _processQueue(host); }, waitMs);
      return;
    }

    while (_queues[host] && _queues[host].length > 0 && _active[host] < maxConcurrent) {
      var item = _queues[host].shift();

      // Override maxConcurrent from the item's config if provided.
      if (item.config && item.config.maxConcurrent !== undefined) {
        maxConcurrent = item.config.maxConcurrent;
      }

      _active[host]++;

      // Fire-and-forget: run the request, then open the slot for the next one.
      (function (entry) {
        _executeWithRetry(entry.url, entry.options, entry.config)
          .then(function (response) {
            entry.resolve(response);
          })
          .catch(function (err) {
            entry.reject(err);
          })
          .finally(function () {
            _active[host]--;
            _processQueue(host);
          });
      })(item);
    }
  }

  // ── Public API ────────────────────────────────────────────────────────

  /**
   * Main entry point. Queues the request by host, respects concurrency
   * limits, and retries on 429 / 5xx failures.
   *
   * @param {string} url
   * @param {object} [options]  - standard fetch options
   * @param {object} [config]   - {maxRetries, baseDelay, maxConcurrent}
   * @returns {Promise<Response>}
   */
  function rateLimitedFetch(url, options, config) {
    var host = getHost(url);
    _ensureHost(host);

    return new Promise(function (resolve, reject) {
      _queues[host].push({
        url: url,
        options: options || {},
        config: config || {},
        resolve: resolve,
        reject: reject
      });
      _processQueue(host);
    });
  }

  /**
   * Get current rate-limit status for a single host.
   */
  function getStatus(host) {
    _ensureHost(host);
    var now = Date.now();
    var isLimited = _rateLimited[host] && now < _rateLimited[host];

    return {
      queued:        (_queues[host] || []).length,
      active:        _active[host] || 0,
      rateLimited:   !!isLimited,
      retryAfter:    isLimited ? _rateLimited[host] - now : 0,
      totalRequests: _stats[host].requests,
      totalRetries:  _stats[host].retries
    };
  }

  /**
   * Get status for every tracked host.
   */
  function getAllStatus() {
    var hosts = {};
    var allKeys = Object.keys(_stats);
    for (var i = 0; i < allKeys.length; i++) {
      hosts[allKeys[i]] = getStatus(allKeys[i]);
    }
    return hosts;
  }

  /**
   * Render a compact status panel into the given container element.
   * Shows per-host: active/queued counts, rate-limit indicator, totals.
   */
  function renderStatus(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    var allStatus = getAllStatus();
    var hosts     = Object.keys(allStatus);

    if (hosts.length === 0) {
      container.innerHTML = '<div class="rate-limiter-empty">No API activity tracked.</div>';
      return;
    }

    var html = '<div class="rate-limiter-panel">';
    html += '<div class="rate-limiter-title">Rate Limit Status</div>';

    for (var i = 0; i < hosts.length; i++) {
      var host = hosts[i];
      var s    = allStatus[host];

      html += '<div class="rate-limiter-host">';
      html += '<span class="rate-limiter-hostname">' + _escapeHtml(host) + '</span>';

      // Rate-limit badge.
      if (s.rateLimited) {
        var countdown = Math.ceil(s.retryAfter / 1000);
        html += ' <span class="rate-limiter-badge rate-limited">'
              + '&#9679; limited (' + countdown + 's)</span>';
      }

      html += '<div class="rate-limiter-details">'
            + 'Active: ' + s.active
            + ' &middot; Queued: ' + s.queued
            + ' &middot; Requests: ' + s.totalRequests
            + ' &middot; Retries: ' + s.totalRetries
            + '</div>';
      html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;
  }

  /**
   * Minimal HTML escaping for status display.
   */
  function _escapeHtml(str) {
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
  }

  /**
   * Reset stats for a single host.
   */
  function resetStats(host) {
    if (_stats[host])       _stats[host] = { requests: 0, retries: 0, rateLimits: 0 };
    if (_rateLimited[host]) delete _rateLimited[host];
  }

  /**
   * Reset all internal state.
   */
  function resetAll() {
    var hosts = Object.keys(_stats);
    for (var i = 0; i < hosts.length; i++) {
      resetStats(hosts[i]);
    }
    // Clear queues (pending promises will never resolve — intentional on full reset).
    _queues      = {};
    _active      = {};
    _stats       = {};
    _rateLimited = {};
  }

  // ── Exported interface ────────────────────────────────────────────────

  return {
    // Defaults
    DEFAULT_MAX_RETRIES:    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_DELAY:     DEFAULT_BASE_DELAY,
    DEFAULT_MAX_CONCURRENT: DEFAULT_MAX_CONCURRENT,

    // Public methods
    fetch:            rateLimitedFetch,
    parseRetryAfter:  parseRetryAfter,
    calculateBackoff: calculateBackoff,
    getHost:          getHost,
    getStatus:        getStatus,
    getAllStatus:      getAllStatus,
    renderStatus:     renderStatus,
    resetStats:       resetStats,
    resetAll:         resetAll,

    // Internal state (exposed for inspection / testing)
    _queues:            _queues,
    _active:            _active,
    _stats:             _stats,
    _rateLimited:       _rateLimited,

    // Internal methods (exposed for testing)
    _processQueue:      _processQueue,
    _executeWithRetry:  _executeWithRetry
  };

})();
