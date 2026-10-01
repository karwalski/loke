/*
 * test-moke-store.js — every dataset the UI lists loads from the one store (MK19.1).
 *
 * Run: node packages/moke/static/js/tests/test-moke-store.js
 *
 * moke had two dataset stores holding different tables under the same ids: a
 * 230KB object inline in templates/index.tkt, which the pages used, and
 * data/csv, which /api/datasets served. They were merged into static/data. This
 * test drives the REAL data layer (moke-data.js, with fetch answered from the
 * files on disk exactly as the server would serve them) for every dataset a page
 * offers, and checks what comes back against the manifest entry:
 *
 *   - the landing page's cards (loadDataset('<id>')), and the row and column
 *     counts each card prints;
 *   - the manifest entries the landing page's real-data grid and the upload
 *     page's built-in grid render (every entry not marked "listed": false);
 *   - every dataset a demo flow names (static/data/flows.json).
 *
 * The companion gate check, scripts/check_dataset_store.py, fails when a second
 * copy of any dataset appears anywhere else in the tree.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MOKE = path.resolve(__dirname, '../../..');
const STATIC = path.join(MOKE, 'static');

// fetch answers a /static/ path from the file on disk and refuses anything else,
// so a test that reached the network would fail rather than hang.
const served = [];
global.fetch = async (url) => {
  if (!/^\/static\//.test(url)) throw new Error('unexpected fetch ' + url);
  const file = path.join(STATIC, url.replace(/^\/static\//, ''));
  served.push(url);
  if (!fs.existsSync(file)) return { ok: false, status: 404 };
  const text = fs.readFileSync(file, 'utf8');
  return { ok: true, status: 200, text: async () => text, json: async () => JSON.parse(text) };
};
global.sessionStorage = {
  _v: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._v, k) ? this._v[k] : null; },
  setItem(k, v) { this._v[k] = String(v); },
  removeItem(k) { delete this._v[k]; }
};

require(path.join(STATIC, 'js/moke-data.js'));
const M = globalThis.MokeData;
const A = globalThis.MokeActive;

let pass = 0, fail = 0;
const t = (label, cond) => {
  if (cond) { pass++; } else { console.log('FAIL     ' + label); fail++; }
};

const manifest = JSON.parse(fs.readFileSync(path.join(STATIC, 'data/manifest.json'), 'utf8'));
const byId = {};
manifest.datasets.forEach(d => { byId[d.id] = d; });

const index = fs.readFileSync(path.join(MOKE, 'templates/index.tkt'), 'utf8');
const flows = JSON.parse(fs.readFileSync(path.join(STATIC, 'data/flows.json'), 'utf8'));

// ── What the UI lists ─────────────────────────────────────────────────────
const cards = {};
const cardRe = /<div class="ds-card">([\s\S]*?)loadDataset\('([^']+)'\)/g;
let m;
while ((m = cardRe.exec(index)) !== null) {
  const body = m[1];
  const rows = /<span>([\d,]+) rows<\/span>/.exec(body);
  const cols = /<span>(\d+) cols<\/span>/.exec(body);
  cards[m[2]] = {
    rows: rows ? Number(rows[1].replace(/,/g, '')) : null,
    cols: cols ? Number(cols[1]) : null
  };
}
const listedInManifest = manifest.datasets.filter(d => d.listed !== false).map(d => d.id);
const inFlows = [];
flows.flows.forEach(f => f.steps.forEach(s => { if (s.dataset) inFlows.push(s.dataset); }));

const uiIds = Array.from(new Set(Object.keys(cards).concat(listedInManifest, inFlows))).sort();
t('the landing page lists the fifteen synthetic datasets as cards', Object.keys(cards).length === 15);
t('the manifest lists sixteen datasets to the UI', listedInManifest.length === 16);
t('every flow dataset is listed', inFlows.every(id => listedInManifest.indexOf(id) >= 0));

// ── Each loads from the store with the shape its entry records ─────────────
function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

async function checkOne(id) {
  const d = byId[id];
  t(id + ': has a manifest entry', !!d);
  if (!d) return;
  t(id + ': the UI lists it (not "listed": false)', d.listed !== false);
  t(id + ': its file is in the store', /^\/static\/data\/(fixtures|snapshots)\/[^/]+\.csv$/.test(d.data.path));

  const file = path.join(STATIC, d.data.path.replace(/^\/static\//, ''));
  const want = d.data.sha256 || (d.provenance && d.provenance.snapshot_sha256);
  t(id + ': the file is the one the manifest hashed', !!want && sha256(file) === want);

  const parsed = await M.rows(id);
  t(id + ': loads ' + d.data.rowcount + ' rows (got ' + parsed.rows.length + ')', parsed.rows.length === d.data.rowcount);
  t(id + ': has ' + d.data.colcount + ' columns (got ' + parsed.headers.length + ')', parsed.headers.length === d.data.colcount);
  t(id + ': no ragged record', parsed.ragged.length === 0 && !parsed.rowcountMismatch);
  t(id + ': no empty or repeated column name',
    parsed.headers.every(h => h.length > 0) && new Set(parsed.headers).size === parsed.headers.length);
  t(id + ': every declared PII column exists', (d.pii || []).every(c => parsed.headers.indexOf(c) >= 0));
  t(id + ': every described column exists',
    Object.keys(d.descriptions || {}).every(c => parsed.headers.indexOf(c) >= 0));

  if (cards[id]) {
    t(id + ': its card says ' + cards[id].rows + ' rows; the store holds ' + d.data.rowcount,
      cards[id].rows === d.data.rowcount);
    t(id + ': its card says ' + cards[id].cols + ' cols; the store holds ' + d.data.colcount,
      cards[id].cols === d.data.colcount);
  }

  // What a Load button does: the active dataset carries the store's rows.
  sessionStorage.removeItem('moke_dataset');
  const ds = await A.load(id);
  const stored = JSON.parse(sessionStorage.getItem('moke_dataset'));
  t(id + ': Load makes it the active dataset with every row',
    stored.id === id && stored.rows.length === d.data.rowcount && stored.headers.length === d.data.colcount);
  t(id + ': and its first row is the file\'s first record',
    JSON.stringify(stored.rows[0]) === JSON.stringify(parsed.rows[0]) && ds.name === d.name);
}

(async () => {
  for (const id of uiIds) await checkOne(id);

  // A sensitivity override from the card's selector reaches the active dataset.
  await A.load('au.water', 'RESTRICTED');
  t('a sensitivity override is kept', JSON.parse(sessionStorage.getItem('moke_dataset')).sensitivity === 'RESTRICTED');

  // A file that disagrees with its entry is refused, not loaded quietly.
  M._resetCaches();
  const realFetch = global.fetch;
  global.fetch = async (url) => {
    const r = await realFetch(url);
    if (!/au\.opal\.csv$/.test(url)) return r;
    const text = (await r.text()).split('\n').slice(0, 5).join('\n') + '\n';
    return { ok: true, status: 200, text: async () => text };
  };
  let refused = false;
  try { await A.load('au.opal'); } catch (e) { refused = /manifest entry says 30/.test(e.message); }
  t('a truncated file is refused against its manifest row count', refused);
  global.fetch = realFetch;
  M._resetCaches();

  // The landing page no longer carries the data.
  t('index.tkt holds no inline dataset object', !/var DATASETS\s*=/.test(index));
  t('index.tkt is under 40KB (it was 236KB)', Buffer.byteLength(index) < 40000);

  console.log('test-moke-store: ' + uiIds.length + ' listed datasets, ' + pass + ' checks passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
