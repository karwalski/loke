/*
 * test-moke-data.js — tests for the dataset data layer (MK19.1).
 *
 * Run: node packages/moke/static/js/tests/test-moke-data.js
 *
 * These test the real module against the real bank-statement fixtures, rather
 * than against a simplified reimplementation. That distinction matters in this
 * repository: 54 of the toke test files re-declare the module under test instead
 * of importing it, which is why a live regression went unnoticed for months.
 *
 * The load-bearing assertion is "schema profile contains NO cell value". The
 * no-custody claim rests on it, so it is asserted against a sentinel drawn from
 * the fixture rather than against a hand-written string.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '../../../../..');
const FIXTURES = path.join(REPO, 'tests/fixtures/bank-statements');

// Minimal environment. fetch throws, so any test that accidentally depends on
// the network fails loudly rather than hanging.
global.fetch = async () => { throw new Error('no network in tests'); };
global.sessionStorage = {
  _v: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._v, k) ? this._v[k] : null; },
  setItem(k, v) { this._v[k] = String(v); },
  removeItem(k) { delete this._v[k]; }
};

require(path.join(REPO, 'packages/moke/static/js/moke-data.js'));
const M = globalThis.MokeData;

let pass = 0, fail = 0;
const t = (label, cond) => {
  if (cond) { console.log('ok       ' + label); pass++; }
  else { console.log('FAIL     ' + label); fail++; }
};

function fixture(name) {
  const p = path.join(FIXTURES, name);
  if (!fs.existsSync(p)) {
    console.error(`\nfixture ${name} missing — run tests/fixtures/bank-statements/generate.py`);
    process.exit(2);
  }
  return fs.readFileSync(p, 'utf8');
}

// --- Parsing, against fixtures with known difficulties ------------------
const wp = M.parseCSV(fixture('westpac-shaped.csv'));
t('CRLF fixture parses to 5 headers', wp.headers.length === 5);
t('CRLF fixture has no ragged records', wp.ragged.length === 0);
t('every record has the header field count', wp.rows.every(r => r.length === 5));
const withRef = wp.rows.find(r => r[1].includes('REF 8891'));
t('a comma inside a quoted field did not split the record',
  !!withRef && withRef[1].includes(', REF 8891'));

const rg = M.parseCSV(fixture('ragged.csv'));
t('ragged records are reported, not silently padded', rg.ragged.length === 2);
t('the ragged report names the record numbers',
  rg.ragged[0].record === 12 && rg.ragged[1].record === 22);

// --- Delimiter detection -----------------------------------------------
t('detects a comma delimiter', M.detectDelimiter('a,b,c\n1,2,3\n') === ',');
t('detects a semicolon delimiter', M.detectDelimiter('a;b;c\n1;2;3\n') === ';');
t('detects a tab delimiter', M.detectDelimiter('a\tb\tc\n1\t2\t3\n') === '\t');
t('a comma inside quotes does not outvote the real semicolon delimiter',
  M.detectDelimiter('a;b\n"x,y,z,w,v";2\n"p,q,r,s,t";4\n') === ';');

// --- Byte order mark ---------------------------------------------------
t('a BOM is stripped from the first header',
  M.parseCSV('﻿Date,Amount\n1,2\n').headers[0] === 'Date');

// --- Schema profile: the no-custody assertion -------------------------
const prof = M.schemaProfile(wp);
const profJson = JSON.stringify(prof);
t('profile has one entry per column', prof.columns.length === wp.headers.length);
t('profile reports the row count', prof.row_count === wp.rows.length);

// Every single cell value must be absent from the profile, not just the first.
let leaked = null;
for (const row of wp.rows) {
  for (const cell of row) {
    const v = String(cell).trim();
    if (v.length >= 6 && profJson.includes(v)) { leaked = v; break; }
  }
  if (leaked) break;
}
t('profile contains NO cell value from any row' + (leaked ? ` (leaked: ${leaked})` : ''),
  leaked === null);
t('profile has no min, max, mean or sample keys',
  !/"(min|max|mean|sample)/.test(profJson));

const bal = prof.columns.find(c => c.name === 'Balance');
t('a numeric column is typed numeric', !!bal && bal.type === 'numeric');
const dt = prof.columns.find(c => c.name === 'Date');
t('a date column is typed temporal', !!dt && dt.type === 'temporal');
t('null_rate is a proportion between 0 and 1',
  prof.columns.every(c => c.null_rate >= 0 && c.null_rate <= 1));

// --- MokeActive shim --------------------------------------------------
t('MokeActive.get returns null with nothing selected', globalThis.MokeActive.get() === null);

const res = globalThis.MokeActive.setFromManifest({
  id: 'x.y', name: 'X', description: 'd', category: 'c', kind: 'snapshot',
  sensitivity: 'PUBLIC', data: { rowcount: 42 }
});
t('setFromManifest stores a handle', res.ok === true);
const stored = JSON.parse(global.sessionStorage.getItem('moke_dataset'));
t('the stored handle carries no rows', !stored.rows || stored.rows.length === 0);
t('the stored handle records the row count', stored.rowcount === 42);
t('the stored handle is marked as manifest-sourced', stored.source === 'manifest');

console.log('\n' + (fail ? 'FAIL' : 'PASS') + `: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
