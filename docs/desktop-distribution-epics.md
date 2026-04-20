# Desktop Distribution — Epics & Stories

**Proposed addition to:** `docs/epics-and-stories.md`
**Layer:** Foundation (F1 extension) + Application (new epic A6)
**Status:** Draft — for team review
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## Background

loke must be distributable as a self-contained desktop application on macOS and Windows with no administrator or elevated privileges required at any point — install, run, update, or uninstall. This document defines the epics and stories required to achieve that, written to slot into the existing epic structure.

### What is packaged

Each distribution artifact bundles the full loke + toke stack:

| Component | Package | Included in Electron | Included in CLI binary |
|---|---|---|---|
| Foundation core (privacy, router, optimiser, storage, audit) | `packages/core` | Yes | Yes |
| toke MCP server (F7.4 — compress, decompress, template, analyse) | `packages/mcp-toke` | Yes | Yes |
| MCP broker (F7.3) | `packages/mcp-broker` | Yes | Yes |
| Platform HTTP server (P1) | `packages/core` | Yes | Yes (proxy mode) |
| Browser UI shell (P3) | `packages/browser` | Yes | No |
| CLI (`loke ask`, `loke proxy`) | `packages/cli` | No (separate artifact) | Yes |
| Shared types and utilities | `packages/shared` | Yes | Yes |

The toke MCP server (`packages/mcp-toke`) is a first-class component of every loke distribution — it is not optional. It provides the TOON serialisation, LLMLingua compression, and template capabilities (F7.4) that the Foundation layer relies on for token optimisation (F4).

---

## Impact on Existing Epics

Two existing stories require scope additions before A6 work can begin.

### F1.2 — Electron application shell (scope addition)

The existing story covers the Electron shell, IPC, window management, and multi-platform builds at a design level. The following is required in addition:

- **Per-user installer configuration** — electron-builder must be configured with `perMachine: false` so the Windows NSIS installer writes to `%LOCALAPPDATA%\Programs\loke\` with no UAC prompt. Mac target must produce a DMG with drag-to-Applications layout (no `.pkg` system installer).
- **Hardened runtime and entitlements** — macOS requires `hardenedRuntime: true` and a signed entitlements plist for notarization to succeed. Minimum entitlements: `com.apple.security.network.client`, `com.apple.security.files.user-selected.read-write`, `com.apple.security.cs.allow-jit`.
- **User-scoped data paths** — all persistent writes must use `app.getPath('userData')` (`~/Library/Application Support/loke/` on Mac, `%APPDATA%\loke\` on Windows). No writes to system directories at runtime.

### F1.4 — CI/CD pipeline (scope addition)

The existing story covers lint, type-check, test, build, and release. The following is required in addition:

- **Separate macOS and Windows runners** — Mac and Windows cannot cross-compile each other's signed builds. Two jobs are required: one on a `macos-14` runner (Apple Silicon) and one on `windows-latest`.
- **Certificate secret management** — signing certificates stored as base64-encoded P12 secrets in GitHub Actions. Mac requires `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `CSC_LINK`, `CSC_KEY_PASSWORD`. Windows requires `WIN_CSC_LINK`, `WIN_CSC_KEY_PASSWORD`.
- **Publish to GitHub Releases** — `electron-builder --publish always` uploads binaries and `latest.yml` / `latest-mac.yml` update manifests to the GitHub Release. This is the update server.

---

## New Epic: A6 — Desktop Distribution

*Package, sign, and distribute loke as a no-admin desktop application on macOS and Windows, with auto-update and a portable CLI binary.*

| Story | Size | Summary |
|-------|------|---------|
| A6.1 | M | electron-builder packaging config (DMG for Mac, per-user NSIS for Windows, universal binary, output paths, app metadata) |
| A6.2 | L | Code signing and notarization (Apple Developer ID + notarization pipeline, Windows EV certificate + timestamping, CI secret wiring) |
| A6.3 | L | Auto-update (electron-updater integration, startup version check, background download, user-prompted restart, stable and beta channels, force-update flag for security releases) |
| A6.4 | M | Portable CLI binary (Node.js SEA build target for `packages/cli`, single-file output for Mac and Windows, GitHub Release attachment) |
| A6.5 | M | Per-user proxy configuration (MCP environment variable injection into shell profile or tool config file without admin; system-wide proxy as optional elevated step) |
| A6.6 | S | Port conflict detection and resolution (detect if default localhost port is in use at startup, auto-select an available port, persist chosen port in settings, surface in first-run wizard) |

---

## Story Detail

### A6.1 — electron-builder packaging config
**Size:** M

Configure `packages/browser/package.json` with an `electron-builder` build section. Acceptance criteria:

- `pnpm build` in `packages/browser` produces a signed DMG (Mac) and NSIS installer (Windows) in `dist/`
- Mac target: `dmg` with `arm64` and `x64` arches (universal binary preferred; separate downloads acceptable for v1)
- Windows target: `nsis` with `x64` arch; `perMachine: false`; installs to `%LOCALAPPDATA%\Programs\loke\` with no UAC prompt
- App ID: `dev.tokelang.loke`
- Product name: `loke`
- All user data written via `app.getPath('userData')` — no system directory writes at runtime
- The toke MCP server (`packages/mcp-toke`) is spawned as a child process by the Electron main process at startup and terminated on graceful shutdown (F1.6)
- Uninstaller (Windows) removes only `%LOCALAPPDATA%\Programs\loke\` and Start Menu entry — no system-level cleanup

### A6.2 — Code signing and notarization
**Size:** L

Acceptance criteria:

- Mac: binary signed with Developer ID Application certificate; DMG notarized via Apple notary service; notarization ticket stapled to the DMG; Gatekeeper passes without user override on macOS 13+
- Windows: binary signed with EV code signing certificate using SHA-256 and an RFC 3161 timestamp; SmartScreen does not block launch for signed publisher
- Signing performed in CI only — developer builds may be unsigned
- Certificate private keys never leave secrets storage (GitHub Actions secrets or equivalent); no plaintext keys in the repository
- If signing credentials are absent (local dev), build succeeds with a warning, not a failure

### A6.3 — Auto-update
**Size:** L

Acceptance criteria:

- `electron-updater` checks for updates against `https://github.com/karwalski/loke/releases` on startup and every 6 hours
- Update check is non-blocking — app is fully usable while check runs
- When an update is available, user sees a non-intrusive notification (P3.8 notification system) with "Update and restart" and "Later" options
- Update is downloaded in the background; user is not prompted until download is complete
- On Mac: update is applied on next restart (standard Squirrel.Mac flow)
- On Windows: update re-runs the NSIS installer silently in user context — no admin prompt
- Two update channels: `stable` (default) and `beta` (opt-in via settings)
- A server-side `forceUpdate` flag in the release manifest triggers a mandatory update prompt for critical security releases — user cannot dismiss
- Update check respects the existing settings store (F6.7) for channel preference

### A6.4 — Portable CLI binary
**Size:** M

Acceptance criteria:

- `pnpm build:binary` in `packages/cli` produces a single self-contained executable for Mac (no-extension) and Windows (`.exe`) using Node.js Single Executable Application (SEA) or `caxa` as fallback
- Binary bundles `packages/cli`, `packages/core`, `packages/mcp-toke`, `packages/mcp-broker`, and `packages/shared` — the full toke stack without the browser UI
- Binary requires no Node.js installation on the host machine
- Binary is attached to GitHub Releases alongside the Electron installers
- On startup, binary checks `https://github.com/karwalski/loke/releases` for a newer version and prints a one-line notice to stderr if one is available — consistent with A5.3
- `loke update` command downloads the latest binary and replaces the current executable (Mac/Linux); on Windows, prints download URL with instruction (file locking prevents self-replace)
- Binary is not code-signed for v1 (acceptable for developer/CLI use); add signing in a follow-up story

### A6.5 — Per-user proxy configuration
**Size:** M

loke intercepts LLM traffic by acting as an HTTP proxy. This must work without admin rights. Acceptance criteria:

- First-run wizard (A4.1) includes a "Connect your tools" step that auto-configures supported tools without admin
- For MCP-compatible tools (Claude Code, Codex CLI, Gemini CLI): wizard writes `HTTPS_PROXY=http://127.0.0.1:<port>` to the tool's config file or user shell profile (`~/.zshrc`, `~/.bashrc`, `%USERPROFILE%\Documents\PowerShell\profile.ps1`) — these tools then route through the toke MCP broker (F7.3, `packages/mcp-broker`) and the full privacy pipeline
- For browsers: wizard detects installed browsers and provides a PAC file URL (`http://127.0.0.1:<port>/proxy.pac`) with browser-specific setup instructions — no system proxy change
- Per-user system proxy (WinInet on Windows via `HKCU` registry, network location proxy on Mac) is offered as an optional step with a clear explanation — no admin required for this level
- System-wide proxy (affects all users and applications) is presented as a separate optional step that explicitly requests admin/sudo elevation with a clear explanation of what will change
- Core loke functionality is never gated on system-wide proxy — it is always optional

### A6.6 — Port conflict detection and resolution
**Size:** S

Acceptance criteria:

- On startup, loke attempts to bind the configured localhost port (default: `11430`) for the Platform HTTP server (P1.1) and the toke MCP server (F7.4)
- If the port is in use, loke automatically selects the next available port in the range `11430–11440`
- The chosen port is persisted in the settings store (F6.7) so it is stable across restarts
- The active port is displayed in the first-run wizard, the about screen (P3.9), and the pipeline visibility panel (A4.2)
- `loke doctor` (A2.5) includes a port status check for both the Platform HTTP server and the toke MCP server

---

## Dependencies

| Story | Depends on |
|-------|------------|
| A6.1 | F1.2 (Electron shell) |
| A6.2 | A6.1 |
| A6.3 | A6.1, A6.2, F6.7 (settings store), P3.8 (notification system) |
| A6.4 | F1.4 (CI/CD pipeline) |
| A6.5 | A6.6 (stable port), A4.1 (first-run wizard), P1.1 (HTTP server) |
| A6.6 | P1.1 (HTTP server) |

---

## Open Questions

| # | Question |
|---|----------|
| 1 | Fixed or dynamic default port? A fixed well-known port (e.g. `11430`) simplifies MCP tool configuration. Dynamic ports eliminate conflicts but require the wizard to update tool configs on every change. |
| 2 | Windows EV certificate at current funding stage? EV clears SmartScreen immediately; OV requires reputation build-up. For a privacy product, EV is strongly preferred — but requires a hardware token or HSM. |
| 3 | Universal Mac binary (single download, arm64 + x64) or two separate downloads? Universal adds ~40MB to the DMG but reduces support complexity. |
| 4 | Mac App Store distribution required? Sandbox entitlements may conflict with proxy functionality. Separate story if yes. |
| 5 | Tray-only / headless mode? Some users may want background privacy filtering with no visible window. Out of scope for A6 but affects the Electron shell architecture in F1.2. |
