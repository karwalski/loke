# ooke Gaps Discovered by loke/moke

Filed for the toke project (ooke is built on toke). These block loke and moke API functionality.

---

**1. API GET handlers not wired**
`pages/api/*.tk` files define `pub f=get()` but ooke registers them as `POST echo` only. GET requests to `/api/*` return 404. All loke/moke API endpoints that serve data (health, models, settings, savings, tabs, pipeline history) are affected. The `get()` function exists and compiles but is never called by the ooke router.

**2. API POST handlers not wired**
`pages/api/*.tk` files define `pub f=post()` but ooke ignores them — POST requests just echo the request body back unchanged. All loke/moke API endpoints that process input (pipeline, datasets, upload, ML, feedback, agents, approve, privacy toggles) have handler logic that never executes. The server returns `{"text":"hello"}` instead of running the pipeline.

**3. Page handlers must use renderfile()**
If a page `get()` returns `http.res.json()` directly (without calling `tpl.renderfile()`), ooke doesn't register the route at all. This forces workarounds like creating single-line `.tkt` template files for JSON responses. Page handlers should be able to return any `http.$res` value.

**4. No CORS headers for localhost cross-port**
ooke serves no `Access-Control-Allow-Origin` headers. When moke (port 11432) makes a browser fetch to loke (port 11430), the browser blocks the response. Need configurable CORS for localhost origins, at minimum `Access-Control-Allow-Origin: http://localhost:*` and preflight `OPTIONS` handling.

**5. Page handler get() not called**
`pages/*.tk` files define `pub f=get()` but ooke never calls them. When a matching template exists in `templates/*.tkt`, ooke renders the template directly, bypassing the handler. The handler's return value (`http.res.json()`, template variables via `@("key":"val")`) is never used. This means page handlers cannot pass dynamic data to templates, check auth, query databases, or return JSON. The `{! var("key") !}` directive was added in v1.1.0 but has no effect since the handler that would populate it doesn't run.

**6. No API route namespace prefix**
API routes register as `/api/health` regardless of which ooke application defines them. When loke and moke both define `/api/health`, there's no way to namespace them (e.g. `/api/loke/health` vs `/api/moke/health`). The `[paths]` config in `ooke.toml` should allow an `api_prefix` setting.
