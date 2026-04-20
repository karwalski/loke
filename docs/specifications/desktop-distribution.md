# Desktop Distribution — Specification

**Epic:** A6 — Desktop Distribution
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

This document defines the requirements for packaging and distributing loke as a desktop application on macOS and Windows. loke is built on its own platform layer — the Foundation engine (privacy pipeline, LLM router, storage, MCP), the Platform HTTP server (P1), and the Electron application shell (F1.2) — and distribution must package and deliver all of these together as a single self-contained artifact.

The primary goals are:

- Zero admin/elevated privileges required to install or run
- Seamless out-of-box experience — the packaged binary includes everything; no separate runtime installs
- Auto-update capability suited to a security product (rapid patch delivery via the notification system, P3.8)
- Code-signed builds that satisfy platform Gatekeeper and SmartScreen requirements
- Support for both Browser mode (`packages/browser`, Electron GUI) and CLI mode (`packages/cli`) distributions

Two distribution approaches are evaluated: **Electron** (recommended, already specified in F1.2) and **Tauri** (lightweight alternative, requires architectural change). A third option — **portable CLI binary** — covers headless and developer proxy scenarios via `packages/cli`.

The epics and stories required to implement this specification are defined in `docs/desktop-distribution-epics.md` (Epic A6, plus scope additions to F1.2 and F1.4).

---

## 2. Constraints

| Constraint | Detail |
|---|---|
| No admin rights (Mac) | Must install to `~/Applications` or run directly — no `sudo`, no system-level writes at install time |
| No admin rights (Windows) | Must install to `%LOCALAPPDATA%` — no UAC elevation, no `HKLM` writes at install time |
| No separate runtime | The packaged artifact must be self-contained. The Foundation layer (F3–F7) runs inside Electron's Node.js process — no separate Node.js install required |
| User-scoped storage | All persistent data — SQLCipher database, audit trail, PII mappings, settings (F6.1, F6.2, F6.7) — must write to user-scoped paths only |
| System proxy optional | Setting a system-wide HTTP proxy requires admin on both platforms. The Platform HTTP server (P1.1) and proxy interception must function without system-wide proxy — see §7 |
| Privacy pipeline integrity | The packaged binary must be code-signed. Tampered builds must be detectable |
| Auto-update | Security fixes must be deliverable without user action beyond accepting a prompt. Notification delivered via P3.8 |

---

## 3. Option A — Electron (Recommended)

### 3.1 Summary

Electron bundles Chromium and Node.js into a self-contained application. It is the approach already specified in F1.2 (`packages/browser`). The entire Foundation layer (F3 privacy pipeline, F4 token optimiser, F5 LLM router, F6 storage, F7 MCP framework) and the Platform HTTP server (P1) run inside the Electron main process. The renderer process hosts the UI — vanilla TypeScript, no framework, as specified in P3.

### 3.2 Why Recommended

- Already the specified Browser mode shell (F1.2) — no architectural change required
- Foundation layer runs as-is inside Electron's bundled Node.js process — F3 through F7 require no modification
- The Platform HTTP server (P1.1) binds to `localhost` by default — no elevated ports, no admin
- Mature toolchain (`electron-builder`) with first-class Mac + Windows support
- Per-user install on Windows (no admin) is a single config flag
- `electron-updater` integrates with GitHub Releases and delivers notifications through the existing notification system (P3.8)

### 3.3 Downsides

- Large distribution size: ~180–220 MB (Chromium + Node.js bundled)
- Higher memory footprint than native alternatives

### 3.4 Toolchain

| Tool | Purpose |
|---|---|
| `electron-builder` | Package, sign, and publish Mac + Windows builds — extends F1.2 |
| `electron-updater` | In-app auto-update, integrates with GitHub Releases — implements A6.3 |
| GitHub Actions | CI/CD build pipeline on Mac and Windows runners — extends F1.4 |
| Apple Developer Program | Notarization required for seamless Gatekeeper pass — implements A6.2 |
| Windows EV code signing cert | Clears SmartScreen immediately — implements A6.2 |

### 3.5 macOS Configuration

```json
"mac": {
  "target": [
    { "target": "dmg", "arch": ["arm64", "x64"] }
  ],
  "category": "public.app-category.productivity",
  "hardenedRuntime": true,
  "gatekeeperAssess": false,
  "entitlements": "build/entitlements.mac.plist",
  "entitlementsInherit": "build/entitlements.mac.plist",
  "notarize": true
}
```

**Entitlements required** — the Foundation layer and P1 HTTP server need these entitlements under hardened runtime:

```xml
<!-- build/entitlements.mac.plist -->
<key>com.apple.security.cs.allow-jit</key><true/>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
<key>com.apple.security.network.client</key><true/>
<key>com.apple.security.files.user-selected.read-write</key><true/>
```

**Distribution format:** DMG with drag-to-Applications layout. Universal binary (arm64 + x64) is preferred — single download works on both Apple Silicon and Intel Mac. Open question: see §12.3.

**Install path:** `~/Applications/loke.app` (user-level, no admin). Electron apps can also run directly from anywhere.

**Gatekeeper:** Requires notarization via Apple's notary service in the CI pipeline (F1.4 extension). Without notarization, users must right-click → Open. With notarization, launch is seamless.

**Storage:** `app.getPath('userData')` resolves to `~/Library/Application Support/loke/` — the path used by F6.1 (SQLCipher database), F6.2 (audit trail), and F6.7 (settings store).

### 3.6 Windows Configuration

```json
"win": {
  "target": [
    { "target": "nsis", "arch": ["x64"] }
  ],
  "signingHashAlgorithms": ["sha256"],
  "certificateSubjectName": "loke"
},
"nsis": {
  "perMachine": false,
  "oneClick": true,
  "allowToChangeInstallationDirectory": false,
  "createDesktopShortcut": true,
  "createStartMenuShortcut": true,
  "runAfterFinish": true
}
```

**Install path:** `%LOCALAPPDATA%\Programs\loke\` — no UAC, no admin.

**Storage:** `app.getPath('userData')` resolves to `%APPDATA%\loke\` — the path used by F6.1, F6.2, and F6.7.

**SmartScreen:** A valid EV code signing certificate suppresses the SmartScreen warning immediately. An OV certificate suppresses it after reputation builds. For a security product, EV is strongly recommended — see §12.2 and §8.2.

**Uninstall:** NSIS-generated uninstaller runs in user context from `%LOCALAPPDATA%`. No admin required. Removes the application bundle and Start Menu entry only — user data in `%APPDATA%\loke\` is preserved unless the user explicitly requests it removed (first-run wizard, A4.1, should communicate this).

### 3.7 Auto-Update

`electron-updater` polls GitHub Releases on startup and every 6 hours. When an update is found:

1. Installer/delta is downloaded in the background
2. User is notified via the loke notification system (P3.8) with "Update and restart" and "Later" actions
3. Update is applied on next restart (Mac — Squirrel.Mac) or immediately via a background NSIS re-run (Windows — no admin prompt)

For a security product, the update interval must be short. A server-side `forceUpdate` flag in the release manifest triggers a mandatory prompt (the P3.8 notification is non-dismissable) for critical security releases such as a privacy pipeline bypass.

**Update channels:** `latest.yml` (stable) and `beta.yml` (opt-in beta). Channel preference is stored via the settings store (F6.7) and surfaced in the base settings UI (P3.9).

### 3.8 Build Pipeline

Two GitHub Actions runners are required — macOS and Windows cannot cross-compile each other's signed builds. This extends the existing CI pipeline (F1.4).

```yaml
# .github/workflows/release.yml (outline)
jobs:
  build-mac:
    runs-on: macos-14          # Apple Silicon runner for arm64
    steps:
      - pnpm build
      - electron-builder --mac --publish always
    env:
      APPLE_ID: ${{ secrets.APPLE_ID }}
      APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
      CSC_LINK: ${{ secrets.MAC_CERT_P12_BASE64 }}
      CSC_KEY_PASSWORD: ${{ secrets.MAC_CERT_PASSWORD }}

  build-win:
    runs-on: windows-latest
    steps:
      - pnpm build
      - electron-builder --win --publish always
    env:
      WIN_CSC_LINK: ${{ secrets.WIN_CERT_P12_BASE64 }}
      WIN_CSC_KEY_PASSWORD: ${{ secrets.WIN_CERT_PASSWORD }}
```

---

## 4. Option B — Tauri (Lightweight Alternative)

### 4.1 Summary

Tauri is a Rust-based desktop framework that uses the operating system's native WebView instead of bundling Chromium. The UI layer (P3 — vanilla HTML/CSS/TS) would be unchanged. The backend is Rust, which must wrap or replace the Node.js Foundation layer.

### 4.2 Why Consider It

- App bundle size: **10–15 MB** vs ~200 MB for Electron
- Lower memory footprint
- The P3 UI platform (vanilla JS/TS, no framework) requires no changes
- No admin rights — same per-user install model as Electron

### 4.3 Why Not Recommended (Yet)

| Issue | Detail |
|---|---|
| Foundation layer mismatch | F3 (privacy pipeline), F4 (token optimiser), F5 (router), F6 (SQLCipher storage), F7 (MCP framework) are all TypeScript/Node.js. Tauri's backend is Rust. Options: (a) run Node.js as a sidecar alongside Tauri — eliminates the size advantage; (b) rewrite Foundation in Rust — multi-year effort |
| WebView2 dependency (Windows) | Windows 10 before 20H2 (Oct 2020) may not have WebView2. Affects ~5–10% of the installed base in 2026. Tauri v2 can bundle a fixed WebView2 as a fallback, adding ~40 MB |
| P1 HTTP server boundary | The Platform HTTP server (P1) runs inside Electron's main process today. In a Tauri architecture, P1 would need to run inside the Node.js sidecar, with Tauri's Rust backend acting as a thin IPC bridge — additional design work required |
| Architectural disruption | F1.2 already specifies Electron as the browser mode shell. Switching to Tauri invalidates that specification and the work done to date |

### 4.4 Recommended Path If Tauri Is Pursued

If bundle size becomes a hard user-reported constraint after v1.0:

1. Keep the Foundation layer (F3–F7) and Platform layer (P1–P6) as TypeScript/Node.js, bundled as a Node.js sidecar using Node.js SEA
2. Tauri Rust backend manages the sidecar lifecycle (start, health check, restart on crash)
3. Tauri WebView renders the existing P3 UI unchanged, communicating with P1 via `localhost`
4. Net result: ~50–80 MB (Tauri shell + Node.js sidecar) vs ~200 MB (Electron)

This preserves the Foundation and Platform layers entirely but adds sidecar lifecycle complexity.

---

## 5. Option C — Portable CLI Binary

### 5.1 Summary

For headless and developer scenarios, `packages/cli` can be distributed as a single portable executable requiring no installation. This covers the terminal mode (A2) and the coding LLM proxy (`loke proxy claude-code`, A2.2) without the Electron overhead.

The Foundation layer (F3–F7) and the components of the Platform layer used by CLI mode are bundled into the binary. The Platform HTTP server (P1) is included for the proxy mode. The P3 UI platform and Electron-specific components (F1.2) are excluded.

### 5.2 Toolchain Options

| Tool | Output | Admin required | Size |
|---|---|---|---|
| Node.js SEA (v21+) | Native single binary | None | ~30–50 MB |
| `caxa` | Self-extracting binary | None | ~60–80 MB |
| `pkg` (Vercel) | `.exe` / no-ext binary | None | ~60–80 MB |

Node.js SEA is the preferred approach — it is the official Node.js mechanism from v21+ and produces the smallest output. The CLI bundle is produced by esbuild first (already part of F1.1 build tooling), then embedded into the Node.js binary via the SEA configuration.

### 5.3 Use Cases

- Headless server or VM deployment — Foundation + Platform without a GUI
- Developer `PATH` install: drop binary in `~/.local/bin` or `~/bin`
- CI/CD pipeline integration with privacy filtering
- `loke proxy claude-code` (A2.2) — transparent LLM proxy without launching the Electron app

### 5.4 No Admin Required

The binary runs from any user-writable path. No installer, no registry writes, no system directories. Storage paths (F6.1, F6.7) resolve to the same user-scoped locations as the Electron build.

### 5.5 Auto-Update

The portable binary does not use `electron-updater`. On startup it checks the GitHub Releases API (same endpoint used by electron-updater) and prints a single stderr notice if a newer version exists — consistent with the version check in A5.3.

`loke update` (an extension to A2.5 `loke doctor`) downloads the new binary and replaces the current executable on Mac and Linux. On Windows, file locking prevents self-replace; the command prints the download URL with instructions instead.

Homebrew tap (Mac) and Scoop bucket (Windows) are future distribution channels for developer contexts — see §12.3.

---

## 6. Comparison Matrix

| Criterion | Electron (A) | Tauri (B) | CLI Binary (C) |
|---|---|---|---|
| Admin rights required | No | No | No |
| Mac support | Yes | Yes | Yes |
| Windows support | Yes | Yes | Yes |
| GUI | Yes — P3 UI in Chromium | Yes — P3 UI in native WebView | No |
| Foundation layer (F3–F7) | Runs in Electron Node.js process | Requires Node.js sidecar | Bundled in binary |
| Platform HTTP server (P1) | Runs in Electron main process | Runs in Node.js sidecar | Included for proxy mode |
| Bundle size | ~200 MB | ~15 MB (no sidecar) / ~70 MB (with sidecar) | ~30–60 MB |
| Auto-update | electron-updater → P3.8 notification | Tauri updater | Startup notice / `loke update` |
| Architectural change from F1.2 | None | Significant | None |
| Code signing (Mac) | Required for notarization | Required for notarization | Not required for v1 |
| Code signing (Windows) | EV cert recommended | EV cert recommended | OV or unsigned acceptable for developers |
| Time to ship | Low | High | Low |
| Recommended for | Primary app distribution | Future if size is critical | Developer / headless / A2 use |

---

## 7. Proxy Interception Without Admin Rights

The Platform HTTP server (P1.1) binds to `localhost` — no admin required for ports above 1024. loke intercepts LLM traffic by acting as an HTTP proxy on this port. System-wide proxy configuration is never mandatory.

### 7.1 Approaches by Integration Type

| Integration | Mac (no admin) | Windows (no admin) |
|---|---|---|
| **MCP tools** (Claude Code, Codex CLI, Gemini CLI) — the primary A2.2 use case | Write `HTTPS_PROXY=http://127.0.0.1:<port>` to the tool's config file or shell profile (`~/.zshrc`, `~/.bashrc`) | Same — write to `%USERPROFILE%\Documents\PowerShell\profile.ps1` or tool config |
| **Browser extensions** | Extension sets proxy via `chrome.proxy` API — no system change | Same |
| **Per-user system proxy** | `networksetup` for a specific network location — user-scoped, no admin | `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` — no admin |
| **PAC file** | P1.1 serves `http://127.0.0.1:<port>/proxy.pac` — user points browser to it | Same |
| **System-wide proxy** | Requires `sudo networksetup -setwebproxy` | Requires `netsh winhttp` — **not achievable without admin** |

### 7.2 Design Requirement

The first-run wizard (A4.1) must include a "Connect your tools" step that auto-writes MCP environment variables to user shell profiles or tool config files — no admin. System-wide proxy is offered as a separate optional step with explicit admin elevation, a clear explanation of what will change, and a clear statement that core loke functionality does not require it.

Port auto-detection (A6.6 — see §10) must run before the wizard's proxy configuration step, so the injected `HTTPS_PROXY` value uses the confirmed active port.

---

## 8. Code Signing Requirements

### 8.1 macOS

| Requirement | Detail |
|---|---|
| Apple Developer Program membership | $99 USD/year — required for notarization |
| Developer ID Application certificate | Issued via developer.apple.com, stored as P12 in GitHub Actions secrets for F1.4 CI |
| Notarization | Submits signed binary to Apple's notary service; ticket stapled to DMG. Required for seamless Gatekeeper pass on macOS 13+ |
| Hardened runtime | Must be enabled for notarization — required entitlements listed in §3.5 |

### 8.2 Windows

| Requirement | Detail |
|---|---|
| OV code signing certificate | ~$200–300/year (DigiCert, Sectigo). Clears SmartScreen after reputation accumulates |
| EV code signing certificate | ~$300–500/year. Clears SmartScreen immediately. Stored on a hardware token or HSM. Strongly recommended for a security product — shipping a privacy tool with an untrusted binary is a trust contradiction |
| SHA-256 signing | Required — SHA-1 is deprecated |
| Timestamping | RFC 3161 timestamp authority required so signatures remain valid after certificate expiry |

---

## 9. Storage and File System

All persistent data — SQLCipher database (F6.1), audit trail (F6.2), PII placeholder mappings (F3.5), settings (F6.7), and vector store (F6.3) — must write to user-scoped paths. `app.getPath('userData')` in Electron resolves the correct path on each platform automatically.

| Platform | userData path |
|---|---|
| macOS | `~/Library/Application Support/loke/` |
| Windows | `%APPDATA%\loke\` |

No files are written outside these paths at runtime. Install-time writes are limited to the application bundle location under the user's home directory (`~/Applications/` on Mac, `%LOCALAPPDATA%\Programs\loke\` on Windows).

---

## 10. First-Run Experience

The first-run wizard (A4.1) must be extended to cover the distribution context. The following steps are required beyond those already specified in A4.1:

1. **Port confirmation** (A6.6) — detect the active localhost port before any other step that depends on it. Display the confirmed port so the user can note it for manual tool configuration if needed.
2. **Proxy configuration** (A6.5) — offer to auto-configure MCP tools by writing `HTTPS_PROXY` to shell profiles or tool config files (no admin). Offer per-user system proxy configuration. Offer system-wide proxy as a clearly-labelled optional step requiring admin elevation.
3. **Tamper detection** — verify the binary is signed and notarized; display a warning in the wizard and the about screen (P3.9) if it is not.
4. **WebView2 detection** (Windows, Tauri path only) — if WebView2 is absent, prompt to install it before proceeding. Not applicable to the Electron (recommended) path.

---

## 11. Implementation Order

This maps to the story ordering in `docs/desktop-distribution-epics.md` (Epic A6).

1. **F1.2 scope addition** — add hardened runtime, entitlements, and user-scoped data paths to the Electron shell
2. **A6.1** — electron-builder packaging config (DMG + per-user NSIS)
3. **F1.4 scope addition** — add macOS and Windows CI runners, certificate secret wiring, publish to GitHub Releases
4. **A6.2** — code signing and notarization
5. **A6.6** — port conflict detection (required before A6.5 and A4.1 proxy step)
6. **A6.3** — auto-update via electron-updater and P3.8 notification system
7. **A6.5** — per-user proxy configuration in first-run wizard (A4.1 extension)
8. **A6.4** — portable CLI binary (Node.js SEA build for `packages/cli`)
9. **Tauri evaluation** — revisit after v1.0 if bundle size becomes a user-reported friction point

---

## 12. Open Questions

| # | Question | Owner |
|---|---|---|
| 1 | **Fixed or dynamic localhost port?** A fixed well-known port (e.g. `11430`) simplifies MCP tool configuration and avoids the wizard needing to re-write configs when the port changes. A dynamic port eliminates conflicts but adds complexity. Recommendation: fixed default with auto-increment on conflict (A6.6), persisted in F6.7. | Architecture |
| 2 | **Windows EV certificate at current funding stage?** EV clears SmartScreen immediately and requires a hardware token; OV clears it after reputation builds. For a privacy product, EV is strongly preferred. | Ops |
| 3 | **Universal Mac binary or two separate downloads?** Universal binary (arm64 + x64) is a single DMG but adds ~40 MB. Separate downloads halve the file size but increase support complexity. | Product |
| 4 | **Mac App Store distribution?** App Store sandboxing constraints may conflict with the proxy functionality (P1, A2.2) and shell profile writes (A6.5). Requires separate evaluation if yes. | Product |
| 5 | **Headless / tray-only Electron mode?** Some users may want background privacy filtering (F3, A2.2) with no visible window. This affects the F1.2 Electron shell architecture and is out of scope for A6 but should be decided before F1.2 implementation is finalised. | Product |
| 6 | **Homebrew tap (Mac) and Scoop bucket (Windows)?** Package manager distribution for the CLI binary (A6.4) reduces friction for developer installs. Low effort, high value for the A2 terminal mode audience. | Product |
