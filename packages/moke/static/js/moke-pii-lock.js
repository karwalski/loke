/*
 * moke-pii-lock.js — which columns the schema panel marks with a lock (MK20.3b)
 *
 * WHY THIS EXISTS
 *
 * The lock in chat.tkt came from a column-name pattern (`_name$`, `phone`, ...) or
 * the first match of a value-detector cascade whose phone test,
 * /^[\+]?[\d\s\-\(\)]{7,18}$/, ran before any date test. Measured over the listed
 * datasets it was wrong both ways: every ISO date (`service_date`, `sale_date`,
 * `join_date`, ...) and numeric id or price (BITRE's `crash_id`, `sale_price`) was
 * locked as a phone number; `industry_name`, `line_name`, `app_name`,
 * `school_name`, `sensor_name` and `lender_name` were locked for their suffix; and
 * `patient_id` and `assignee`, which the manifest declares as PII, had no lock.
 *
 * The rule now:
 *
 *   1. A column the dataset DECLARES as PII (the manifest's `pii`, the same list
 *      chat.tkt names for redaction) is always locked. Nothing below can remove it,
 *      so the lock never covers less than the demo's redaction list.
 *   2. A heuristic may ADD locks: explicit identifier headers (email, phone, dob,
 *      medicare, ...), person identifiers (`patient_id`, `user_id`, ... but not
 *      every `*_id`), person-role headers whose values are names (`assignee`,
 *      `requested_by`), `*_name` columns whose values are person names, and values
 *      that are emails, formatted phone numbers or IP addresses.
 *
 * The lock is advisory UI. It is not the redaction list and it does not decide
 * anything: loke's privacy filter still judges every prompt.
 *
 * Run the tests: node packages/moke/static/js/tests/test-moke-pii-lock.js
 */
(function (root) {
  'use strict';

  // Headers that name personal information outright. Normalised: lower case, letters only.
  var PII_HEADERS = {
    email: 'email', emailaddress: 'email', contactemail: 'email',
    phone: 'phone', phonenumber: 'phone', mobile: 'phone', mobilenumber: 'phone', contactphone: 'phone',
    name: 'person_name', fullname: 'person_name', firstname: 'person_name', lastname: 'person_name',
    givenname: 'person_name', surname: 'person_name', familyname: 'person_name', middlename: 'person_name',
    username: 'person_name', contact: 'person_name', contactname: 'person_name',
    dob: 'dob', dateofbirth: 'dob', birthdate: 'dob',
    address: 'address', streetaddress: 'address', homeaddress: 'address',
    postcode: 'address', zipcode: 'address', zip: 'address',
    medicare: 'gov_id', medicarenumber: 'gov_id', ssn: 'gov_id', sin: 'gov_id', tfn: 'gov_id',
    taxfilenumber: 'gov_id', passport: 'gov_id', passportno: 'gov_id', passportnumber: 'gov_id',
    license: 'gov_id', licence: 'gov_id', driverlicense: 'gov_id', driverlicence: 'gov_id',
    abn: 'gov_id', acn: 'gov_id',
    bsb: 'financial', accountnumber: 'financial', creditcard: 'financial', cardnumber: 'financial',
    cardno: 'financial', cvv: 'financial',
    ipaddress: 'ip_address', ip: 'ip_address'
  };

  // The person a `<role>_id` or `<role>_name` column is about. Deliberately short:
  // `crash_id`, `order_id`, `server_id` and `provider_id` identify things or
  // organisations, and locking every `*_id` would make the lock meaningless.
  var PERSON_ROLES = {
    patient: 1, user: 1, customer: 1, client: 1, member: 1, employee: 1, staff: 1,
    student: 1, person: 1, citizen: 1, cardholder: 1, beneficiary: 1, applicant: 1,
    resident: 1, contact: 1, guardian: 1, parent: 1
  };

  // Headers whose values are people when they are names at all (`team_owner` holds
  // a team, so these lock only on their values).
  var PERSON_VALUED = /^(assignee|assigned_to|owner|reporter|requester|approver|author|[a-z]+_by)$/;

  function norm(h) { return String(h).toLowerCase().replace(/[^a-z]/g, ''); }

  // A reason the header alone gives, or null.
  function headerReason(h) {
    var lower = String(h).toLowerCase();
    var direct = PII_HEADERS[norm(h)];
    if (direct) return direct;
    if (/^pii_/.test(lower)) return 'declared_prefix';
    if (/(^|_)email$/.test(lower)) return 'email';
    if (/(^|_)(phone|mobile)(_|$)/.test(lower)) return 'phone';
    if (/(^|_)(dob|date_of_birth|birth_date)$/.test(lower)) return 'dob';
    if (/medicare|(^|_)(ssn|tfn)(_|$)|passport|card_no|card_number/.test(lower)) return 'gov_id';
    if (/(^|_)(home|street|residential|postal)_address$/.test(lower)) return 'address';
    var m = /^([a-z]+)_(id|name)$/.exec(lower);
    if (m && PERSON_ROLES[m[1]]) return m[2] === 'id' ? 'person_id' : 'person_name';
    return null;
  }

  // ── Value tests ────────────────────────────────────────────────────────────

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var IP_RE = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;

  // A phone number as people write one: a leading + or 0 or (area), or a
  // NNN-NNN-NNNN grouping, with 8 to 15 digits. Not a date, not a time, and not a
  // bare run of digits that does not start with 0 — that is an id, a count or a price.
  function isPhone(s) {
    var t = String(s).trim();
    if (!/^[\d\s\-\(\)\+\.]+$/.test(t)) return false;
    if (/^\d{4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,2}$/.test(t)) return false;
    if (/^\d{1,2}[\-\/\.]\d{1,2}[\-\/\.]\d{2,4}$/.test(t)) return false;
    var digits = t.replace(/\D/g, '');
    if (digits.length < 8 || digits.length > 15) return false;
    if (/^\+\d/.test(t)) return true;
    if (/^\(\d{1,4}\)/.test(t)) return true;
    if (/^0\d/.test(t)) return true;
    if (/^1[38]00[\s\-]?\d{3}[\s\-]?\d{3}$/.test(t)) return true;
    return /^\d{3}[\s\-\.]\d{3}[\s\-\.]\d{4}$/.test(t);
  }

  var TITLE = /^(Dr|Mr|Mrs|Ms|Miss|Mx|Prof|Sir|Dame)\.?\s+/;
  // One name word: Chen, Al-Hassan, O'Brien, McLeod, MacDonald.
  var WORD = "(?:[A-Z]')?(?:Ma?c)?[A-Z][a-z]+(?:['\\-][A-Z]?[a-z]+)*";
  // Two or three words, or a couple sharing a surname ("Linda and Peter Kowalski").
  var NAME_RE = new RegExp('^' + WORD + '(?:\\s(?:and|&)\\s' + WORD + ')?(?:\\s' + WORD + '){1,2}$');
  // Words that make a capitalised value an organisation, a place or a product
  // rather than a person. Measured against the datasets' `*_name` columns; common
  // surnames (Park, North, West, ...) are deliberately absent.
  var NOT_PERSON = /\b(Bank|Banking|School|College|University|Line|Ferry|Trains|Portal|Admin|Industry|Services|Group|Council|Hospital|Clinic|Centre|Center|Reservoir|River|Beach|Station|Network|Pty|Ltd|Inc|Corp|Company|Partners|Legal|Conveyancing|Conveyancers|Department|Agency|Authority|Insurance|Platform|Street|Road|Avenue|Intake|Outfall|Outlet|Monitor|Loop|Digital|Customer|Merchant)\b/;

  function isPersonName(s) {
    var t = String(s).trim().replace(TITLE, '');
    return NAME_RE.test(t) && !NOT_PERSON.test(t);
  }

  function share(strs, test) {
    if (!strs.length) return 0;
    var n = 0;
    for (var i = 0; i < strs.length; i++) if (test(strs[i])) n++;
    return n / strs.length;
  }

  // A reason the values give, or null. `strs` are the column's non-empty values.
  // Person names are judged over DISTINCT values, so one contact repeated on every
  // row counts once.
  function valueReason(h, strs) {
    if (!strs || !strs.length) return null;
    if (share(strs, function (s) { return EMAIL_RE.test(s); }) > 0.6) return 'email';
    if (share(strs, isPhone) > 0.6) return 'phone';
    if (share(strs, function (s) { return IP_RE.test(s); }) > 0.5) return 'ip_address';
    var lower = String(h).toLowerCase();
    if (/_name$/.test(lower) || PERSON_VALUED.test(lower)) {
      var distinct = Object.keys(strs.reduce(function (a, s) { a[s] = 1; return a; }, {}));
      if (share(distinct, isPersonName) > 0.6) return 'person_name';
    }
    return null;
  }

  function columnValues(rows, header, index) {
    var out = [];
    (rows || []).forEach(function (r) {
      if (r === null || r === undefined) return;
      var v = Array.isArray(r) ? r[index] : r[header];
      if (v !== null && v !== undefined && v !== '') out.push(String(v));
    });
    return out;
  }

  // { column: reason } for every locked column. Declared columns carry 'declared'
  // whatever else is true of them; the rest carry the heuristic's reason.
  function lock(headers, rows, declared) {
    var out = {};
    var decl = {};
    (declared || []).forEach(function (c) { decl[c] = true; });
    (headers || []).forEach(function (h, i) {
      if (decl[h]) { out[h] = 'declared'; return; }
      var r = headerReason(h) || valueReason(h, columnValues(rows, h, i));
      if (r) out[h] = r;
    });
    // A declared column the header row does not show is still the redaction list.
    Object.keys(decl).forEach(function (c) { out[c] = 'declared'; });
    return out;
  }

  var LABELS = {
    declared: 'Declared as personal information by the dataset; named for redaction',
    declared_prefix: 'Header marks it as personal information',
    email: 'Looks like email addresses', phone: 'Looks like phone numbers',
    person_name: 'Looks like the names of people', person_id: 'Identifies a person',
    dob: 'Date of birth', address: 'Address or postcode', gov_id: 'Government identifier',
    financial: 'Financial account detail', ip_address: 'Looks like IP addresses'
  };

  function label(reason) {
    var l = LABELS[reason] || 'Potential personal information';
    return reason === 'declared' ? l : l + ' (heuristic, advisory)';
  }

  var api = {
    lock: lock,
    headerReason: headerReason,
    valueReason: valueReason,
    isPhone: isPhone,
    isPersonName: isPersonName,
    label: label,
    NOTE: 'A lock marks a column to look at: every column the dataset declares as personal ' +
      'information, plus any a local heuristic suspects. It is advisory. loke’s privacy ' +
      'filter still checks every prompt.'
  };
  root.MokePiiLock = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof window !== 'undefined' ? window : globalThis));
