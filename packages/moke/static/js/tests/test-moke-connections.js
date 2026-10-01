/*
 * test-moke-connections.js — the connection modules are mounted, every request
 * they make goes through moke's proxy, and every load goes through the one
 * active-dataset write (MK19.8).
 *
 * Run: node packages/moke/static/js/tests/test-moke-connections.js
 *
 * Nine modules in static/js were referenced only by a standalone test runner;
 * templates/connections.tkt had empty placeholder comments where they belonged,
 * and its "Load as Dataset" button stashed the raw response in a second
 * sessionStorage key and said a parser was unimplemented. This drives the REAL
 * modules with fetch answered here, as moke's /api/proxy answers, and checks:
 *
 *   - the page loads all nine, after moke-proxy.js and moke-data.js, and calls
 *     each one's mount; no placeholder comment, second copy or "unimplemented"
 *     string is left;
 *   - datagov-source.js names the CKAN base data.gov.au really serves,
 *     /data/api/3/action (the old /api/3/action answers 404 with HTML);
 *   - MokeActive.load takes a fetched table (JSON object rows, CSV array rows)
 *     and writes it, in the store's shape, as the one active dataset; an empty
 *     table is refused and leaves the active dataset alone; the source URL is
 *     kept without its query (an API key may be there);
 *   - a saved connection's Load goes cache -> rate limiter -> /api/proxy, with
 *     the page's saved shape of headers and params; a cached answer sends
 *     nothing; a fresh one does; a refusal is reported with its reason and is
 *     never retried; nothing ever fetches a target URL directly;
 *   - this visit's credentials are applied but never stored or exported;
 *   - live refresh is off after load even for a connection saved with a
 *     schedule, is not persisted, and announces what it fetched;
 *   - a canned successful envelope, as the Connections page receives it, parses
 *     (toTable) and loads (MokeActive.load) into the active dataset.
 *
 * A successful load against a live host is not tested here or anywhere: moke's
 * proxy refuses every loopback and private address in production (MK19.9), so no
 * local stand-in can be fetched through it, and no test may reach the internet.
 * The page's handling of that success is driven in a real browser with the same
 * canned envelope by tests/ui/connections_mk198.json.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const MOKE = path.resolve(__dirname, '../../..');
const JS = path.join(MOKE, 'static/js');

global.window = globalThis;
function store() { return { _v: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._v, k) ? this._v[k] : null; }, setItem(k, v) { this._v[k] = String(v); }, removeItem(k) { delete this._v[k]; } }; }
global.localStorage = store();
global.sessionStorage = store();
global.document = new EventTarget();

// fetch is answered as moke's /api/proxy answers: `next` is the envelope, and
// every request is recorded. Any URL but '/api/proxy' is recorded too, so a
// module that fetched a target directly would be seen.
const sent = [];
let next = null;
global.fetch = async (url, init) => {
  sent.push({ url: String(url), init: init || {} });
  const env = next;
  // A whole Response shape, so a module that fetched a target directly runs on
  // to the named assertion that catches it rather than crashing first.
  const r = {
    ok: env.proxyStatus === 200,
    status: env.proxyStatus,
    headers: new Map([['content-type', 'application/json']]),
    json: async () => { const e = Object.assign({}, env); delete e.proxyStatus; return e; },
    text: async () => JSON.stringify(env),
    clone: () => r
  };
  return r;
};
function answer(body, contentType, status) { next = { proxyStatus: 200, ok: true, status: status || 200, contentType: contentType || 'application/json', body: body }; }
function refuse(reason) { next = { proxyStatus: 403, ok: false, status: 0, error: reason }; }
const posted = () => sent.map(r => { try { return JSON.parse(r.init.body); } catch (e) { return {}; } });

let pass = 0, fail = 0;
const t = (label, cond) => { if (cond) { pass++; } else { console.log('FAIL     ' + label); fail++; } };
async function rejects(fn) { try { await fn(); return ''; } catch (e) { return e.message || String(e); } }

// A connection saved with a live-refresh schedule, before the module loads.
localStorage.setItem('moke_api_connections', JSON.stringify([{
  id: 'conn_1', name: 'Towns', method: 'GET', url: 'https://api.example.org/towns',
  auth: 'bearer', headers: [{ key: 'Accept', value: 'application/json' }],
  params: [{ key: 'state', value: 'TAS' }], body: '', schedule: 5
}]));

const NINE = ['json-parser.js', 'rate-limiter.js', 'api-cache.js', 'auth-methods.js', 'graphql-source.js',
  'openapi-discovery.js', 'datagov-source.js', 'url-import.js', 'connection-manager.js'];
require(path.join(JS, 'moke-proxy.js'));
require(path.join(JS, 'moke-data.js'));
NINE.forEach(f => require(path.join(JS, f)));
const CM = window.MokeConnectionManager;

(async () => {
  // ── The page mounts all nine ───────────────────────────────────────────
  const page = fs.readFileSync(path.join(MOKE, 'templates/connections.tkt'), 'utf8');
  const at = f => page.indexOf('<script src="/static/js/' + f + '"></script>');
  t('connections.tkt loads moke-proxy.js before moke-data.js', at('moke-proxy.js') >= 0 && at('moke-proxy.js') < at('moke-data.js'));
  NINE.forEach(f => t('connections.tkt loads ' + f + ' after moke-data.js and before its own script',
    at(f) > at('moke-data.js') && at(f) < page.indexOf("'use strict'")));
  [
    ["MokeAuth.renderAuthForm(", 'auth-methods.js (MK9.5)'],
    ["MokeGraphQL.execute(", 'graphql-source.js (MK9.3)'],
    ["MokeOpenAPI.fetch(", 'openapi-discovery.js (MK9.4)'],
    ["MokeConnectionManager.toTable(", 'json-parser.js through toTable (MK9.2)'],
    ["MokeConnectionManager.renderConnectionList('mcm-list')", 'connection-manager.js (MK9.8)'],
    ["MokeDataGov.renderSearchUI('datagov-browser')", 'datagov-source.js (MK9.6)'],
    ["MokeUrlImport.renderImportForm('url-import-form')", 'url-import.js'],
    ["MokeApiCache.renderCacheStatus('cache-status')", 'api-cache.js (MK9.9)'],
    ["MokeRateLimiter.renderStatus('rate-status')", 'rate-limiter.js (MK9.10)']
  ].forEach(([call, what]) => t('connections.tkt mounts ' + what, page.indexOf(call) >= 0));
  ['auth-fields', 'mcm-list', 'datagov-browser', 'url-import-form', 'cache-status', 'rate-status', 'parse-preview', 'gql-query', 'openapi-url']
    .forEach(id => t('connections.tkt has the #' + id + ' mount point', page.indexOf('id="' + id + '"') >= 0));
  t('no empty MK9.x placeholder comment is left', !/<!--\s*MK9\.\d+:[^>]*-->/.test(page));
  t('Load as Dataset is not disabled by an "unimplemented" message', !/will be available when|is implemented/.test(page));
  t('the page writes no second copy of a response (no moke_api_response, no sessionStorage.setItem)',
    page.indexOf('moke_api_response') < 0 && page.indexOf('sessionStorage.setItem') < 0);
  const loadFn = page.slice(page.indexOf('function loadTable('), page.indexOf('function loadTable(') + 400);
  t('every load on the page goes through MokeActive.load', /window\.MokeActive\.load\(table, sensSel\.value\)/.test(loadFn));
  t('the allowlist notice says a connection is refused by the allowlist when none is set',
    /MOKE_PROXY_ALLOW<\/code>/.test(page) && /refused by the allowlist/.test(page));
  t('no page module calls startScheduler on load (live refresh is never the demo path)',
    page.indexOf('startScheduler') < 0 && typeof CM.startScheduler === 'undefined');

  // ── data.gov.au's CKAN base ───────────────────────────────────────────
  t('datagov BASE_URL is /data/api/3/action', window.MokeDataGov.BASE_URL === 'https://data.gov.au/data/api/3/action');
  answer(JSON.stringify({ success: true, result: { id: 'roads', title: 'Roads', resources: [] } }));
  await window.MokeDataGov.getDataset('road deaths');
  t('datagov getDataset asks package_show under /data/api/3/action',
    sent.length === 1 && posted()[0].url === 'https://data.gov.au/data/api/3/action/package_show?id=road%20deaths');
  sent.length = 0;
  const wrongBase = fs.readdirSync(JS).filter(f => f.endsWith('.js'))
    .filter(f => /data\.gov\.au\/api\/3\/action/.test(fs.readFileSync(path.join(JS, f), 'utf8')));
  t('no module still names the 404ing /api/3/action base' + (wrongBase.length ? ' (' + wrongBase.join(', ') + ')' : ''), wrongBase.length === 0);

  // ── MokeActive.load takes a fetched table ─────────────────────────────
  const objTable = { name: 'Towns', connection: 'Towns', url: 'https://api.example.org/towns?api_key=SECRET&state=TAS',
    headers: ['city', 'n', 'geo'], rows: [{ city: 'Perth', n: 3, geo: { lat: 1 } }, { n: 4, city: 'Hobart', geo: null }] };
  const ds = await window.MokeActive.load(objTable, 'INTERNAL');
  const active = JSON.parse(sessionStorage.getItem('moke_dataset'));
  t('a fetched table becomes the active dataset', active && active.name === 'Towns' && active.rows.length === 2 && ds.rows.length === 2);
  t('object rows are stored as arrays in header order, as the store’s are',
    JSON.stringify(active.rows) === JSON.stringify([['Perth', '3', '{"lat":1}'], ['Hobart', '4', '']]));
  t('the chosen sensitivity is kept', active.sensitivity === 'INTERNAL');
  t('it defaults to CONFIDENTIAL', JSON.parse(JSON.stringify(await window.MokeActive.load({ headers: ['a'], rows: [['1']] }))).sensitivity === 'CONFIDENTIAL');
  await window.MokeActive.load(objTable, 'INTERNAL');
  const again = JSON.parse(sessionStorage.getItem('moke_dataset'));
  t('the source URL is kept without its query (no API key in the active dataset)',
    again.source.url === 'https://api.example.org/towns' && sessionStorage.getItem('moke_dataset').indexOf('SECRET') < 0);
  t('the connection it came from is recorded, for live refresh', again.source.connection === 'Towns' && again.source.kind === 'connection');
  const arrTable = await window.MokeActive.load({ name: 'csv', headers: ['a', 'b'], rows: [['1', '2']] });
  t('array rows load as they are', JSON.stringify(arrTable.rows) === '[["1","2"]]');
  const before = sessionStorage.getItem('moke_dataset');
  let m = await rejects(() => window.MokeActive.load({ name: 'empty', headers: ['a'], rows: [] }));
  t('an empty table is refused with a reason', /no rows to load/.test(m));
  t('and the active dataset is left as it was', sessionStorage.getItem('moke_dataset') === before);
  t('the only keys written are the active dataset (no second copy)',
    Object.keys(sessionStorage._v).filter(k => k !== 'moke_api_cache').join() === 'moke_dataset');

  // ── live refresh is off after load ────────────────────────────────────
  t('a connection saved with a schedule has no live-refresh timer after load', Object.keys(CM._timers).length === 0);

  // ── A saved connection's Load: cache -> rate limiter -> proxy ─────────
  CM.setSessionAuth('Towns', { type: 'bearer', token: 'tok-123' });
  answer(JSON.stringify({ results: [{ city: 'Hobart', n: 4 }, { city: 'Launceston', n: 2 }] }));
  const table = await CM.fetch('Towns');
  t('a Load sends exactly one request, to moke’s /api/proxy', sent.length === 1 && sent[0].url === '/api/proxy' && sent[0].init.method === 'POST');
  let p = posted()[0];
  t('with the saved params in the URL', p.url === 'https://api.example.org/towns?state=TAS');
  const hdr = n => ((p.headers || []).find(h => h.name.toLowerCase() === n.toLowerCase()) || {}).value;
  t('with the saved headers (the page’s [{key,value}] shape is read)', hdr('Accept') === 'application/json');
  t('and this visit’s credentials applied', hdr('Authorization') === 'Bearer tok-123');
  t('the JSON is tabulated by json-parser.js', table.headers.join() === 'city,n' && table.rows.length === 2 && table.meta.detectedPath === 'results');
  t('the table names its connection', table.connection === 'Towns' && table.name === 'Towns');
  sent.length = 0;
  await CM.fetch('Towns');
  t('a second Load within the TTL is answered by the cache and sends nothing', sent.length === 0);
  await CM.fetch('Towns', { fresh: true });
  t('a fresh fetch (live refresh) skips the cache and sends one request', sent.length === 1);
  sent.length = 0;
  t('credentials are never written to localStorage', JSON.stringify(localStorage._v).indexOf('tok-123') < 0);
  t('nor exported', CM.exportConfig().indexOf('tok-123') < 0);

  // ── A refusal: reported with its reason, never retried ────────────────
  refuse('host not on the proxy allowlist (MOKE_PROXY_ALLOW): api.example.org');
  const tested = await CM.test('Towns');
  t('a refused Test reports the allowlist refusal and its reason',
    tested.ok === false && /refused by moke’s proxy \(403\): host not on the proxy allowlist \(MOKE_PROXY_ALLOW\): api\.example\.org/.test(tested.error));
  t('a refusal is not retried (one request)', sent.length === 1);
  sent.length = 0;
  m = await rejects(() => CM.fetch('Towns', { fresh: true }));
  t('a refused Load rejects with the reason', /not on the proxy allowlist/.test(m));
  sent.length = 0;

  // ── Nothing fetches a target directly ─────────────────────────────────
  answer('a,b\n1,2\n', 'text/csv');
  const viaCache = await window.MokeApiCache.cachedFetch('https://api.example.org/x.csv', { method: 'GET' });
  const viaRate = await window.MokeRateLimiter.fetch('https://api.example.org/y.csv', { method: 'GET' });
  t('api-cache and rate-limiter send through /api/proxy only', sent.length === 2 && sent.every(r => r.url === '/api/proxy'));
  t('and hand back the upstream’s body and content type', (await viaCache.text()) === 'a,b\n1,2\n' && viaRate.headers.get('Content-Type') === 'text/csv');
  sent.length = 0;
  const csvTable = CM.toTable('a,b\n1,2\n', 'text/csv', { name: 'c', url: '' });
  t('toTable parses CSV through moke-data.js', csvTable.headers.join() === 'a,b' && csvTable.rows.length === 1);
  m = '';
  try { CM.toTable('<html>', 'text/html', { name: 'h' }); } catch (e) { m = e.message; }
  t('toTable refuses what is neither JSON nor CSV, naming it', /neither JSON nor CSV \(text\/html\)/.test(m));

  // ── Live refresh, when someone turns it on ────────────────────────────
  const events = [];
  document.addEventListener('moke:live-refresh', e => events.push(e.detail));
  CM.setSchedule('Towns', 15);
  t('setSchedule starts a timer for this page only', !!CM._timers.Towns && CM._schedules.Towns === 15);
  t('and does not persist it (the saved record is untouched)', JSON.parse(localStorage.getItem('moke_api_connections'))[0].schedule === 5);
  CM.stopScheduler();
  t('stopScheduler clears every timer', Object.keys(CM._timers).length === 0);
  answer(JSON.stringify([{ city: 'Devonport', n: 1 }]));
  await CM.refresh('Towns');
  t('a refresh is a fresh request through the proxy', sent.length === 1 && posted()[0].url === 'https://api.example.org/towns?state=TAS');
  t('and announces the table it fetched', events.length === 1 && events[0].table.rows.length === 1 && !events[0].error);
  sent.length = 0;
  refuse('host not on the proxy allowlist (MOKE_PROXY_ALLOW): api.example.org');
  await CM.refresh('Towns');
  t('a refused refresh announces the reason, not a table', events.length === 2 && /not on the proxy allowlist/.test(events[1].error) && !events[1].table);
  sent.length = 0;

  // ── The page's success path, with a canned envelope ───────────────────
  // What connections.tkt does with a 2xx envelope: toTable, then MokeActive.load.
  answer(JSON.stringify({ data: [{ suburb: 'Sandy Bay', count: 7 }, { suburb: 'Battery Point', count: 3 }] }));
  const env = await window.MokeProxy.request({ url: 'https://api.example.org/suburbs', method: 'GET' });
  const canned = CM.toTable(env.body, env.contentType, { name: 'Suburbs', url: 'https://api.example.org/suburbs' });
  await window.MokeActive.load(canned, 'PUBLIC');
  const loaded = JSON.parse(sessionStorage.getItem('moke_dataset'));
  t('a canned 2xx envelope loads as the active dataset, through MokeActive.load',
    loaded.name === 'Suburbs' && loaded.headers.join() === 'suburb,count' && loaded.rows[1][0] === 'Battery Point' && loaded.sensitivity === 'PUBLIC');

  console.log(`test-moke-connections: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.log('FAIL     threw: ' + (e && e.stack || e)); process.exit(1); });
