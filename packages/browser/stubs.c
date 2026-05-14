/* stubs.c — placeholder implementations for core module functions.
 * These will be replaced when the core modules compile fully.
 * Symbol names use toke's module-mangled format: module_path_funcname */

#include <stdint.h>

/* browser.extensions.core */
int64_t browser_extensions_core_getconfig(void) { return 0; }
void browser_extensions_core_setapikey(int64_t a, int64_t b) { (void)a; (void)b; }
int64_t browser_extensions_core_getgateway(void) { return 0; }
int64_t browser_extensions_core_getpipelineconfig(void) { return 0; }
int64_t browser_extensions_core_getrouter(void) { return 0; }
int64_t browser_extensions_core_getdispatcher(void) { return 0; }
int64_t browser_extensions_core_getauditstore(void) { return 0; }
int64_t browser_extensions_core_getpreference(int64_t k) { (void)k; return 0; }
void browser_extensions_core_setpreference(int64_t k, int64_t v) { (void)k; (void)v; }
int64_t browser_extensions_core_gettabstore(void) { return 0; }
void browser_extensions_core_settabstore(int64_t s) { (void)s; }

/* core.models.ollama */
int64_t core_models_ollama_new(int64_t url) { (void)url; return 0; }
int64_t core_models_ollama_healthcheck(int64_t c) { (void)c; return 0; }
int64_t core_models_ollama_listmodels(int64_t c) { (void)c; return 0; }
int64_t core_models_ollama_listrunning(int64_t c) { (void)c; return 0; }

/* core.privacy.pipeline */
int64_t core_privacy_pipeline_run(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }
int64_t core_privacy_pipeline_applypreset(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t core_privacy_pipeline_setentityenabled(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }
int64_t core_privacy_pipeline_setlayerenabled(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* core.router.router */
int64_t core_router_router_route(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e, int64_t f) {
  (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; return 0;
}

/* core.governance.gateway */
int64_t core_governance_gateway_submit(int64_t a, int64_t b) { (void)a; (void)b; return 0; }

/* core.providers.types */
int64_t core_providers_types_usermsg(int64_t t) { (void)t; return 0; }

/* core.providers.dispatcher */
int64_t core_providers_dispatcher_dispatch(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* core.audit.metrics */
int64_t core_audit_metrics_summary(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t core_audit_metrics_emptysummary(void) { return 0; }
int64_t core_audit_metrics_byprovider(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t core_audit_metrics_tokensavingsseries(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t core_audit_metrics_cachestats(int64_t a) { (void)a; return 0; }
int64_t core_audit_metrics_emptycachestats(void) { return 0; }
int64_t core_audit_metrics_export(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* loke.browser.workspace.tabs */
int64_t loke_browser_workspace_tabs_listtabs(int64_t s) { (void)s; return 0; }
int64_t loke_browser_workspace_tabs_activetab(int64_t s) { (void)s; return 0; }
int64_t loke_browser_workspace_tabs_activate(int64_t s, int64_t id) { (void)s; (void)id; return 0; }
int64_t loke_browser_workspace_tabs_pin(int64_t s, int64_t id) { (void)s; (void)id; return 0; }
int64_t loke_browser_workspace_tabs_reorder(int64_t s, int64_t j) { (void)s; (void)j; return 0; }
int64_t loke_browser_workspace_tabs_open(int64_t s, int64_t u, int64_t t) { (void)s; (void)u; (void)t; return 0; }
int64_t loke_browser_workspace_tabs_close(int64_t s, int64_t id) { (void)s; (void)id; return 0; }

/* shared.log */
int64_t shared_log_newcorrelationid(void) { return 0; }
int64_t shared_log_info(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }
int64_t shared_log_warn(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* models.hardware */
int64_t models_hardware_detectprofile(void) { return 0; }

/* core.monitoring.sysmon */
int64_t core_monitoring_sysmon_snapshot(void) { return 0; }
int64_t core_monitoring_sysmon_tojson(int64_t a) { (void)a; return 0; }

/* ooke.config */
int64_t ooke_config_cfgdefault(void) { return 0; }
int64_t ooke_config_configload(int64_t p) { (void)p; return 0; }

/* ooke.serve */
int64_t ooke_serve_serverun(int64_t a, int64_t b, int64_t c, int64_t d,
  int64_t e, int64_t f, int64_t g, int64_t h, int64_t i, int64_t j,
  int64_t k, int64_t l) {
  (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;
  (void)g;(void)h;(void)i;(void)j;(void)k;(void)l; return 0;
}

/* ooke.template */
int64_t ooke_template_renderfile(int64_t a, int64_t b) { (void)a; (void)b; return 0; }

/* page response helpers (ooke template rendering) */
int64_t html(int64_t a) { (void)a; return 0; }
int64_t json(int64_t a) { (void)a; return 0; }
int64_t text(int64_t a, int64_t b) { (void)a; (void)b; return 0; }

/* missing stdlib glue */
int64_t tk_http_pathparam_w(int64_t r, int64_t n) { (void)r; (void)n; return 0; }
int64_t tk_http_queryparam_w(int64_t r, int64_t n) { (void)r; (void)n; return 0; }
int64_t tk_json_encstr_w(int64_t s) { (void)s; return 0; }
int64_t tk_json_getstr_w(int64_t b, int64_t k) { (void)b; (void)k; return 0; }
int64_t tk_str_fromu16_w(int64_t n) { (void)n; return 0; }
int64_t tk_str_fromu32_w(int64_t n) { (void)n; return 0; }
int64_t tk_str_fromu64_w(int64_t n) { (void)n; return 0; }
int64_t tk_sys_chipname_w(void) { return 0; }
double tk_sys_diskfreegb_w(void) { return 0.0; }
int64_t tk_sys_isarm64_w(void) { return 1; }
int64_t tk_sys_platform_w(void) { return 0; }
