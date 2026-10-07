/*
 * test-moke-pii-lock.js — the schema panel's PII lock (MK20.3b).
 *
 * Run: node packages/moke/static/js/tests/test-moke-pii-lock.js
 *
 * Imports the real module, the real manifest and the real CSVs (read through the
 * production parser in moke-data.js), not a restatement of either.
 *
 * What the old lock got wrong, measured over the listed datasets on 2026-10-08:
 *   - its phone test locked every ISO date column and BITRE's eight-digit crash_id
 *     (and au.property's sale_price);
 *   - its `_name$` rule locked industry_name, line_name, app_name, school_name,
 *     sensor_name and lender_name;
 *   - patient_id and assignee, both declared PII, had no lock.
 * The pinned sets below are what the new lock gives; a change to them is a change
 * to what the panel shows, and must be made here on purpose.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const L = require('../moke-pii-lock.js');
require('../moke-data.js');
const MD = globalThis.MokeData;

const STATIC = path.resolve(__dirname, '../..');
const MANIFEST = JSON.parse(fs.readFileSync(path.join(STATIC, 'data/manifest.json'), 'utf8'));

let failures = 0;
let checks = 0;
function ok(cond, msg) {
  checks++;
  if (!cond) { failures++; console.error('  FAIL: ' + msg); }
}

function load(m) {
  const file = path.join(STATIC, m.data.path.replace(/^\/static\//, ''));
  return MD.parseCSV(fs.readFileSync(file, 'utf8'));
}
function sorted(o) { return Object.keys(o).sort(); }

// ── The pinned lock for every listed dataset ──────────────────────────────
// Declared columns carry 'declared'; the rest are the heuristic's additions.
const EXPECTED = {
  'au.employment': {},
  'au.medicare': { patient_id: 'declared', patient_name: 'declared', dob: 'declared',
                   medicare_number: 'declared', provider_name: 'declared', postcode: 'address' },
  'au.opal': {},
  // property_address is not locked: it is not declared (MK20.3a item 3) and a
  // property's address is not a person's. That is MK20.3a's decision, not this story's.
  'au.property': { vendor_name: 'declared', purchaser_name: 'declared', postcode: 'address' },
  'au.schools': { principal_name: 'declared', postcode: 'address' },
  // au.water's declaration is MK20.3a's open decision and is left as it is.
  'au.water': { operator_name: 'declared', postcode: 'address' },
  'bitre.road_fatalities': {},
  'customer_intel': { pii_name: 'declared', pii_email: 'declared', pii_phone: 'declared',
                      customer_id: 'person_id' },
  'it_hardware.performance_metrics': {},
  'it_hardware.server_inventory': { contact_name: 'declared', contact_email: 'declared' },
  'it_ops.app_performance': {},
  'it_ops.asset_cost': {},
  // Undeclared staff names (MK20.3a item 2): the heuristic adds a lock from the values.
  'it_ops.change_management': { requested_by: 'person_name', approved_by: 'person_name' },
  'it_ops.incidents': { assignee: 'declared' },
  'it_platform.wc_orders': { user_id: 'person_id' },
  'it_platform.wc_users': { email: 'declared', full_name: 'declared', user_id: 'person_id' }
};

// Columns the old lock got wrong, by dataset. Each must NOT be locked.
const FALSE_POSITIVES = {
  'bitre.road_fatalities': ['crash_id'],
  'au.medicare': ['service_date', 'claim_date', 'processed_date', 'item_number', 'procedure_code'],
  'au.employment': ['industry_name'],
  'au.opal': ['line_name'],
  'au.property': ['sale_date', 'sale_price', 'settlement_date', 'lender_name', 'mortgage_amount'],
  'au.schools': ['school_name', 'school_id'],
  'au.water': ['sensor_name'],
  'customer_intel': ['acquisition_date'],
  'it_hardware.server_inventory': ['commissioned_date', 'warranty_expiry', 'os_patch_level', 'server_id'],
  'it_ops.app_performance': ['app_name'],
  'it_ops.asset_cost': ['purchase_date', 'support_expiry'],
  'it_ops.change_management': ['implement_date', 'change_id'],
  'it_ops.incidents': ['incident_id', 'server_id'],
  'it_platform.wc_orders': ['order_date', 'order_id'],
  'it_platform.wc_users': ['join_date', 'last_login']
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}/;
const listed = MANIFEST.datasets.filter(function (m) { return m.listed !== false; });

ok(listed.length === Object.keys(EXPECTED).length,
   'every listed dataset has a pinned lock (' + listed.length + ' listed, '
   + Object.keys(EXPECTED).length + ' pinned)');

listed.forEach(function (m) {
  const csv = load(m);
  const got = L.lock(csv.headers, csv.rows, m.pii || []);
  const want = EXPECTED[m.id];
  ok(!!want, 'listed dataset ' + m.id + ' has a pinned lock');
  if (!want) return;
  ok(JSON.stringify(sorted(got)) === JSON.stringify(sorted(want)),
     m.id + ' locks exactly the pinned columns (got ' + JSON.stringify(sorted(got))
     + ', expected ' + JSON.stringify(sorted(want)) + ')');
  Object.keys(want).forEach(function (c) {
    ok(got[c] === want[c], m.id + ': ' + c + ' is locked as ' + want[c] + ' (got ' + got[c] + ')');
  });
  (FALSE_POSITIVES[m.id] || []).forEach(function (c) {
    ok(csv.headers.indexOf(c) !== -1, m.id + ' still has ' + c + ' (the false positive is real)');
    ok(!got[c], m.id + ': ' + c + ' is not locked (got ' + got[c] + ')');
  });
  // No date column is ever read as a phone number, in any listed dataset.
  csv.headers.forEach(function (h, i) {
    const vals = csv.rows.map(function (r) { return r[i]; }).filter(function (v) { return v; });
    const dates = vals.filter(function (v) { return ISO_DATE.test(v); }).length;
    if (vals.length && dates / vals.length > 0.6) {
      ok(got[h] !== 'phone', m.id + ': date column ' + h + ' is not locked as a phone');
      ok(!got[h] || got[h] === 'declared' || got[h] === 'dob',
         m.id + ': date column ' + h + ' is locked only if declared or a date of birth (got ' + got[h] + ')');
    }
  });
});

// ── Declarations first: never lock less than the redaction list ───────────
// Over EVERY dataset in the manifest, listed or not: each declared column is locked,
// and locked as declared, whatever the heuristic thinks of it.
MANIFEST.datasets.forEach(function (m) {
  const csv = load(m);
  const got = L.lock(csv.headers, csv.rows, m.pii || []);
  (m.pii || []).forEach(function (c) {
    ok(got[c] === 'declared', m.id + ': declared PII column ' + c + ' is locked as declared (got ' + got[c] + ')');
  });
});

// A declared column the heuristic would never flag is still locked; so is one the
// header row does not show. The heuristic never removes a declaration.
(function () {
  const got = L.lock(['ref_code', 'amount'], [['A1', '3'], ['A2', '4']], ['ref_code', 'hidden_col']);
  ok(got.ref_code === 'declared', 'a declared column with no PII signal is locked (got ' + got.ref_code + ')');
  ok(got.hidden_col === 'declared', 'a declared column missing from the header is still locked');
  ok(!got.amount, 'an undeclared, unremarkable column is not locked');
  const none = L.lock(['ref_code'], [['A1']], []);
  ok(!none.ref_code, 'the same column undeclared is not locked — the declaration is what locked it');
}());

// ── Person identifiers, not every *_id ───────────────────────────────────
['patient_id', 'user_id', 'customer_id', 'employee_id', 'student_id', 'member_id'].forEach(function (h) {
  ok(L.headerReason(h) === 'person_id', h + ' identifies a person');
});
['crash_id', 'order_id', 'server_id', 'incident_id', 'change_id', 'school_id', 'provider_id',
 'claim_id', 'record_id', 'reading_id'].forEach(function (h) {
  ok(L.headerReason(h) === null, h + ' is not locked for its header alone');
});

// ── `_name` locks on the values, not the suffix ─────────────────────────
ok(L.valueReason('industry_name', ['Construction', 'Health Care and Social Assistance', 'Retail Trade']) === null,
   'industry names are not people');
ok(L.valueReason('school_name', ['Fairfield High School', 'Bourke Central School']) === null,
   'school names are not people');
ok(L.valueReason('lender_name', ['Commonwealth Bank', 'Macquarie Bank', 'Westpac']) === null,
   'lender names are not people');
ok(L.valueReason('vendor_name', ['Robert Chen', 'Linda and Peter Kowalski', "Fiona O'Brien"]) === 'person_name',
   'vendor names that are people lock on their values');
ok(L.valueReason('assignee', ['Sarah Chen', 'Marcus O\'Brien', 'Andrew McLeod']) === 'person_name',
   'an assignee holding names locks on its values');
ok(L.valueReason('team_owner', ['Platform', 'Data', 'Ops']) === null, 'a team is not a person');
ok(L.valueReason('principal_name', ['Dr Karen Bellingham', 'Mr Ahmed Saleh', 'Ms Patricia Doolan']) === 'person_name',
   'titled names are people');

// ── The phone test wants a phone's formatting ───────────────────────────
['+61 412 858 325', '(02) 9876 5432', '0412 345 678', '0412345678', '02 9876 5432',
 '1300 123 456', '555-123-4567'].forEach(function (s) {
  ok(L.isPhone(s), JSON.stringify(s) + ' is a phone number');
});
['2024-10-18', '2024/10/18', '18/10/2024', '20203158', '3250000', '142800', '5773-96082-4',
 '19:00', '1978-10-12', '2026-04-14T00:00:00', '12345678901'].forEach(function (s) {
  ok(!L.isPhone(s), JSON.stringify(s) + ' is not a phone number');
});

// ── The panel uses this module and says what the lock is ─────────────────
const CHAT = fs.readFileSync(path.resolve(STATIC, '../templates/chat.tkt'), 'utf8');
ok(CHAT.indexOf('<script src="/static/js/moke-pii-lock.js"></script>') !== -1, 'chat.tkt loads moke-pii-lock.js');
ok(/piiLock = MokePiiLock\.lock\(dataset\.headers, [^;]*dataset\.pii \|\| \[\]\)/.test(CHAT),
   'chat.tkt computes the lock from the dataset\'s declared PII');
ok(/var lockReason = piiLock\[col\];/.test(CHAT) && /lockReason \? '<span class="col-pii-lock"/.test(CHAT),
   'the schema panel\'s lock icon is the module\'s lock');
ok(CHAT.indexOf('{7,18}') === -1, 'chat.tkt no longer carries the old phone pattern');
ok(/MokePiiLock\.isPhone\(s\)/.test(CHAT), 'the type detector\'s phone test is the module\'s');
ok(/id="schema-lock-note"[^>]*>[^<]*advisory\. loke&#8217;s privacy filter still checks every prompt\./.test(CHAT),
   'the panel says the lock is advisory and that loke\'s filter still checks every prompt');

console.log(checks + ' checks, ' + failures + ' failed');
process.exit(failures ? 1 : 0);
