# Test Coverage Map

Generated: 2026-05-20

Story: X4b.18

## Summary
- Source modules: 182
- Test files: 52
- Modules with tests: 42 (23%)
- Modules without tests: 140

## Coverage by Subsystem

### Privacy (packages/core/src/privacy/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.privacy.regex | tests/unit/privacy/test_regex_detector.tk | 14 |
| core.privacy.guardian | tests/unit/privacy/test_guardian.tk | 13 |
| core.privacy.content | tests/unit/privacy/test_content.tk | 12 |
| core.privacy.org_policy | tests/unit/privacy/test_org_policy.tk | 13 |
| core.privacy.pipeline | tests/unit/privacy/test_pipeline_orchestrator.tk | 15 |
| core.privacy.placeholder_store | tests/unit/privacy/test_placeholder_store.tk | 13 |
| core.privacy.placeholder | tests/unit/privacy/test_placeholder.tk | 14 |
| core.privacy.template | tests/unit/privacy/test_template.tk | 12 |

### Governance (packages/core/src/governance/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.governance.consent | tests/unit/governance/test_consent.tk | 14 |
| core.governance.gateway | tests/unit/governance/test_gateway.tk | 14 |
| core.governance.incidents | tests/unit/governance/test_incidents.tk | 12 |
| core.governance.kill_switch | tests/unit/governance/test_kill_switch.tk | 11 |
| core.governance.policy (ownership) | tests/unit/governance/test_ownership.tk | 12 |
| core.governance.rules_engine | tests/unit/governance/test_rules_engine.tk | 26 |
| core.governance.scorecard | tests/unit/governance/test_scorecard.tk | 16 |

### Memory (packages/core/src/memory/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.memory.aaak | tests/unit/memory/test_aaak.tk | 12 |
| core.memory.decay | tests/unit/memory/test_decay.tk | 14 |
| core.memory.export | tests/unit/memory/test_export.tk | 15 |
| core.memory.palace | tests/unit/memory/test_palace_drawers.tk | 12 |
| core.memory.search | tests/unit/memory/test_search.tk | 10 |

### Models & Router (packages/core/src/models/, packages/core/src/router/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.models.queue | tests/unit/models/test_queue.tk | 5 |
| core.models.registry | tests/unit/models/test_registry.tk | 18 |
| core.models.tiers | tests/unit/models/test_tiers.tk | 13 |
| core.router.router | tests/unit/router/test_router.tk | 15 |
| core.router.sensitivity | tests/unit/router/test_sensitivity.tk | 19 |

### Storage (packages/core/src/storage/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.storage.audit | tests/unit/storage/test_audit.tk | 14 |
| core.storage.ephemeral | tests/unit/storage/test_ephemeral.tk | 7 |
| core.storage.keychain | tests/unit/storage/test_keychain.tk | 14 |
| core.storage.settings | tests/unit/storage/test_settings.tk | 6 |

### Providers (packages/core/src/providers/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.providers.anthropic | tests/unit/providers/test_anthropic.tk | 12 |
| core.providers.dispatcher | tests/unit/providers/test_dispatcher.tk | 12 |
| core.providers.ollama_provider | tests/unit/providers/test_ollama.tk | 13 |
| core.providers.openai | tests/unit/providers/test_openai.tk | 12 |

### Agents & MCP (packages/core/src/agents/, packages/core/src/mcp/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.agents.scheduler | tests/unit/agents/test_scheduler.tk | 13 |
| core.agents.types | tests/unit/agents/test_types.tk | 12 |
| core.mcp.protocol | tests/unit/mcp/test_protocol.tk | 13 |

### CLI (src/cli/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| cli.ask / cli.proxy | tests/unit/cli/test_commands.tk | 12 |
| cli.sessions | tests/unit/cli/test_session.tk | 11 |

### Optimiser (packages/core/src/optimiser/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| core.optimiser.budget | tests/unit/optimiser/test_budget.tk | 16 |
| core.optimiser.toon | tests/unit/optimiser/test_toon.tk | 12 |

### Integration Tests
| Endpoint / Subsystem | Test File(s) | Assertions |
|---|---|---|
| Health API (core.health) | tests/integration/test_health_api.tk | 10 |
| Pipeline API (core.pipeline) | tests/integration/test_pipeline_api.tk | 12 |

### moke (packages/moke/)
| Source Module | Test File(s) | Assertions |
|---|---|---|
| moke.agents.status | packages/moke/tests/test_agents_status.tk | 10 |
| moke.cost_comparison | packages/moke/tests/test_cost_comparison.tk | 15 |
| moke.ddl | packages/moke/tests/test_ddl.tk | 15 |
| moke.governance | packages/moke/tests/test_governance.tk | 14 |
| moke.pipeline_panel (ui) | packages/moke/tests/test_pipeline_panel.tk | 14 |
| moke.pipeline_stages (ui) | packages/moke/tests/test_pipeline_stages.tk | 16 |
| moke.profiler | packages/moke/tests/test_profiler.tk | 15 |
| moke.routing_explainer | packages/moke/tests/test_routing_explainer.tk | 12 |
| moke.streaming | packages/moke/tests/test_streaming.tk | 12 |
| moke.tier_visualiser | packages/moke/tests/test_tier_visualiser.tk | 11 |

Note: moke tests with 0 `t.assert(` calls use pass/fail counter style; assertion counts above reflect `pass=pass+1` occurrences.

## Untested Modules

### High Priority (core pipeline)
| Module | Path |
|---|---|
| core.privacy.consensus | packages/core/src/privacy/consensus.tk |
| core.privacy.entity_routing | packages/core/src/privacy/entity_routing.tk |
| core.privacy.evaluation | packages/core/src/privacy/evaluation.tk |
| core.privacy.filter_registry | packages/core/src/privacy/filter_registry.tk |
| core.privacy.ner | packages/core/src/privacy/ner.tk |
| core.privacy.ner_local | packages/core/src/privacy/ner_local.tk |
| core.privacy.pipeline_types | packages/core/src/privacy/pipeline_types.tk |
| core.privacy.patterns | packages/core/src/privacy/patterns.tk |
| core.privacy.layer_config | packages/core/src/privacy/layer_config.tk |
| core.privacy.layer_health | packages/core/src/privacy/layer_health.tk |
| core.pipeline.emitter | packages/core/src/pipeline/emitter.tk |
| core.pipeline.history | packages/core/src/pipeline/history.tk |
| core.pipeline.types | packages/core/src/pipeline/types.tk |
| core.router.escalation | packages/core/src/router/escalation.tk |
| core.router.selector | packages/core/src/router/selector.tk |
| core.router.latency_router | packages/core/src/router/latency_router.tk |
| core.router.intent | packages/core/src/router/intent.tk |
| core.models.streaming | packages/core/src/models/streaming.tk |
| core.models.queue_types | packages/core/src/models/queue_types.tk |
| core.providers.types | packages/core/src/providers/types.tk |
| core.governance.policy | packages/core/src/governance/policy.tk |
| core.governance.compliance | packages/core/src/governance/compliance.tk |
| core.governance.monitoring | packages/core/src/governance/monitoring.tk |
| core.governance.quota | packages/core/src/governance/quota.tk |
| core.governance.suppression | packages/core/src/governance/suppression.tk |
| core.governance.trace | packages/core/src/governance/trace.tk |
| core.governance.response-scanner | packages/core/src/governance/response-scanner.tk |
| core.storage.db | packages/core/src/storage/db.tk |
| core.storage.migrations | packages/core/src/storage/migrations.tk |
| core.storage.sync_queue | packages/core/src/storage/sync_queue.tk |

### Medium Priority (features)
| Module | Path |
|---|---|
| core.privacy.presidio | packages/core/src/privacy/presidio.tk |
| core.privacy.sidecar_client | packages/core/src/privacy/sidecar_client.tk |
| core.privacy.web_meta | packages/core/src/privacy/web_meta.tk |
| core.privacy.filter_metrics | packages/core/src/privacy/filter_metrics.tk |
| core.governance.ai_gov | packages/core/src/governance/ai_gov.tk |
| core.governance.alert | packages/core/src/governance/alert.tk |
| core.governance.approval | packages/core/src/governance/approval.tk |
| core.governance.dashboard | packages/core/src/governance/dashboard.tk |
| core.governance.dsar | packages/core/src/governance/dsar.tk |
| core.governance.external | packages/core/src/governance/external.tk |
| core.governance.forecast | packages/core/src/governance/forecast.tk |
| core.governance.report | packages/core/src/governance/report.tk |
| core.governance.report-engine | packages/core/src/governance/report-engine.tk |
| core.governance.report-export | packages/core/src/governance/report-export.tk |
| core.governance.use_cases | packages/core/src/governance/use_cases.tk |
| core.governance.value | packages/core/src/governance/value.tk |
| core.memory.context | packages/core/src/memory/context.tk |
| core.memory.graph | packages/core/src/memory/graph.tk |
| core.memory.mcp_server | packages/core/src/memory/mcp_server.tk |
| core.memory.mining | packages/core/src/memory/mining.tk |
| core.memory.palace (full) | packages/core/src/memory/palace.tk |
| core.memory.privacy | packages/core/src/memory/privacy.tk |
| core.memory.storage | packages/core/src/memory/storage.tk |
| core.memory.shorthand | packages/core/src/memory/shorthand.tk |
| core.mcp.client | packages/core/src/mcp/client.tk |
| core.mcp.discovery | packages/core/src/mcp/discovery.tk |
| core.agents.executor | packages/core/src/agents/executor.tk |
| core.agents.latency | packages/core/src/agents/latency.tk |
| core.agents.observability | packages/core/src/agents/observability.tk |
| core.agents.overnight | packages/core/src/agents/overnight.tk |
| core.agents.pipeline | packages/core/src/agents/pipeline.tk |
| core.agents.registry | packages/core/src/agents/registry.tk |
| core.agents.sandbox | packages/core/src/agents/sandbox.tk |
| core.agents.templates | packages/core/src/agents/templates.tk |
| core.models.hardware | packages/core/src/models/hardware.tk |
| core.models.infer | packages/core/src/models/infer.tk |
| core.models.mlx | packages/core/src/models/mlx.tk |
| core.models.ollama | packages/core/src/models/ollama.tk |
| core.optimiser.cache | packages/core/src/optimiser/cache.tk |
| core.optimiser.llmlingua | packages/core/src/optimiser/llmlingua.tk |
| core.optimiser.profiler | packages/core/src/optimiser/profiler.tk |
| core.optimiser.budget_types | packages/core/src/optimiser/budget_types.tk |
| core.optimiser.toon_types | packages/core/src/optimiser/toon_types.tk |
| core.storage.backup | packages/core/src/storage/backup.tk |
| core.storage.dashboard | packages/core/src/storage/dashboard.tk |
| core.auth.oauth | packages/core/src/auth/oauth.tk |
| core.auth.pkce | packages/core/src/auth/pkce.tk |
| core.auth.refresh | packages/core/src/auth/refresh.tk |
| core.auth.token_store | packages/core/src/auth/token_store.tk |
| core.companion.channel | packages/core/src/companion/channel.tk |
| core.companion.discovery | packages/core/src/companion/discovery.tk |
| core.companion.executor | packages/core/src/companion/executor.tk |
| core.companion.exo | packages/core/src/companion/exo.tk |
| core.companion.types | packages/core/src/companion/types.tk |
| core.eval.advisor | packages/core/src/eval/advisor.tk |
| core.eval.bench | packages/core/src/eval/bench.tk |
| core.eval.compare | packages/core/src/eval/compare.tk |
| core.extensions.gateway_hooks | packages/core/src/extensions/gateway_hooks.tk |
| core.extensions.pipeline_hooks | packages/core/src/extensions/pipeline_hooks.tk |
| core.extensions.provider_registry | packages/core/src/extensions/provider_registry.tk |
| core.feedback.draft | packages/core/src/feedback/draft.tk |
| core.feedback.learning | packages/core/src/feedback/learning.tk |
| core.feedback.pipeline | packages/core/src/feedback/pipeline.tk |
| core.feedback.report | packages/core/src/feedback/report.tk |
| core.feedback.reporter | packages/core/src/feedback/reporter.tk |
| core.feedback.store | packages/core/src/feedback/store.tk |
| core.feedback.types | packages/core/src/feedback/types.tk |
| core.installer.* (9 modules) | packages/core/src/installer/*.tk |
| core.metrics.collector | packages/core/src/metrics/collector.tk |
| core.monitoring.sysmon | packages/core/src/monitoring/sysmon.tk |
| core.audit.metrics | packages/core/src/audit/metrics.tk |
| core.policy.* (12 modules) | packages/core/src/policy/*.tk |
| core.setup.wizard | packages/core/src/setup/wizard.tk |
| core.update.checker | packages/core/src/update/checker.tk |
| core.router.routellm | packages/core/src/router/routellm.tk |
| core.router.examples | packages/core/src/router/examples.tk |

### Low Priority (utility/internal/types)
| Module | Path |
|---|---|
| core.governance.types | packages/core/src/governance/types.tk |
| core.governance.violation-types | packages/core/src/governance/violation-types.tk |
| core.memory.types | packages/core/src/memory/types.tk |
| core.memory.schema | packages/core/src/memory/schema.tk |
| core.privacy.test_harness | packages/core/src/privacy/test_harness.tk |
| shared.config | packages/shared/src/config.tk |
| shared.errors | packages/shared/src/errors.tk |
| shared.log | packages/shared/src/log.tk |
| shared.result | packages/shared/src/result.tk |
| shared.types | packages/shared/src/types.tk |
| browser.extensions.core | packages/browser/extensions/core.tk |
| browser.shell | src/browser/shell.tk |
| browser.window_manager | src/browser/window_manager.tk |
| browser.workspace.chat_panel | src/browser/workspace/chat_panel.tk |
| browser.workspace.dashboard_persist | src/browser/workspace/dashboard_persist.tk |
| browser.workspace.extractor | src/browser/workspace/extractor.tk |
| browser.workspace.privacy_metadata | src/browser/workspace/privacy_metadata.tk |
| browser.workspace.tabs | src/browser/workspace/tabs.tk |

### moke Untested
| Module | Priority |
|---|---|
| moke.approval | Medium |
| moke.companion_simulator | Medium |
| moke.compute | Medium |
| moke.console_log | Low |
| moke.dashboard_flow | Medium |
| moke.feedback.feedback | Medium |
| moke.hooks | Low |
| moke.main | Low |
| moke.mcp.broker_status | Medium |
| moke.mcp.memory_demo | Low |
| moke.mcp.tool_panel | Medium |
| moke.memory.memory | Medium |
| moke.ml.engine | Medium |
| moke.ml.proposal | Medium |
| moke.provider | Medium |
| moke.sensitivity | Medium |
| moke.token_optimisation | Medium |
| moke.upload | Low |
| moke.workspace | Low |
| moke._handlers | Low |
