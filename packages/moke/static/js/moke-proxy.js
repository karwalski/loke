/*
 * moke-proxy.js — the one way a moke page fetches a remote URL (MK19.9).
 *
 * A page cannot fetch a third-party API itself (CORS), so it asks moke's own
 * server: POST /api/proxy, same origin, with
 *
 *   { "url": "https://...", "method": "GET" | "POST",
 *     "headers": [{ "name": "...", "value": "..." }], "body": "..." }
 *
 * and moke answers an envelope:
 *
 *   { "ok": true,  "status": <upstream status>, "contentType": "...", "body": "..." }
 *   { "ok": false, "status": <upstream status or 0>, "error": "why" }
 *
 * The server decides what may be fetched (moke.proxy.guard): https only, port
 * 443, a host on the operator's allowlist (MOKE_PROXY_ALLOW, empty by default),
 * never an address on this machine or its network, redirects reported and never
 * followed, a 4 MiB body cap and a 15-second limit. Nothing here can widen that;
 * this file only shapes the request and reads the envelope.
 *
 * Six call sites use it: datagov-source.js, graphql-source.js,
 * openapi-discovery.js, url-import.js, auth-methods.js, and the Connections
 * page's Test Connection button. They used to post to an /api/proxy on loke's
 * port, where no such endpoint ever existed, in four different request shapes.
 */
(function (root) {
  'use strict';

  var ENDPOINT = '/api/proxy';

  // Headers as [{name, value}], from an object or from such an array.
  function headerList(h) {
    if (!h) return [];
    if (Array.isArray(h)) {
      return h.filter(function (x) { return x && x.name; })
              .map(function (x) { return { name: String(x.name), value: String(x.value == null ? '' : x.value) }; });
    }
    return Object.keys(h).filter(function (k) { return k && h[k] != null && h[k] !== ''; })
                         .map(function (k) { return { name: k, value: String(h[k]) }; });
  }

  function bodyText(b) {
    if (b == null) return '';
    if (typeof b === 'string') return b;
    return JSON.stringify(b);
  }

  /**
   * Send one request through moke's proxy. Resolves to the envelope, with
   * `proxyStatus` (the status /api/proxy itself answered) added. Never throws
   * for a refusal: the envelope says why.
   */
  async function request(opts) {
    var o = opts || {};
    var payload = {
      url: String(o.url || ''),
      method: String(o.method || 'GET').toUpperCase(),
      headers: headerList(o.headers),
      body: bodyText(o.body)
    };
    var resp = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    var env;
    try {
      env = await resp.json();
    } catch (e) {
      env = { ok: false, status: 0, error: 'moke’s proxy answered ' + resp.status + ' without an envelope' };
    }
    if (!env || typeof env !== 'object') env = { ok: false, status: 0, error: 'moke’s proxy answered nothing readable' };
    env.proxyStatus = resp.status;
    return env;
  }

  function describe(env) {
    if (!env) return 'no answer from moke’s proxy';
    if (!env.ok) return 'refused by moke’s proxy (' + env.proxyStatus + '): ' + (env.error || 'no reason given');
    return 'the upstream answered ' + env.status;
  }

  // The body of a 2xx answer, or an Error saying why there is none.
  async function text(opts) {
    var env = await request(opts);
    if (!env.ok || env.status < 200 || env.status >= 300) {
      var err = new Error(describe(env) + (env.ok && env.body ? ': ' + String(env.body).slice(0, 200) : ''));
      err.envelope = env;
      throw err;
    }
    return env.body;
  }

  async function json(opts) {
    return JSON.parse(await text(opts));
  }

  root.MokeProxy = { endpoint: ENDPOINT, request: request, text: text, json: json, describe: describe, headerList: headerList };
})(typeof window !== 'undefined' ? window : globalThis);
