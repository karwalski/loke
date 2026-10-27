# Legacy `src/` modules: the F10.12-T4 table

Story F10.12, tranche T4. Measured 2026-10-27. Line and importer counts are from the tree after F10.12-T2; the error column is from `scripts/build_trees.sh src-legacy` run at the branch base (39f5e53e), and none of these files changed since. **This table records facts only. It makes no port, withdraw or keep decision about any module.** The decision is T4's second half and belongs to the maintainers.

Columns:

- **Lines**: physical lines in the file.
- **src importers**: how many other files under `src/` import the module.
- **Outside importers**: how many files under `packages/` or `tests/` import it. Every row is 0, which is the row's 2026-09-23 finding, still true once T1 removed the two exceptions.
- **Same leaf in packages/**: modules under `packages/` whose last name segment matches. A match is a candidate duplicate, not a confirmed one: `schema` matches three unrelated modules.
- **src-legacy errors**: compile errors attributed to the file by `scripts/build_trees.sh src-legacy` (check-only, toke 3.1.0).

T3 holds `companion/{mdns,remoteexec,sidecar}` and `core/discovery/mdns` pending the `std.mdns` re-survey. Two of those exist under `src/` and are marked T3: `companion/remote_exec.tk` and `core/discovery/mdns.tk`. There is no `src/companion/mdns.tk` or `src/companion/sidecar.tk`; the nearest file, `src/core/inference/sidecar.tk`, is listed unmarked because the row does not name it.

| File | Module | Lines | src importers | Outside importers | Same leaf in packages/ | src-legacy errors |
|---|---|---:|---:|---:|---|---:|
| `src/browser/shell.tk` | `loke.browser.shell` | 105 | 0 | 0 | browser.shell | 4 |
| `src/browser/window_manager.tk` | `loke.browser.windowmanager` | 69 | 0 | 0 | — | 4 |
| `src/browser/workspace/chat_panel.tk` | `loke.browser.workspace.chatpanel` | 177 | 0 | 0 | — | 1 |
| `src/browser/workspace/dashboard_persist.tk` | `loke.browser.workspace.dashboardpersist` | 157 | 0 | 0 | — | 2 |
| `src/browser/workspace/extractor.tk` | `loke.browser.workspace.extractor` | 168 | 0 | 0 | — | 15 |
| `src/browser/workspace/privacy_metadata.tk` | `loke.browser.workspace.privacymetadata` | 230 | 0 | 0 | — | 2 |
| `src/browser/workspace/tabs.tk` | `loke.browser.workspace.tabs` | 367 | 0 | 0 | page.api.tabs, page.tabs, browser.tabs | 6 |
| `src/cli/ask.tk` | `loke.cli.ask` | 120 | 0 | 0 | cli.ask | 7 |
| `src/cli/code_preprocess.tk` | `loke.cli.codepreprocess` | 244 | 0 | 0 | — | 14 |
| `src/cli/env.tk` | `loke.cli.env` | 167 | 0 | 0 | — | 12 |
| `src/cli/proxy.tk` | `loke.cli.proxy` | 98 | 0 | 0 | cli.proxy, mcpbroker.proxy, page.moke.api.proxy | 7 |
| `src/cli/sessions.tk` | `loke.cli.sessions` | 215 | 0 | 0 | — | 16 |
| `src/companion/channel.tk` | `loke.companion.channel` | 155 | 1 | 0 | core.companion.channel | 9 |
| `src/companion/discovery.tk` | `loke.companion.discovery` | 206 | 0 | 0 | core.companion.discovery, core.mcp.discovery | 11 |
| `src/companion/exo.tk` | `loke.companion.exo` | 197 | 0 | 0 | core.companion.exo | 30 |
| `src/companion/remote_exec.tk` (T3) | `loke.companion.remoteexec` | 125 | 0 | 0 | — | 1 |
| `src/core/audit/trail.tk` | `loke.core.audit.trail` | 189 | 0 | 0 | — | 16 |
| `src/core/cache/semantic.tk` | `loke.core.cache.semantic` | 178 | 0 | 0 | — | 7 |
| `src/core/config/keychain.tk` | `loke.core.config.keychain` | 95 | 0 | 0 | core.storage.keychain | 6 |
| `src/core/config/schema.tk` | `loke.core.config.schema` | 78 | 0 | 0 | core.memory.schema, core.policy.schema, page.moke.api.agents.schema | 23 |
| `src/core/discovery/mdns.tk` (T3) | `loke.core.discovery.mdns` | 159 | 0 | 0 | — | 8 |
| `src/core/hardware/profile.tk` | `loke.core.hardware.profile` | 86 | 2 | 0 | — | 21 |
| `src/core/hardware/recommender.tk` | `loke.core.hardware.recommender` | 285 | 0 | 0 | — | 1 |
| `src/core/health/api.tk` | `loke.core.health.api` | 24 | 0 | 0 | — | 0 |
| `src/core/health/checker.tk` | `loke.core.health.checker` | 138 | 1 | 0 | core.update.checker | 0 |
| `src/core/inference/mlx/backend.tk` | `loke.core.inference.mlx.backend` | 155 | 0 | 0 | — | 13 |
| `src/core/inference/native/engine.tk` | `loke.core.inference.native.engine` | 126 | 0 | 0 | moke.ml.engine | 6 |
| `src/core/inference/native/selector.tk` | `loke.core.inference.native.selector` | 73 | 0 | 0 | core.router.selector | 1 |
| `src/core/inference/ner/local.tk` | `loke.core.inference.ner.local` | 303 | 0 | 0 | — | 20 |
| `src/core/inference/sidecar.tk` | `loke.core.inference.sidecar` | 142 | 0 | 0 | — | 15 |
| `src/core/inference/streaming/disk.tk` | `loke.core.inference.streaming.disk` | 123 | 0 | 0 | — | 1 |
| `src/core/storage/ephemeral.tk` | `loke.core.storage.ephemeral` | 119 | 0 | 0 | core.storage.ephemeral | 6 |
| `src/core/storage/vector.tk` | `loke.core.storage.vector` | 142 | 0 | 0 | — | 5 |
| `src/governance/disclosure.tk` | `loke.governance.disclosure` | 91 | 0 | 0 | core.audit.disclosure | 0 |
| `src/governance/dsar.tk` | `loke.governance.dsar` | 162 | 0 | 0 | core.governance.dsar | 3 |
| `src/governance/explainability.tk` | `loke.governance.explainability` | 137 | 0 | 0 | — | 8 |
| `src/governance/incidents.tk` | `governance.incidents` | 101 | 0 | 0 | core.governance.incidents | 4 |
| `src/governance/justification.tk` | `governance.justification` | 89 | 0 | 0 | — | 2 |
| `src/governance/kill_switch.tk` | `governance.killswitch` | 113 | 0 | 0 | core.governance.killswitch | 10 |
| `src/governance/ownership.tk` | `governance.ownership` | 89 | 0 | 0 | — | 1 |
| `src/governance/tier_dashboard.tk` | `loke.governance.tierdashboard` | 236 | 0 | 0 | — | 19 |
| `src/governance/trace.tk` | `loke.governance.trace` | 163 | 0 | 0 | core.governance.trace | 6 |
| `src/mcp-broker/broker.tk` | `loke.mcpbroker.broker` | 211 | 1 | 0 | page.moke.api.mcp.broker | 1 |
| `src/mcp-broker/cli.tk` | `loke.mcpbroker.cli` | 75 | 0 | 0 | — | 2 |
| `src/mcp-broker/config.tk` | `loke.mcpbroker.config` | 119 | 2 | 0 | shared.config | 6 |
| `src/mcp-broker/registry.tk` | `loke.mcpbroker.registry` | 147 | 2 | 0 | core.agents.registry, core.models.registry, core.policy.presets.registry, mcpbroker.registry, moke.data.registry | 2 |
| `src/mcp-broker/transport.tk` | `loke.mcpbroker.transport` | 103 | 1 | 0 | core.providers.transport, mcptoke.transport | 10 |
| `src/memory/agent_diary.tk` | `loke.memory.agentdiary` | 179 | 0 | 0 | — | 3 |
| `src/memory/enrichment.tk` | `loke.memory.enrichment` | 102 | 0 | 0 | — | 5 |
| `src/memory/knowledge_graph.tk` | `loke.memory.knowledgegraph` | 177 | 0 | 0 | — | 5 |
| `src/memory/mining.tk` | `loke.memory.mining` | 224 | 0 | 0 | core.memory.mining | 12 |
| `src/platform/error/api_client.tk` | `loke.platform.error.apiclient` | 78 | 0 | 0 | — | 2 |
| `src/platform/error/client.tk` | `loke.platform.error.client` | 54 | 0 | 0 | core.mcp.client | 1 |
| `src/platform/error/server.tk` | `loke.platform.error.server` | 51 | 0 | 0 | browser.server, mcpbroker.server, mcptoke.server | 1 |
| `src/platform/http/middleware.tk` | `loke.platform.http.middleware` | 54 | 0 | 0 | — | 1 |
| `src/platform/http/response.tk` | `loke.platform.http.response` | 87 | 0 | 0 | — | 3 |
| `src/platform/http/router.tk` | `loke.platform.http.router` | 85 | 0 | 0 | core.router.router | 1 |
| `src/platform/http/security.tk` | `loke.platform.http.security` | 70 | 0 | 0 | — | 0 |
| `src/platform/http/server.tk` | `loke.platform.http.server` | 46 | 0 | 0 | browser.server, mcpbroker.server, mcptoke.server | 1 |
| `src/platform/integration/adapter.tk` | `loke.platform.integration.adapter` | 121 | 0 | 0 | — | 1 |
| `src/platform/integration/http_client.tk` | `loke.platform.integration.httpclient` | 96 | 0 | 0 | — | 0 |
| `src/platform/integration/oauth.tk` | `loke.platform.integration.oauth` | 120 | 0 | 0 | loke.core.auth.oauth | 2 |
| `src/platform/integration/sanitise.tk` | `loke.platform.integration.sanitise` | 80 | 0 | 0 | — | 3 |
| `src/platform/plugin/anonymisation.tk` | `loke.platform.plugin.anonymisation` | 97 | 0 | 0 | — | 1 |
| `src/platform/plugin/config.tk` | `loke.platform.plugin.config` | 65 | 0 | 0 | shared.config | 1 |
| `src/platform/plugin/contracts.tk` | `loke.platform.plugin.contracts` | 69 | 0 | 0 | — | 3 |
| `src/platform/plugin/lifecycle.tk` | `loke.platform.plugin.lifecycle` | 93 | 0 | 0 | — | 3 |
| `src/platform/plugin/registry.tk` | `loke.platform.plugin.registry` | 128 | 0 | 0 | core.agents.registry, core.models.registry, core.policy.presets.registry, mcpbroker.registry, moke.data.registry | 1 |
| `src/platform/testing/debug.tk` | `loke.platform.testing.debug` | 121 | 0 | 0 | — | 10 |
| `src/platform/testing/quality_gate.tk` | `loke.platform.testing.qualitygate` | 111 | 0 | 0 | — | 2 |
| `src/platform/testing/scaffold.tk` | `loke.platform.testing.scaffold` | 89 | 0 | 0 | — | 1 |
| `src/platform/testing/utilities.tk` | `loke.platform.testing.utilities` | 85 | 0 | 0 | — | 3 |
| `src/platform/testing/watch.tk` | `loke.platform.testing.watch` | 64 | 0 | 0 | — | 1 |
| `src/platform/ui/components.tk` | `loke.platform.ui.components` | 116 | 0 | 0 | — | 0 |
| `src/platform/ui/navigation.tk` | `loke.platform.ui.navigation` | 108 | 0 | 0 | — | 0 |
| `src/platform/ui/notifications.tk` | `loke.platform.ui.notifications` | 90 | 0 | 0 | browser.notifications | 2 |
| `src/platform/ui/reset.tk` | `loke.platform.ui.reset` | 29 | 0 | 0 | — | 0 |
| `src/platform/ui/router.tk` | `loke.platform.ui.router` | 169 | 0 | 0 | core.router.router | 0 |
| `src/platform/ui/settings_ui.tk` | `loke.platform.ui.settingsui` | 135 | 0 | 0 | — | 0 |
| `src/platform/ui/shell.tk` | `loke.platform.ui.shell` | 97 | 0 | 0 | browser.shell | 0 |
| `src/platform/ui/theme.tk` | `loke.platform.ui.theme` | 56 | 0 | 0 | — | 1 |
| `src/platform/ui/tokens.tk` | `loke.platform.ui.tokens` | 142 | 0 | 0 | — | 0 |

82 modules, 10539 lines, 434 src-legacy compile errors.
