/* stubs.c — placeholder implementations for core module functions.
 * These will be replaced when the core modules compile fully.
 * Each returns 0/NULL to allow the binary to link and serve the UI. */

#include <stdint.h>
#include <string.h>
#include <stdlib.h>

/* browser.extensions.core */
int64_t getconfig(void) { return 0; }
void setapikey(int64_t a, int64_t b) { (void)a; (void)b; }
int64_t getgateway(void) { return 0; }
int64_t getpipelineconfig(void) { return 0; }
int64_t getrouter(void) { return 0; }
int64_t getdispatcher(void) { return 0; }
int64_t getauditstore(void) { return 0; }
int64_t getpreference(int64_t key) { (void)key; return 0; }
void setpreference(int64_t key, int64_t val) { (void)key; (void)val; }
int64_t gettabstore(void) { return 0; }
void settabstore(int64_t s) { (void)s; }

/* core.models.ollama */
int64_t new(int64_t url) { (void)url; return 0; }
int64_t healthcheck(int64_t client) { (void)client; return 0; }
int64_t listmodels(int64_t client) { (void)client; return 0; }
int64_t listrunning(int64_t client) { (void)client; return 0; }

/* core.privacy.pipeline */
int64_t run(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }
int64_t applypreset(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t setentityenabled(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }
int64_t setlayerenabled(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* core.router.router */
int64_t route(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e, int64_t f) {
  (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; return 0;
}

/* core.governance.gateway */
int64_t submit(int64_t a, int64_t b) { (void)a; (void)b; return 0; }

/* core.providers.types */
int64_t usermsg(int64_t text) { (void)text; return 0; }

/* core.providers.dispatcher */
int64_t dispatch(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* core.audit.metrics */
int64_t summary(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t emptysummary(void) { return 0; }
int64_t byprovider(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t tokensavingsseries(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t cachestats(int64_t a) { (void)a; return 0; }
int64_t emptycachestats(void) { return 0; }
/* 'export' is a C++ keyword but valid C identifier */
int64_t export(int64_t, int64_t, int64_t);
int64_t export(int64_t a, int64_t b, int64_t c) { (void)a; (void)b; (void)c; return 0; }

/* loke.browser.workspace.tabs */
int64_t listtabs(int64_t s) { (void)s; return 0; }
int64_t activetab(int64_t s) { (void)s; return 0; }
int64_t activate(int64_t s, int64_t id) { (void)s; (void)id; return 0; }
int64_t pin(int64_t s, int64_t id) { (void)s; (void)id; return 0; }
int64_t reorder(int64_t s, int64_t j) { (void)s; (void)j; return 0; }
int64_t open(int64_t s, int64_t u, int64_t t) { (void)s; (void)u; (void)t; return 0; }
int64_t close(int64_t s, int64_t id) { (void)s; (void)id; return 0; }

/* shared.log */
int64_t newcorrelationid(void) { return 0; }

/* models.hardware */
int64_t detectprofile(void) { return 0; }

/* core.monitoring.sysmon */
int64_t snapshot(void) { return 0; }

/* ooke.config stubs */
int64_t cfgdefault(void) { return 0; }

/* missing stdlib glue stubs */
int64_t tk_http_pathparam_w(int64_t req, int64_t name) { (void)req; (void)name; return 0; }
int64_t tk_http_queryparam_w(int64_t req, int64_t name) { (void)req; (void)name; return 0; }
int64_t tk_json_encstr_w(int64_t s) { (void)s; return 0; }
int64_t tk_json_getstr_w(int64_t body, int64_t key) { (void)body; (void)key; return 0; }
int64_t tk_str_fromu16_w(int64_t n) { (void)n; return 0; }
int64_t tk_str_fromu32_w(int64_t n) { (void)n; return 0; }
int64_t tk_str_fromu64_w(int64_t n) { (void)n; return 0; }
int64_t tk_sys_chipname_w(void) { return 0; }
double tk_sys_diskfreegb_w(void) { return 0.0; }
int64_t tk_sys_isarm64_w(void) { return 1; }
int64_t tk_sys_platform_w(void) { return 0; }

/* page rendering */
int64_t renderfile(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t html(int64_t a) { (void)a; return 0; }
int64_t json(int64_t a) { (void)a; return 0; }
int64_t text(int64_t a, int64_t b) { (void)a; (void)b; return 0; }
int64_t tojson(int64_t a) { (void)a; return 0; }
