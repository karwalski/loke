# ooke Bindings Required by loke

> **Status: COMPLETE** — All 9 binding modules shipped by the ooke team (2026-04-19).
> 306/306 tests passing. All blocked loke stories are now unblocked. See implementation
> progress in `docs/epics-and-stories.md`.

This document describes the native ooke capabilities that loke needs but cannot implement
until ooke provides them. It is written for the **ooke and toke development teams** so they
understand the downstream requirements before designing each binding.

Each section covers one capability group: what loke needs, which loke stories are blocked,
the interface loke expects to call from toke, and any constraints or notes.

---

## Status summary

| Capability group | Priority | Blocked stories | Status |
|-----------------|----------|-----------------|--------|
| [Web view / app shell](#1-web-view--app-shell) | P1 | F1.2 | ✅ Done — std.webview (16/16 pass) |
| [OS keychain](#2-os-keychain) | P1 | F1.5 | ✅ Done — std.keychain (23/23 pass) |
| [In-process inference](#3-in-process-inference) | P1 | F2.4, F2.5 | ✅ Done — std.infer (32/32 pass) |
| [MLX backend](#4-mlx-backend-apple-silicon) | P2 | F2.3 | ✅ Done — std.mlx (35/35 pass) |
| [Disk-streaming inference](#5-disk-streaming-inference) | P2 | F2.9 | ✅ Done — std.infer streaming (34/34 pass) |
| [Vector store](#6-vector-store) | P2 | F4.4, F6.3 | ✅ Done — std.vecstore (63/63 pass) |
| [Secure ephemeral memory](#7-secure-ephemeral-memory) | P1 | F6.4 | ✅ Done — std.secure_mem (37/37 pass) |
| [mDNS / Bonjour](#8-mdns--bonjour) | P3 | F7.5, F8.1 | ✅ Done — std.mdns (29/29 pass) |
| [TLS primitives](#9-tls-primitives) | P3 | F8.2 | ✅ Done — std.tls (37/37 pass) |

Priority: P1 = blocks core security/privacy guarantees · P2 = blocks performance features · P3 = blocks companion/discovery features

---

## 1. Web view / app shell

**Blocked stories:** F1.2 (L) — **now unblocked**

**What loke needs:**
An ooke-hosted Chromium or WebKit web view that can be opened as a desktop window, load
a local ooke HTTP server as its URL, handle window lifecycle (open, close, minimise,
fullscreen), and pass system-level events (tray icon, native menus, deep links) into toke
handler functions.

This replaces Electron entirely. loke's browser mode is a single-page application already
written as ooke pages (`pages/index.tk`); it just needs a native window to host it.

**Expected toke interface:**
```
// ooke std.webview
pub f=open(url:str;title:str;width:i32;height:i32):$webview_handle
pub f=close(h:$webview_handle):bool
pub f=set_title(h:$webview_handle;title:str):bool
pub f=on_close(h:$webview_handle;cb:f():void):void
pub f=run_event_loop():void  // blocks until all windows closed
```

**Platform targets:** macOS first (WebKit), Windows planned (WebView2).

**Constraints:**
- Web view must be sandboxed — loke requires that web page JS cannot call arbitrary toke
  functions. Only explicitly registered message handlers are callable from the web view.
- Deep link handling needed: `loke://` scheme for CLI → browser handoff.

---

## 2. OS keychain

**Blocked stories:** F1.5 (L) — **now unblocked**

**What loke needs:**
Read and write named secrets to the OS-native credential store (macOS Keychain,
Windows Credential Manager) from toke. Used to store provider API keys (Anthropic,
OpenAI) and the SQLCipher database encryption key without ever writing them to disk in
plaintext.

**Expected toke interface:**
```
// ooke std.keychain
pub f=set(service:str;account:str;secret:str):bool
pub f=get(service:str;account:str):?(str)
pub f=delete(service:str;account:str):bool
pub f=exists(service:str;account:str):bool
```

**Constraints:**
- `service` = `"dev.loke"` by convention; `account` = key name e.g. `"anthropic_api_key"`.
- Must not log or expose the secret value at any level.
- Should fail gracefully (return `?(none)`) if the keychain is locked or unavailable rather
  than crashing — loke will fall back to prompting the user.
- Currently loke stores API keys via `storage.settings` (plaintext SQLite). Once keychain
  is available, `core.extensions` will migrate to it transparently.

---

## 3. In-process inference

**Blocked stories:** F2.4 (M), F2.5 (M) — **now unblocked**

**What loke needs:**
Run a small language model in-process — in the same native binary as loke — without
spawning a separate process or making a network call. This is the path to < 10ms intent
classification (F5.1) and to NER/embeddings that do not depend on Ollama being running.

**Expected toke interface:**
```
// ooke std.infer  (wraps llama.cpp or equivalent natively)
pub m.$model_handle{ id:str }
pub m.$infer_opts{ n_gpu_layers:i32; n_threads:i32; seed:i32 }

pub f=load(model_path:str;opts:$infer_opts):$model_handle
pub f=unload(h:$model_handle):bool
pub f=generate(h:$model_handle;prompt:str;max_tokens:i32):str
pub f=embed(h:$model_handle;text:str):@(f32)        // for embeddings
pub f=is_loaded(h:$model_handle):bool
```

**Constraints:**
- `model_path` will point to GGUF files in `~/.loke/models/`.
- loke needs to run a ≤ 3B model for intent/NER without loading it into the Ollama daemon.
- For embeddings (`embed`), the return type is a flat `@(f32)` vector — loke will handle
  cosine similarity itself.
- Thread safety: loke may call `generate` and `embed` concurrently from background agent
  threads; the binding must be safe to call from multiple toke coroutines simultaneously
  (or document that it is not and loke will serialise).

---

## 4. MLX backend (Apple Silicon)

**Blocked stories:** F2.3 (L) — **now unblocked**

**What loke needs:**
An optional inference path that delegates to Apple's MLX framework instead of llama.cpp
when running on Apple Silicon. MLX achieves 8–9% higher throughput on M-series hardware
by using unified memory more efficiently.

**Two acceptable approaches:**

Option A — ooke provides a native MLX binding:
```
// ooke std.mlx
pub f=load(model_path:str):$mlx_model
pub f=generate(m:$mlx_model;prompt:str;max_tokens:i32):str
pub f=is_available():bool  // false on non-Apple-Silicon or no MLX installed
```

Option B — ooke ships a local MLX REST bridge (same Ollama-compatible interface, different port).

**Constraints:**
- Must be no-op / gracefully absent on Intel Mac and Windows — `is_available()` returns false.
- MLX Python package may be a system prerequisite; loke will surface a setup prompt if unavailable.

---

## 5. Disk-streaming inference

**Blocked stories:** F2.9 (L) — **now unblocked**

**What loke needs:**
Run a 70B+ model that does not fit in RAM by streaming its layers from NVMe one at a time.
Background tier only; speed target is 0.5–5 tok/s.

**Expected toke interface:**
```
// ooke std.infer (extension of in-process inference binding)
pub m.$stream_opts{ ram_ceiling_gb:f32; prefetch_layers:i32; requires_nvme:bool }

pub f=load_streaming(model_dir:str;opts:$stream_opts):$model_handle
// generate() is the same as the in-process binding — streaming is transparent
```

**Constraints:**
- Must detect storage type (NVMe vs SATA/HDD) and warn if NVMe is unavailable.
- Must respect `ram_ceiling_gb` — never exceed it.
- Graceful degradation below 0.1 tok/s with cloud cost comparison surfaced to user.

---

## 6. Vector store

**Blocked stories:** F4.4 (L), F6.3 (M) — **now unblocked**

**What loke needs:**
An embedded vector store for semantic cache (prompt deduplication) and routing examples
(few-shot routing when RouteLLM is unavailable).

**Expected toke interface:**
```
// ooke std.vecstore
pub f=open(data_dir:str):$vec_store
pub f=collection(vs:$vec_store;name:str):$vec_collection
pub f=upsert(col:$vec_collection;id:str;embedding:@(f32);payload:str):bool
pub f=search(col:$vec_collection;query:@(f32);top_k:i32;min_score:f64):@($search_result)
pub f=delete(col:$vec_collection;id:str):bool
pub f=delete_before(col:$vec_collection;before_ts:i64):i32  // TTL sweep
```

**Constraints:**
- Embedded, no daemon, no network. Data in `~/.loke/data/vectors/`.
- Dimension-agnostic per collection (supports 384 or 768 depending on embedding model).

---

## 7. Secure ephemeral memory

**Blocked stories:** F6.4 (L) — **now unblocked**

**What loke needs:**
A memory region that is never written to disk (mlock'd), zeroed on deallocation, and
auto-expired after a configurable TTL. Used for PII placeholder maps in high-sensitivity
sessions.

**Expected toke interface:**
```
// ooke std.secure_mem
pub f=alloc(size_bytes:i32;ttl_seconds:i32):$secure_buf
pub f=write(buf:$secure_buf;data:str):bool
pub f=read(buf:$secure_buf):?(str)
pub f=wipe(buf:$secure_buf):bool
pub f=sweep():i32  // zero and free all expired buffers
```

**Constraints:**
- `mlock()` / `VirtualLock()` required — OS must not swap the region.
- `wipe()` must use compiler-barrier-safe zero (memset_s / SecureZeroMemory).
- `sweep()` called every 60s by background queue and on shutdown.

---

## 8. mDNS / Bonjour

**Blocked stories:** F7.5 (M), F8.1 (L) — **now unblocked**

**What loke needs:**
Advertise and discover loke companion devices and MCP servers on the local network
without manual configuration.

**Expected toke interface:**
```
// ooke std.mdns
pub f=advertise(svc:$service_record):bool
pub f=stop_advertise(name:str):bool
pub f=browse(service_type:str;cb:f($discovered):void):bool  // async callback
pub f=stop_browse(service_type:str):bool
pub f=resolve(name:str;service_type:str):?($discovered)
```

**Service types:** `_loke-mcp._tcp`, `_loke-companion._tcp`

**Constraints:**
- Browse must be async/callback-based. macOS: native Bonjour. Windows: mDNS stub.
- Discovered devices require explicit user approval before connection.

---

## 9. TLS primitives

**Blocked stories:** F8.2 (L) — **now unblocked**

**What loke needs:**
Mutual TLS 1.3 between loke host and companion device, with certificate pinning after
initial pairing.

**Expected toke interface:**
```
// ooke std.tls
pub f=listen_tls(port:i32;cfg:$tls_config;cb:f($tls_conn):void):bool
pub f=connect_tls(host:str;port:i32;cfg:$tls_config):?($tls_conn)
pub f=read(conn:$tls_conn):?(str)
pub f=write(conn:$tls_conn;data:str):bool
pub f=close(conn:$tls_conn):bool
pub f=gen_self_signed(common_name:str;valid_days:i32):$tls_keypair
```

**Constraints:**
- TLS 1.3 only. P-384 EC keys. Certificate pinning enforced when `peer_cert_pem` set.
- Pairing confirmation code derived from key fingerprints for out-of-band verification.

---

## Implementation order (completed 2026-04-19)

All 9 modules were implemented in a single batch per the priority ordering below.

| Order | Module | Tests | Completed |
|-------|--------|-------|-----------|
| 1 | std.keychain | 23/23 | 2026-04-19 |
| 2 | std.infer | 32/32 | 2026-04-19 |
| 3 | std.secure_mem | 37/37 | 2026-04-19 |
| 4 | std.webview | 16/16 | 2026-04-19 |
| 5 | std.vecstore | 63/63 | 2026-04-19 |
| 6 | std.mlx | 35/35 | 2026-04-19 |
| 7 | std.infer (streaming) | 34/34 | 2026-04-19 |
| 8 | std.mdns | 29/29 | 2026-04-19 |
| 9 | std.tls | 37/37 | 2026-04-19 |
| | **Total** | **306/306** | |
