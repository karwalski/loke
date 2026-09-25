#!/usr/bin/env node
// Copyright 2026 loke contributors
// SPDX-License-Identifier: Apache-2.0
//
// ui_check.mjs — open a page in headless Chrome and evaluate named checks in it.
//
//   node scripts/lib/ui_check.mjs <url> <checks.json>
//
// checks.json is [{"name": "...", "js": "<expression, may be async, returning true>"}],
// or {"reload": true} to reload the page between checks.
// Each check runs in the live page after load. Anything other than `true` fails it. The
// DevTools protocol is driven directly over Node's built-in WebSocket, so there is no
// dependency to install. It exists because the GA3 UI rows had been Done for months
// without ever being run in a browser (RV1.4).

import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, checksPath] = process.argv.slice(2);
if (!url || !checksPath) { console.error('usage: ui_check.mjs <url> <checks.json>'); process.exit(2); }
const checks = JSON.parse(readFileSync(checksPath, 'utf8'));
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = Number(process.env.UI_CHECK_PORT || 9333);
const profile = mkdtempSync(join(tmpdir(), 'ui_check_'));

const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', 'about:blank'], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let exitCode = 1;
try {
  let target;
  for (let i = 0; i < 80 && !target; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      target = list.find((t) => t.type === 'page');
    } catch { await sleep(250); }
  }
  if (!target) throw new Error('headless Chrome did not start');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let seq = 0; const pending = new Map(); const events = [];
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    else if (d.method) events.push(d.method);
  };
  const send = (method, params = {}) => new Promise((res) => {
    const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params }));
  });

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Page.navigate', { url });
  for (let i = 0; i < 80 && !events.includes('Page.loadEventFired'); i++) await sleep(250);
  await sleep(500);

  let failed = 0;
  for (const c of checks) {
    if (c.reload) {
      // A check that changes state the page reads at load (sessionStorage) reloads it,
      // and the checks after it run against the reloaded page.
      events.length = 0;
      await send('Page.reload');
      for (let i = 0; i < 80 && !events.includes('Page.loadEventFired'); i++) await sleep(250);
      await sleep(500);
      console.log('  --   reloaded');
      continue;
    }
    const r = await send('Runtime.evaluate', {
      expression: `(async () => { return (${c.js}); })()`,
      awaitPromise: true, returnByValue: true,
    });
    const v = r.result && r.result.result ? r.result.result.value : undefined;
    const err = r.result && r.result.exceptionDetails ? r.result.exceptionDetails.exception?.description : '';
    if (v === true) console.log(`  ok   ${c.name}`);
    else { failed++; console.log(`  FAIL ${c.name} -> ${JSON.stringify(v)} ${err ? '(' + err.split('\n')[0] + ')' : ''}`); }
  }
  ws.close();
  exitCode = failed ? 1 : 0;
} catch (e) {
  console.error('ui_check:', e.message);
} finally {
  chrome.kill('SIGKILL');
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
process.exit(exitCode);
