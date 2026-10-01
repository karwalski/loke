/*
 * test-moke-proxy.js — every call site of /api/proxy goes through moke-proxy.js (MK19.9).
 *
 * Run: node packages/moke/static/js/tests/test-moke-proxy.js
 *
 * Six call sites referenced an /api/proxy that did not exist, on loke's port
 * (LOKE_URL), in four different request shapes. They now share one client,
 * moke-proxy.js, which posts to moke's own /api/proxy. This drives the REAL
 * modules — datagov-source.js, graphql-source.js, openapi-discovery.js,
 * url-import.js and auth-methods.js — with fetch answered here, and checks for
 * each one:
 *
 *   - that it posted once, to the same-origin '/api/proxy', as application/json,
 *     and never to loke's port;
 *   - that the request is the one contract ({url, method, headers:[{name,value}],
 *     body}) with the target URL, method, headers and body the call site meant;
 *   - that an ok envelope's body comes back as the module's result;
 *   - that a refusal's reason reaches the caller in the Error, rather than a
 *     generic failure.
 *
 * The Connections page's Test Connection button is checked in a real browser by
 * tests/ui/proxy_mk199.json (smoke_ui.sh). This file also fails if any template
 * or script still names loke's port for the proxy or the retired X-Loke-Target
 * header.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const MOKE = path.resolve(__dirname, '../../..');
const JS = path.join(MOKE, 'static/js');

global.window = globalThis;
window.LOKE_URL = 'http://127.0.0.1:11430';
global.localStorage = { _v: {}, getItem(k) { return this._v[k] || null; }, setItem(k, v) { this._v[k] = String(v); }, removeItem(k) { delete this._v[k]; } };
global.sessionStorage = { _v: {}, getItem(k) { return this._v[k] || null; }, setItem(k, v) { this._v[k] = String(v); }, removeItem(k) { delete this._v[k]; } };

// fetch is answered here: `next` is the envelope the proxy answers, and every
// request is recorded. Anything but /api/proxy is a failure, so a call site
// that still went to loke would be seen.
const sent = [];
let next = null;
global.fetch = async (url, init) => {
  sent.push({ url: String(url), init: init || {} });
  const env = next;
  return {
    ok: env.proxyStatus === 200,
    status: env.proxyStatus,
    json: async () => { const e = Object.assign({}, env); delete e.proxyStatus; return e; },
    text: async () => JSON.stringify(env)
  };
};
function answer(body, contentType) { next = { proxyStatus: 200, ok: true, status: 200, contentType: contentType || 'application/json', body: body }; }
function refuse(reason) { next = { proxyStatus: 403, ok: false, status: 0, error: reason }; }

let pass = 0, fail = 0;
const t = (label, cond) => { if (cond) { pass++; } else { console.log('FAIL     ' + label); fail++; } };

require(path.join(JS, 'moke-proxy.js'));
['datagov-source.js', 'graphql-source.js', 'openapi-discovery.js', 'url-import.js', 'auth-methods.js']
  .forEach(f => require(path.join(JS, f)));

// The one request the last call made, decoded.
function lastRequest(label) {
  t(label + ': exactly one request was sent', sent.length === 1);
  const r = sent[sent.length - 1] || { url: '', init: {} };
  t(label + ': to moke’s own /api/proxy, never loke’s port', r.url === '/api/proxy');
  t(label + ': as a POST', r.init.method === 'POST');
  const h = r.init.headers || {};
  t(label + ': of application/json (a cross-origin page needs a preflight to send this)', h['Content-Type'] === 'application/json');
  let p = {};
  try { p = JSON.parse(r.init.body); } catch (e) { t(label + ': with a JSON body', false); }
  t(label + ': in the one contract (url, method, headers as a list, body as text)',
    typeof p.url === 'string' && typeof p.method === 'string' && Array.isArray(p.headers) && typeof p.body === 'string');
  sent.length = 0;
  return p;
}
const header = (p, name) => (p.headers.find(h => h.name.toLowerCase() === name.toLowerCase()) || {}).value;

async function rejects(fn) {
  try { await fn(); return ''; } catch (e) { return e.message; }
}

(async () => {
  // ── datagov-source.js: search (JSON) and downloadCSV (text) ───────────────
  answer(JSON.stringify({ success: true, result: { count: 1, results: [{ id: 'roads', title: 'Roads', resources: [] }] } }));
  const found = await window.MokeDataGov.search('road deaths', { rows: 5 });
  let p = lastRequest('datagov search');
  t('datagov search: names the CKAN package_search URL', /^https:\/\/data\.gov\.au\/data\/api\/3\/action\/package_search\?q=road%20deaths&rows=5/.test(p.url));
  t('datagov search: a GET with Accept: application/json', p.method === 'GET' && header(p, 'Accept') === 'application/json');
  t('datagov search: the envelope’s body is what it parsed', found.count === 1 && found.results[0].id === 'roads');

  answer('a,b\n1,2\n', 'text/csv');
  const csv = await window.MokeDataGov.downloadCSV('https://data.gov.au/x.csv', 'x');
  p = lastRequest('datagov downloadCSV');
  t('datagov downloadCSV: names the resource URL', p.url === 'https://data.gov.au/x.csv' && p.method === 'GET');
  t('datagov downloadCSV: parses the text the envelope carried', csv.rows.length === 1 && csv.headers.join() === 'a,b');

  refuse('host not on the proxy allowlist (MOKE_PROXY_ALLOW): data.gov.au');
  let m = await rejects(() => window.MokeDataGov.search('x'));
  sent.length = 0;
  t('datagov search: a refusal reaches the caller with its reason', /refused by moke’s proxy \(403\): host not on the proxy allowlist/.test(m));

  // ── graphql-source.js: execute (POST with a JSON body) ────────────────────
  answer(JSON.stringify({ data: { items: [{ id: 1 }] } }));
  const gq = await window.MokeGraphQL.execute('https://api.example.com/graphql', '{ items { id } }', { n: 1 }, { Authorization: 'Bearer t' });
  p = lastRequest('graphql execute');
  t('graphql execute: POSTs to the endpoint', p.url === 'https://api.example.com/graphql' && p.method === 'POST');
  t('graphql execute: the query and variables are the body', JSON.parse(p.body).query === '{ items { id } }' && JSON.parse(p.body).variables.n === 1);
  t('graphql execute: the caller’s headers go with it, and no X-Loke-Target', header(p, 'Authorization') === 'Bearer t' && !header(p, 'X-Loke-Target'));
  t('graphql execute: the result is the upstream’s JSON', gq.data.items[0].id === 1);
  refuse('blocked address: private (10.0.0.0/8)');
  m = await rejects(() => window.MokeGraphQL.execute('https://10.0.0.1/graphql', '{x}'));
  sent.length = 0;
  t('graphql execute: a refusal reaches the caller with its reason', /GraphQL request failed: .*private/.test(m));

  // ── openapi-discovery.js: fetch a spec ────────────────────────────────────
  answer(JSON.stringify({ openapi: '3.0.0', info: { title: 'T', version: '1' }, paths: {} }));
  const spec = await window.MokeOpenAPI.fetch('https://api.example.com/openapi.json');
  p = lastRequest('openapi fetch');
  t('openapi fetch: a GET of the spec URL', p.url === 'https://api.example.com/openapi.json' && p.method === 'GET');
  t('openapi fetch: the spec is parsed from the envelope’s body', spec && spec._raw && spec._raw.openapi === '3.0.0');
  refuse('https only: the URL must start https://');
  m = await rejects(() => window.MokeOpenAPI.fetch('http://api.example.com/openapi.json'));
  sent.length = 0;
  t('openapi fetch: a refusal reaches the caller with its reason', /Failed to fetch spec: .*https only/.test(m));

  // ── url-import.js: import a CSV ───────────────────────────────────────────
  answer('city,n\nPerth,3\nHobart,4\n', 'text/csv');
  const ds = await window.MokeUrlImport.importFromUrl('https://data.example.org/towns.csv');
  p = lastRequest('url-import');
  t('url-import: a GET of the file URL', p.url === 'https://data.example.org/towns.csv' && p.method === 'GET');
  t('url-import: the rows come from the envelope’s body', ds.rows.length === 2 && ds.headers.join() === 'city,n');
  refuse('local name: printer.local is never proxied');
  m = await rejects(() => window.MokeUrlImport.importFromUrl('https://printer.local/x.csv'));
  sent.length = 0;
  t('url-import: a refusal reaches the caller with its reason', /local name/.test(m));
  answer('x', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  m = await rejects(() => window.MokeUrlImport.importFromUrl('https://data.example.org/book.xlsx'));
  sent.length = 0;
  t('url-import: an Excel file is refused plainly, as text-only, not mis-parsed', /carries text only/.test(m));

  // ── auth-methods.js: the OAuth2 client-credentials token request ─────────
  answer(JSON.stringify({ access_token: 'tok', token_type: 'bearer', expires_in: 60 }));
  const tok = await window.MokeAuth.fetchOAuth2Token('https://auth.example.com/token', 'id', 'se cret', 'read');
  p = lastRequest('oauth token');
  t('oauth token: a POST to the token URL', p.url === 'https://auth.example.com/token' && p.method === 'POST');
  t('oauth token: form-encoded, as the token endpoint expects', header(p, 'Content-Type') === 'application/x-www-form-urlencoded');
  t('oauth token: with the grant in the body', p.body === 'grant_type=client_credentials&client_id=id&client_secret=se%20cret&scope=read');
  t('oauth token: the token comes back from the envelope', tok.access_token === 'tok');
  refuse('the upstream answered 302, a redirect; redirects are not followed');
  m = await rejects(() => window.MokeAuth.fetchOAuth2Token('https://auth.example.com/token', 'id', 's', ''));
  sent.length = 0;
  t('oauth token: a refusal reaches the caller with its reason', /redirects are not followed/.test(m));

  // ── An upstream error status is an error, with the status ────────────────
  next = { proxyStatus: 200, ok: true, status: 404, contentType: 'text/plain', body: 'no such thing' };
  m = await rejects(() => window.MokeProxy.text({ url: 'https://api.example.com/x' }));
  sent.length = 0;
  t('MokeProxy.text: an upstream 404 is an error naming the status', /the upstream answered 404/.test(m));

  // ── Nothing still points at loke for the proxy ───────────────────────────
  const files = fs.readdirSync(JS).filter(f => f.endsWith('.js')).map(f => path.join(JS, f))
    .concat(fs.readdirSync(path.join(MOKE, 'templates')).filter(f => f.endsWith('.tkt')).map(f => path.join(MOKE, 'templates', f)));
  const stale = files.filter(f => {
    const s = fs.readFileSync(f, 'utf8');
    return /X-Loke-Target|LOKE_URL[^\n;]*\/api\/proxy|lokeUrl\(\)\s*\+\s*'\/api\/proxy'/.test(s);
  }).map(f => path.relative(MOKE, f));
  t('no script or template still sends the proxy to loke or uses X-Loke-Target' + (stale.length ? ' (' + stale.join(', ') + ')' : ''), stale.length === 0);
  const conn = fs.readFileSync(path.join(MOKE, 'templates/connections.tkt'), 'utf8');
  t('the Connections page loads moke-proxy.js before its own script', conn.indexOf('<script src="/static/js/moke-proxy.js"></script>') >= 0
    && conn.indexOf('<script src="/static/js/moke-proxy.js"></script>') < conn.indexOf('window.MokeProxy.request('));

  console.log(`test-moke-proxy: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.log('FAIL     threw: ' + (e && e.stack || e)); process.exit(1); });
