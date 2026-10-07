#!/usr/bin/env node
// Copyright 2026 loke contributors
// SPDX-License-Identifier: Apache-2.0
//
// ui_check.mjs — open a page in headless Chrome and evaluate named checks in it.
//
//   node scripts/lib/ui_check.mjs <url> <checks.json>
//
// checks.json is [{"name": "...", "js": "<expression, may be async, returning true>"}],
// or {"reload": true} to reload the page, or {"key": "Tab"} to press a key for real,
// or {"name": "...", "navigates": "<expression>"} for an action that loads another page,
// or {"init": "<script>"} (BG1.4), run in every document the run loads, before the page's own
// scripts (Page.addScriptToEvaluateOnNewDocument); init items are installed before the first
// navigation, wherever they appear in the file.
// BG1.4: every request the browser sends is recorded from the DevTools Network domain, and
// before each `js` check window.__uiRequests holds them all so far, oldest first, as
// {url, method, type, page}: type is the DevTools resource type (Fetch, XHR, Document, ...)
// and page the document that sent it. A check can so judge where a page's requests went,
// including the ones made while it loaded, before any check ran.
// Each check runs in the live page after load. Anything other than `true` fails it. The
// DevTools protocol is driven directly over Node's built-in WebSocket, so there is no
// dependency to install. It exists because the GA3 UI rows had been Done for months
// without ever being run in a browser (RV1.4).

import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, checksPath] = process.argv.slice(2);
if (!url || !checksPath) { console.error('usage: ui_check.mjs <url> <checks.json>'); process.exit(2); }
const checks = JSON.parse(readFileSync(checksPath, 'utf8'));
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
// Port 0 lets Chrome pick a free port and write it to <profile>/DevToolsActivePort, so two
// runs (or a Chrome left behind by a killed one) can never share a debugging port. A fixed
// 9333 once let a stale headless Chrome answer for a new run. UI_CHECK_PORT still overrides.
const FIXED = process.env.UI_CHECK_PORT ? Number(process.env.UI_CHECK_PORT) : 0;
const profile = mkdtempSync(join(tmpdir(), 'ui_check_'));

const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${FIXED}`,
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', 'about:blank'], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// A gate stopped mid-run sends SIGTERM to this process; take Chrome down with it.
for (const sig of ['SIGTERM', 'SIGINT', 'SIGHUP']) {
  process.on(sig, () => {
    try { chrome.kill('SIGKILL'); } catch {}
    try { rmSync(profile, { recursive: true, force: true }); } catch {}
    process.exit(1);
  });
}
let exitCode = 1;
let PORT = FIXED;
try {
  let target;
  for (let i = 0; i < 80 && !target; i++) {
    try {
      if (!PORT) {
        const f = join(profile, 'DevToolsActivePort');
        if (!existsSync(f)) throw new Error('no port yet');
        PORT = Number(readFileSync(f, 'utf8').split('\n')[0]);
        if (!PORT) throw new Error('no port yet');
      }
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      target = list.find((t) => t.type === 'page');
    } catch { await sleep(250); }
  }
  if (!target) throw new Error('headless Chrome did not start');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let seq = 0; const pending = new Map(); const events = []; const requests = [];
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    else if (d.method) {
      events.push(d.method);
      if (d.method === 'Network.requestWillBeSent') {
        const q = d.params;
        requests.push({ url: q.request.url, method: q.request.method, type: q.type || '', page: q.documentURL || '' });
      }
    }
  };
  const send = (method, params = {}) => new Promise((res) => {
    const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params }));
  });

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  for (const c of checks) {
    if (c.init) await send('Page.addScriptToEvaluateOnNewDocument', { source: c.init });
  }
  await send('Page.navigate', { url });
  // X8.11: under heavy load the load event can take longer than the old 20 s wait, and the checks
  // then ran against a blank or half-loaded page and all failed at once. Wait up to 90 s for the
  // page this run asked for to be fully loaded, and stop with a clear error if it never is.
  const loaded = async () => {
    const r = await send('Runtime.evaluate', { expression:
      `document.readyState === 'complete' && location.href.startsWith(${JSON.stringify(url)})`,
      returnByValue: true });
    return r.result && r.result.result && r.result.result.value === true;
  };
  let ready = false;
  for (let i = 0; i < 360 && !ready; i++) {
    if (events.includes('Page.loadEventFired') && await loaded()) ready = true;
    else await sleep(250);
  }
  if (!ready) throw new Error(`page did not finish loading: ${url}`);
  await sleep(500);

  let failed = 0;
  for (const c of checks) {
    if (c.init) continue;
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
    if (c.navigates) {
      // A check whose action navigates the page (GA5.26: the chat opens /approve, which
      // returns to /chat). Awaiting it would die with the old document, so it is fired, and
      // it passes when the next page has loaded. The checks after it run on that page.
      events.length = 0;
      await send('Runtime.evaluate', { expression: c.navigates });
      for (let i = 0; i < 80 && !events.includes('Page.loadEventFired'); i++) await sleep(250);
      await sleep(500);
      if (events.includes('Page.loadEventFired')) console.log(`  ok   ${c.name}`);
      else { failed++; console.log(`  FAIL ${c.name} -> no page load followed`); }
      continue;
    }
    if (c.key) {
      // A real key press, through the browser's input pipeline, so focus moves as it does
      // for a keyboard user (programmatic .focus() does not trigger :focus-visible).
      for (const type of ['keyDown', 'keyUp']) {
        await send('Input.dispatchKeyEvent', { type, key: c.key, code: c.key,
          windowsVirtualKeyCode: c.key === 'Tab' ? 9 : 0 });
      }
      await sleep(100);
      continue;
    }
    await send('Runtime.evaluate', { expression: `window.__uiRequests = ${JSON.stringify(requests)}; true` });
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
