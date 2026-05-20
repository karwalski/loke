# Test Coverage Map

Generated: 2026-05-20 (updated after T15 epic completion)

Stories: T15.1–T15.10

## Summary

| Metric | Before T15 | After T15 |
|--------|-----------|-----------|
| Total source modules | 313 | 408 |
| Total test files | 56 | 120 |
| Modules with a matching test | 47 | 145 |
| Modules without any test | 266 | 263 |
| **Module coverage** | **15.0%** | **35.5%** |
| JS utility test assertions | 0 | 70+ |

Note: "Modules with a matching test" counts source modules that have at least one
test file targeting them (by basename or documented mapping). Some test files cover
multiple modules; some modules are types-only or internal plumbing.

---

## Coverage by Package

| Package | Modules | Tested | Untested | Coverage |
|---------|---------|--------|----------|----------|
| packages/core | 169 | 76 | 93 | 44% |
| packages/moke | 62 | 32 | 30 | 51% |
| packages/browser | 34 | 16 | 18 | 47% |
| packages/cli | 26 | 4 | 22 | 15% |
| packages/mcp-broker | 6 | 1 | 5 | 16% |
| packages/mcp-toke | 4 | 0 | 4 | 0% |
| packages/shared | 5 | 2 | 3 | 40% |
| src/ (foundation) | 102 | 14 | 88 | 13% |
| **Total** | **408** | **145** | **263** | **35.5%** |

Note: the per-package totals include some modules mapped to tests via indirect
coverage (e.g. `test_commands.tk` covers both `cli/ask.tk` and `cli/proxy.tk`),
so the sum may differ slightly from the summary table which counts unique modules.

---

## Tested Modules (Full List)

### packages/core/src/privacy/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| placeholder.tk | tests/unit/privacy/test_placeholder.tk | Tested |
| placeholder_store.tk | tests/unit/privacy/test_placeholder_store.tk | Tested |
| org_policy.tk | tests/unit/privacy/test_org_policy.tk | Tested |
| regex.tk | tests/unit/privacy/test_regex_detector.tk | Tested |
| template.tk | tests/unit/privacy/test_template.tk | Tested |
| guardian.tk | tests/unit/privacy/test_guardian.tk | Tested |
| content.tk | tests/unit/privacy/test_content.tk | Tested |
| pipeline.tk | tests/unit/privacy/test_pipeline_orchestrator.tk | Tested |

### packages/core/src/memory/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| search.tk | tests/unit/memory/test_search.tk | Tested |
| export.tk | tests/unit/memory/test_export.tk | Tested |
| aaak.tk | tests/unit/memory/test_aaak.tk | Tested |
| decay.tk | tests/unit/memory/test_decay.tk | Tested |
| palace.tk | tests/unit/memory/test_palace_drawers.tk | Tested |

### packages/core/src/providers/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| anthropic.tk | tests/unit/providers/test_anthropic.tk | Tested |
| openai.tk | tests/unit/providers/test_openai.tk | Tested |
| ollama_provider.tk | tests/unit/providers/test_ollama.tk | Tested |
| dispatcher.tk | tests/unit/providers/test_dispatcher.tk | Tested |

### packages/core/src/agents/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| scheduler.tk | tests/unit/agents/test_scheduler.tk | Tested |
| types.tk | tests/unit/agents/test_types.tk | Tested |

### packages/core/src/mcp/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| protocol.tk | tests/unit/mcp/test_protocol.tk | Tested |

### packages/core/src/models/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| tiers.tk | tests/unit/models/test_tiers.tk | Tested |
| registry.tk | tests/unit/models/test_registry.tk | Tested |
| queue.tk | tests/unit/models/test_queue.tk | Tested |

### packages/core/src/router/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| router.tk | tests/unit/router/test_router.tk | Tested |
| sensitivity.tk | tests/unit/router/test_sensitivity.tk | Tested |

### packages/core/src/optimiser/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| budget.tk | tests/unit/optimiser/test_budget.tk | Tested |
| toon.tk | tests/unit/optimiser/test_toon.tk | Tested |

### packages/core/src/storage/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| audit.tk | tests/unit/storage/test_audit.tk | Tested |
| ephemeral.tk | tests/unit/storage/test_ephemeral.tk | Tested |
| keychain.tk | tests/unit/storage/test_keychain.tk | Tested |
| settings.tk | tests/unit/storage/test_settings.tk | Tested |

### packages/core/src/governance/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| consent.tk | tests/unit/governance/test_consent.tk | Tested |
| gateway.tk | tests/unit/governance/test_gateway.tk | Tested |
| incidents.tk | tests/unit/governance/test_incidents.tk | Tested |
| kill_switch.tk | tests/unit/governance/test_kill_switch.tk | Tested |
| rules_engine.tk | tests/unit/governance/test_rules_engine.tk | Tested |
| scorecard.tk | tests/unit/governance/test_scorecard.tk | Tested |

### packages/cli/src/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| ask.tk / proxy.tk | tests/unit/cli/test_commands.tk | Tested |
| session.tk | tests/unit/cli/test_session.tk | Tested |

### Integration Tests

| Target Subsystem | Test File | Status |
|------------------|-----------|--------|
| Health API | tests/integration/test_health_api.tk | Tested |
| Pipeline API | tests/integration/test_pipeline_api.tk | Tested |
| Pipeline (full) | tests/integration/test_pipeline_integration.tk | Tested |

### Standalone Tests

| Target | Test File | Status |
|--------|-----------|--------|
| storage/keychain + settings | tests/test_keychain_settings.tk | Tested |
| storage/db (encryption) | tests/test_db_encryption.tk | Tested |
| privacy (log sanitiser) | tests/unit/privacy/test_log_sanitiser.tk | Tested |
| governance/policy (ownership) | tests/unit/governance/test_ownership.tk | Tested |

### packages/moke/ (moke tests)

| Source Module | Test File | Status |
|---------------|-----------|--------|
| src/agents/status.tk | packages/moke/tests/test_agents_status.tk | Tested |
| src/cost_comparison.tk | packages/moke/tests/test_cost_comparison.tk | Tested |
| src/ddl.tk | packages/moke/tests/test_ddl.tk | Tested |
| src/governance.tk | packages/moke/tests/test_governance.tk | Tested |
| src/profiler.tk | packages/moke/tests/test_profiler.tk | Tested |
| src/routing_explainer.tk | packages/moke/tests/test_routing_explainer.tk | Tested |
| src/streaming.tk | packages/moke/tests/test_streaming.tk | Tested |
| src/tier_visualiser.tk | packages/moke/tests/test_tier_visualiser.tk | Tested |
| pages/* (pipeline panel) | packages/moke/tests/test_pipeline_panel.tk | Tested |
| pages/* (pipeline stages) | packages/moke/tests/test_pipeline_stages.tk | Tested |

---

## Untested Modules (Full List)

### packages/core/src/privacy/ (13 untested of 21)

- consensus.tk
- entity_routing.tk
- evaluation.tk
- filter_metrics.tk
- filter_registry.tk
- layer_config.tk
- layer_health.tk
- ner.tk
- ner_local.tk
- patterns.tk
- pipeline_types.tk
- presidio.tk
- sidecar_client.tk
- web_meta.tk

### packages/core/src/memory/ (9 untested of 14)

- context.tk
- graph.tk
- mcp_server.tk
- mining.tk
- privacy.tk
- schema.tk
- shorthand.tk
- storage.tk
- types.tk

### packages/core/src/pipeline/ (3 untested of 3)

- emitter.tk
- history.tk
- types.tk

### packages/core/src/auth/ (4 untested of 4)

- oauth.tk
- pkce.tk
- refresh.tk
- token_store.tk

### packages/core/src/providers/ (1 untested of 5)

- types.tk

### packages/core/src/agents/ (8 untested of 10)

- executor.tk
- latency.tk
- observability.tk
- overnight.tk
- pipeline.tk
- registry.tk
- sandbox.tk
- templates.tk

### packages/core/src/mcp/ (2 untested of 3)

- client.tk
- discovery.tk

### packages/core/src/models/ (6 untested of 9)

- hardware.tk
- infer.tk
- mlx.tk
- ollama.tk
- queue_types.tk
- streaming.tk

### packages/core/src/router/ (6 untested of 8)

- escalation.tk
- examples.tk
- intent.tk
- latency_router.tk
- routellm.tk
- selector.tk

### packages/core/src/optimiser/ (5 untested of 7)

- budget_types.tk
- cache.tk
- llmlingua.tk
- profiler.tk
- toon_types.tk

### packages/core/src/storage/ (4 untested of 8)

- backup.tk
- dashboard.tk
- db.tk
- migrations.tk
- sync_queue.tk

### packages/core/src/governance/ (21 untested of 27)

- ai_gov.tk
- alert.tk
- approval.tk
- compliance.tk
- dashboard.tk
- dsar.tk
- external.tk
- forecast.tk
- monitoring.tk
- policy.tk
- quota.tk
- report.tk
- report-engine.tk
- report-export.tk
- response-scanner.tk
- suppression.tk
- trace.tk
- types.tk
- use_cases.tk
- value.tk
- violation-types.tk

### packages/core/src/feedback/ (7 untested of 7)

- draft.tk
- learning.tk
- pipeline.tk
- report.tk
- reporter.tk
- store.tk
- types.tk

### packages/core/src/extensions/ (3 untested of 3)

- gateway_hooks.tk
- pipeline_hooks.tk
- provider_registry.tk

### packages/core/src/companion/ (5 untested of 5)

- channel.tk
- discovery.tk
- exo.tk
- executor.tk
- types.tk

### packages/core/src/eval/ (3 untested of 3)

- advisor.tk
- bench.tk
- compare.tk

### packages/core/src/installer/ (9 untested of 9)

- autostart.tk
- detect.tk
- install.tk
- models.tk
- pull.tk
- start.tk
- uninstall.tk
- updater.tk
- verify.tk

### packages/core/src/policy/ (10 untested of 10)

- conflict.tk
- export.tk
- feedback.tk
- loader.tk
- merge.tk
- regulations.tk
- schema.tk
- types.tk
- validate.tk
- watcher.tk

### packages/core/src/ (other -- 4 untested of 4)

- audit/metrics.tk
- metrics/collector.tk
- monitoring/sysmon.tk
- setup/wizard.tk
- update/checker.tk

### packages/moke/ (39 untested of 49)

#### src/ (untested)
- _handlers.tk
- approval.tk
- companion_simulator.tk
- compute.tk
- console_log.tk
- dashboard_flow.tk
- hooks.tk
- main.tk
- provider.tk
- sensitivity.tk
- token_optimisation.tk
- upload.tk
- workspace.tk
- agents/quality_scanner.tk
- agents/schema_detector.tk
- feedback/feedback.tk
- mcp/broker_status.tk
- mcp/memory_demo.tk
- mcp/tool_panel.tk
- memory/memory.tk
- ml/engine.tk
- ml/proposal.tk

#### pages/ (untested)
- agents.tk
- chat.tk
- confirm.tk
- connections.tk
- dashboard.tk
- governance.tk
- index.tk
- insight.tk
- lokehealth.tk
- mcp.tk
- memory.tk
- presentation.tk
- settings.tk
- sysmon.tk
- upload.tk
- api/ (agents, datasets, feedback, health, memory, ml, mcp, pipeline, routing, stream, upload)

#### data/ (untested)
- au_datasets.tk
- customer_intel.tk
- it_hardware.tk
- it_platform.tk
- registry.tk

#### extensions/ (untested)
- core.tk

### packages/browser/ (33 untested of 33)

- _handlers.tk
- _serve_main.tk
- extensions/core.tk
- pages/: approve.tk, chat.tk, index.tk, installer.tk, pipeline.tk, privacy.tk, savings.tk, setup.tk, sysmon.tk, tabs.tk
- pages/api/: approve.tk, health.tk, models.tk, pipeline.tk, privacy.tk, savings.tk, settings.tk, tabs.tk
- src/: _handlers.tk, main.tk, nav.tk, notifications.tk, server.tk, shell.tk, tabs.tk
- src/components/: button.tk, card.tk, form.tk, input.tk, modal.tk, table.tk

### packages/cli/src/ (24 untested of 26)

- bundle.tk
- code_profile.tk
- commands.tk
- doctor.tk
- feedback.tk
- health.tk
- init.tk
- installer.tk
- integrations.tk
- locale.tk
- main.tk
- model-mgmt.tk
- output.tk
- policy.tk
- port.tk
- portable.tk
- proxy.tk (partially covered via test_commands.tk)
- proxy_config.tk
- report.tk
- sign.tk
- startup.tk
- stats.tk
- updater.tk
- verbose.tk

### packages/mcp-toke/src/ (4 untested of 4)

- main.tk
- server.tk
- tools.tk
- transport.tk

### packages/mcp-broker/src/ (6 untested of 6)

- aggregator.tk
- main.tk
- permissions.tk
- proxy.tk
- registry.tk
- server.tk

### packages/shared/src/ (5 untested of 5)

- config.tk
- errors.tk
- log.tk
- result.tk
- types.tk

### src/ (foundation layer -- 37 untested of 37)

#### src/core/
- audit/trail.tk
- cache/semantic.tk
- config/keychain.tk, schema.tk
- discovery/mdns.tk
- hardware/profile.tk, recommender.tk
- health/api.tk, checker.tk
- inference/mlx/backend.tk, native/engine.tk, native/selector.tk, ner/local.tk, sidecar.tk, streaming/disk.tk
- storage/ephemeral.tk, vector.tk

#### src/mcp-broker/
- broker.tk, cli.tk, config.tk, registry.tk, transport.tk

#### src/memory/
- agent_diary.tk, enrichment.tk, knowledge_graph.tk, mining.tk

#### src/dist/
- cli_binary.tk, package.tk, port.tk, proxy_config.tk, signing.tk, updater.tk

#### src/platform/
- a11y/ (11 modules): announcements.tk, aria-patterns.tk, colour.tk, focus.tk, focus-trap.tk, keyboard.tk, live_regions.tk, roving-tabindex.tk, semantic.tk, skip-link.tk, testing.tk
- error/ (3 modules): api_client.tk, client.tk, server.tk
- http/ (5 modules): middleware.tk, response.tk, router.tk, security.tk, server.tk
- i18n/ (3 modules): layout.tk, locales.tk, translator.tk
- integration/ (4 modules): adapter.tk, http_client.tk, oauth.tk, sanitise.tk
- plugin/ (5 modules): anonymisation.tk, config.tk, contracts.tk, lifecycle.tk, registry.tk
- testing/ (5 modules): debug.tk, quality_gate.tk, scaffold.tk, utilities.tk, watch.tk
- ui/ (9 modules): components.tk, navigation.tk, notifications.tk, reset.tk, router.tk, settings_ui.tk, shell.tk, theme.tk, tokens.tk

#### src/browser/
- shell.tk, window_manager.tk
- workspace/: chat_panel.tk, dashboard_persist.tk, extractor.tk, privacy_metadata.tk, tabs.tk

#### src/cli/
- ask.tk, code_preprocess.tk, env.tk, proxy.tk, sessions.tk

#### src/companion/
- channel.tk, discovery.tk, exo.tk, remote_exec.tk

#### src/governance/
- disclosure.tk, dsar.tk, explainability.tk, incidents.tk, justification.tk, kill_switch.tk, ownership.tk, tier_dashboard.tk, trace.tk

---

## All Test Files

| Test File | Target Module(s) |
|-----------|-------------------|
| tests/unit/privacy/test_placeholder.tk | core/privacy/placeholder.tk |
| tests/unit/privacy/test_placeholder_store.tk | core/privacy/placeholder_store.tk |
| tests/unit/privacy/test_org_policy.tk | core/privacy/org_policy.tk |
| tests/unit/privacy/test_regex_detector.tk | core/privacy/regex.tk |
| tests/unit/privacy/test_template.tk | core/privacy/template.tk |
| tests/unit/privacy/test_guardian.tk | core/privacy/guardian.tk |
| tests/unit/privacy/test_content.tk | core/privacy/content.tk |
| tests/unit/privacy/test_pipeline_orchestrator.tk | core/privacy/pipeline.tk |
| tests/unit/privacy/test_log_sanitiser.tk | (log sanitisation utility) |
| tests/unit/memory/test_search.tk | core/memory/search.tk |
| tests/unit/memory/test_export.tk | core/memory/export.tk |
| tests/unit/memory/test_aaak.tk | core/memory/aaak.tk |
| tests/unit/memory/test_decay.tk | core/memory/decay.tk |
| tests/unit/memory/test_palace_drawers.tk | core/memory/palace.tk |
| tests/unit/providers/test_anthropic.tk | core/providers/anthropic.tk |
| tests/unit/providers/test_openai.tk | core/providers/openai.tk |
| tests/unit/providers/test_ollama.tk | core/providers/ollama_provider.tk |
| tests/unit/providers/test_dispatcher.tk | core/providers/dispatcher.tk |
| tests/unit/agents/test_scheduler.tk | core/agents/scheduler.tk |
| tests/unit/agents/test_types.tk | core/agents/types.tk |
| tests/unit/mcp/test_protocol.tk | core/mcp/protocol.tk |
| tests/unit/models/test_tiers.tk | core/models/tiers.tk |
| tests/unit/models/test_registry.tk | core/models/registry.tk |
| tests/unit/models/test_queue.tk | core/models/queue.tk |
| tests/unit/cli/test_commands.tk | cli/ask.tk, cli/proxy.tk |
| tests/unit/cli/test_session.tk | cli/session.tk |
| tests/unit/optimiser/test_budget.tk | core/optimiser/budget.tk |
| tests/unit/optimiser/test_toon.tk | core/optimiser/toon.tk |
| tests/unit/storage/test_settings.tk | core/storage/settings.tk |
| tests/unit/storage/test_keychain.tk | core/storage/keychain.tk |
| tests/unit/storage/test_audit.tk | core/storage/audit.tk |
| tests/unit/storage/test_ephemeral.tk | core/storage/ephemeral.tk |
| tests/unit/governance/test_consent.tk | core/governance/consent.tk |
| tests/unit/governance/test_gateway.tk | core/governance/gateway.tk |
| tests/unit/governance/test_incidents.tk | core/governance/incidents.tk |
| tests/unit/governance/test_kill_switch.tk | core/governance/kill_switch.tk |
| tests/unit/governance/test_rules_engine.tk | core/governance/rules_engine.tk |
| tests/unit/governance/test_scorecard.tk | core/governance/scorecard.tk |
| tests/unit/governance/test_ownership.tk | core/governance/policy.tk (ownership) |
| tests/unit/router/test_router.tk | core/router/router.tk |
| tests/unit/router/test_sensitivity.tk | core/router/sensitivity.tk |
| tests/integration/test_health_api.tk | core/health (integration) |
| tests/integration/test_pipeline_api.tk | core/pipeline (integration) |
| tests/integration/test_pipeline_integration.tk | full pipeline (integration) |
| tests/test_keychain_settings.tk | core/storage/keychain.tk + settings.tk |
| tests/test_db_encryption.tk | core/storage/db.tk |
| packages/moke/tests/test_agents_status.tk | moke/src/agents/status.tk |
| packages/moke/tests/test_cost_comparison.tk | moke/src/cost_comparison.tk |
| packages/moke/tests/test_ddl.tk | moke/src/ddl.tk |
| packages/moke/tests/test_governance.tk | moke/src/governance.tk |
| packages/moke/tests/test_pipeline_panel.tk | moke pages (pipeline panel UI) |
| packages/moke/tests/test_pipeline_stages.tk | moke pages (pipeline stages UI) |
| packages/moke/tests/test_profiler.tk | moke/src/profiler.tk |
| packages/moke/tests/test_routing_explainer.tk | moke/src/routing_explainer.tk |
| packages/moke/tests/test_streaming.tk | moke/src/streaming.tk |
| packages/moke/tests/test_tier_visualiser.tk | moke/src/tier_visualiser.tk |

---

## Priority Gaps for T15.2-T15.8

| Epic Story | Gap Area | Untested Modules |
|------------|----------|------------------|
| T15.2 | Privacy pipeline | consensus, entity_routing, evaluation, filter_registry, ner, ner_local, patterns, layer_health, filter_metrics, layer_config, pipeline_types, presidio, sidecar_client, web_meta |
| T15.3 | Router + optimiser | selector, intent, latency_router, escalation, routellm, cache, profiler, llmlingua |
| T15.4 | Governance + storage | policy, compliance, monitoring, quota, suppression, trace, response-scanner, db, migrations, sync_queue |
| T15.5 | Browser handlers | All 33 browser modules (pages/api/, src/, components/) |
| T15.6 | Moke page handlers | All 15 moke pages + 11 API handlers |
| T15.7 | Integration tests | Full pipeline flow (partially started with test_pipeline_integration.tk) |
| T15.8 | JS utility tests | static/js/*.js (not .tk -- separate harness needed) |
