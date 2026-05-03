# toke v3 Migration Issues — Post-Batch Status

**Date:** 2026-05-04
**Commit:** 3d412a9
**Compile status:** 85/562 files compile clean (15.1%)
**Files with errors:** 540
**Unique error types:** 156

---

## #1 — 70 files: `expected field, got '$'`

### Example 1: `packages/mcp-broker/src/main.tk:7`
```
>>>   let cfg=s.$brokerconfig{ port:s.defaultport(); datadir:"./data" };
    log.info("mcp broker starting on port 11436";"broker";"system");
```

### Example 2: `packages/core/src/privacy/regex.tk:88`
```
            let placeholder=ph.makeplaceholder(pdef.name;entityindex);
>>>           let entity=t.$piientity{
              entitytype:pdef.name;
```

### Example 3: `packages/core/src/agents/registry.tk:29`
```
  f=register(reg:$agentregistry;agent:i64):void!$lokeerr{
>>>     <$lokeerr.$configerr("agent must have a name")
    }el{
```

### Example 4: `packages/core/src/agents/templates.tk:18`
```
      description:"Summarises activity from the past 24 hours";
>>>     trigger:$triggertype.$schedule("0 7 * * *");
      modelpreference:"qwen2.5:7b";
```

### Example 5: `packages/core/src/models/streaming.tk:15`
```
>>>   let opts=inf.$streamopts{ ramceilinggb:cfg.ramceilinggb; prefetchlayers:cfg.prefetchlayers; requiresnvme:true };
    let path=str.concat(cfg.modeldir;str.concat("/";modelid));
```

**Intent:** Constructing a struct literal with module-qualified type.
**Root cause:** `mod.$typename{field:val}` — module prefix on struct constructor in expression.
**Fix:** Drop module prefix: `$typename{field:val}`. Module qualification not valid in expressions.

---

## #2 — 30 files: `missing semicolon`

### Example 1: `packages/mcp-broker/src/registry.tk:20`
```
>>>   let result=reg.servers.find|s{ toolname.startswith(s.toolprefix) };
    <result
```

### Example 2: `packages/core/src/pipeline/history.tk:19`
```
      let trimmed=mut.@($pipelinerun);
>>>     runs.each|r|{
        if(skip){skip=false}el{
```

### Example 3: `packages/core/src/pipeline/emitter.tk:50`
```
    let totalms=mut.0;
>>>   emitter.events.each|e|{
      totalms=totalms+e.durationms;
```

### Example 4: `packages/core/src/memory/mining.tk:56`
```
    let storedcount=0;
>>>   sentences.each|sentence{
      let trimmed=str.trim(sentence);
```

### Example 5: `packages/core/src/memory/search.tk:26`
```
    let stops=stopwords();
>>>   stops.each|sw{
      if(str.eq(sw;word)){
```

**Intent:** Code between statement boundaries.
**Root cause:** `.each|var{` closure syntax, `|$err` error union in return type, `}else{` not converted, or missing `};` block terminator.
**Fix:** Convert `.each|v{` to `lp` loop, `|$err` → `!$err`, ensure all blocks end with `};`.

---

## #3 — 29 files: `unexpected token in expression, got 'if'`

### Example 1: `packages/core/src/metrics/collector.tk:42`
```
  f=record(conn:i64;event:$metricevent;extconfig:i64):void!$lokeerr{
>>>   let localint=if(event.routedlocal){1}el{0};
    let cacheint=if(event.cachehit){1}el{0};
```

### Example 2: `packages/core/src/privacy/web_meta.tk:200`
```
    let line1=str.concat("Privacy grade : ";meta.privacygrade);
>>>   let line3=str.concat("HTTPS         : ";if(meta.https){"yes"}el{"no"});
    let line4=str.concat("Cookies       : ";str.fromint(meta.cookiecount));
```

### Example 3: `packages/core/src/privacy/content.tk:16`
```
  f=extract(html:str;url:str):$pagecontent{
>>>   let title=if(str.len(titleraw)>0){str.strip(titleraw)}el{""};
```

### Example 4: `packages/core/src/memory/shorthand.tk:70`
```
    let startexpansion=str.concat(expansion;" ");
>>>   let s=if(str.contains(s;startabbrev)){
      let parts=str.split(s;startabbrev);
```

### Example 5: `packages/core/src/setup/wizard.tk:38`
```
    let cores=sys.cpucount();
>>>   log.info(str.concat("RAM: ";str.concat(str.fromint(ram);str.concat("GB, cores: ";str.concat(str.fromint(cores);str.concat(", Apple Silicon: ";if(applesilicon){"yes"}el{"no"})))));"setup.wizard";"system");
    <$hardwareprofile{
```

**Intent:** Using `if` as an expression (let x = if(cond){a}el{b}).
**Root cause:** v3 `if` is a statement, not an expression. Cannot assign result of `if`.
**Fix:** Restructure: `let x=mut.default; if(cond){x=a}el{x=b};`

---

## #4 — 20 files: `unexpected token in expression, got '='`

### Example 1: `packages/core/src/governance/use_cases.tk:108`
```
    let i=0;
>>>     if(i>=count){
        <$$unknownerr(str.concat("use case not found: ";id))
```

### Example 2: `packages/core/src/policy/conflict.tk:13`
```
>>>   if(adays<=bdays){
      <$conflictresolution{chosenvalue:str.fromint(adays);chosensource:asource;reason:"shortest retention wins (data minimisation)"}
```

### Example 3: `packages/cli/src/ask.tk:38`
```
    let argc=str.len(args);
>>>     if(i>=argc){ break }el{
        let arg=args.get(i);
```

### Example 4: `packages/cli/src/port.tk:42`
```
  f=findfreeport():i32{
>>>   lp(let lv=0;port<=portrangeend();lv=lv){
      if(isportfree(port)){
```

### Example 5: `src/memory/enrichment.tk:38`
```
  f=buildsearchquery(prompt:str):str{
>>>   if(length <= 100){
      <prompt
```

**Intent:** Struct field initialization or comparison.
**Root cause:** `field=value` in struct literal (should be `field:value`), or `>=` comparison (not in v3).
**Fix:** Use `:` for struct fields, use `>` or separate comparison for `>=`.

---

## #5 — 20 files: `module 'ooke.template' not found; available: `

### Example 1: `packages/browser/pages/tabs.tk:3`
```
  m=page.tabs;
>>> i=tpl:ooke.template;
```

### Example 2: `packages/browser/pages/index.tk:3`
```
  m=page.index;
>>> i=tpl:ooke.template;
```

### Example 3: `packages/browser/pages/sysmon.tk:3`
```
  m=page.sysmon;
>>> i=tpl:ooke.template;
  i=sysmon:core.monitoring.sysmon;
```

### Example 4: `packages/browser/pages/approve.tk:3`
```
  m=page.approve;
>>> i=tpl:ooke.template;
```

### Example 5: `packages/browser/pages/privacy.tk:3`
```
  m=page.privacy;
>>> i=tpl:ooke.template;
```

**Intent:** Importing a module from another package.
**Root cause:** Cross-package module resolution fails in standalone compilation.
**Fix:** Not a syntax error — resolves at link time during `ooke compile`. Can ignore for migration.

---

## #6 — 17 files: `unexpected token in expression, got '<'`

### Example 1: `packages/core/src/privacy/placeholder_store.tk:37`
```
        log.debug("stored placeholder entry";"placeholder_store";pmap.requestid);
>>>       <$err($storageerr(str.concat("failed to store placeholder entry for request: ";pmap.requestid)))
    }
```

### Example 2: `packages/core/src/privacy/ner.tk:97`
```
    mt result {
>>>       <$err($$networkerr("ner detect_entities: failed to reach Ollama /api/chat"));
      $ok:raw
```

### Example 3: `packages/core/src/auth/token_store.tk:24`
```
    let result=kc.get(service();account(adapterid;"access_token"));
>>>     $some:v <v;
      $none <""
```

### Example 4: `packages/core/src/mcp/discovery.tk:36`
```
    mt healthresp {
>>>       <$$networkerr("port not responding");
      $ok:raw
```

### Example 5: `packages/core/src/optimiser/toon.tk:35`
```
    let boolval=json.trybool(v);
>>>     $ok:b <$$bool;
      $err:e
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #7 — 17 files: `expected ':', got '='`

### Example 1: `packages/shared/src/log.tk:27`
```
  f=debug(msg:str;component:str;correlationid:str):void{
>>>     level=$debug;
      msg=msg;
```

### Example 2: `packages/shared/src/config.tk:18`
```
  f=defaultconfig():$lokeconfig{
>>>     port=11430;
      datadir="~/.loke";
```

### Example 3: `packages/cli/src/proxy.tk:32`
```
  f=defaultconfig(tool:str):$proxyconfig{
>>>     port=11431;
      targettool=tool;
```

### Example 4: `packages/moke/data/registry.tk:37`
```
      let entry=aulist.get(i);
>>>       id="au." + entry.id;
        name=entry.name;
```

### Example 5: `packages/moke/src/sensitivity.tk:30`
```
    if(l = "PUBLIC"){
>>>       level="PUBLIC";
        colour="green";
```

**Intent:** Struct field initialization or comparison.
**Root cause:** `field=value` in struct literal (should be `field:value`), or `>=` comparison (not in v3).
**Fix:** Use `:` for struct fields, use `>` or separate comparison for `>=`.

---

## #8 — 17 files: `expected ')', got '{'`

### Example 1: `packages/browser/src/shell.tk:17`
```
    log.info(str.concat("loke browser mode starting — ";url);"shell";"system");
>>>   wv.onclose(handle;f(){ log.info("window closed";"shell";"system") });
    wv.runeventloop();
```

### Example 2: `packages/moke/src/tier_visualiser.tk:64`
```
>>>   let modelsjson=str.join(t.recommendedmodels.map(m{ <"\"" + str.jsonescape(m) + "\"" }); ",");
    let j=mut."{";
```

### Example 3: `packages/moke/src/profiler.tk:34`
```
    );
>>>   hits.each(h{
      if(str.contains(lc;h)){ found=true }
```

### Example 4: `packages/moke/src/streaming.tk:112`
```
>>>   let eventsjson=str.join(s.events.map(e{ <eventtojson(e) });",");
    let j="{";
```

### Example 5: `packages/moke/src/ml/engine.tk:62`
```
    if(n = 0){ <0.0 };
>>>   vals.each(v{ total=total + v });
    <total / str.tofloat(str.fromint(n))
```

**Intent:** Function parameter list or array type annotation.
**Root cause:** `@$str{` — array type `@$str` immediately followed by `{` block, missing `)` to close params.
**Fix:** Add `)` to close function signature: `args:@str):returntype{`.

---

## #9 — 16 files: `unexpected token at statement level, got '{'`

### Example 1: `src/mcp-broker/transport.tk:66`
```
        latencyms:0
>>>   }{
      let statusstr=str.fromi32(res.status);
```

### Example 2: `src/core/hardware/profile.tk:44`
```
    if(p.unifiedmemorygb > 0){
>>>   }{
      <p.ramgb + p.vramgb
```

### Example 3: `src/core/hardware/recommender.tk:35`
```
    if(quant = "fp16"){
>>>   }{
      estimatedvramgb=paramsb * 0.6
```

### Example 4: `src/core/cache/semantic.tk:59`
```
    if(a.len() = 0){
>>>   }{
      if(b.len() = 0){
```

### Example 5: `src/core/config/schema.tk:43`
```
        log.warn("config validation failed: data_dir must not be empty");
>>>     }{
        let validlevels=@("debug";"info";"warn";"error");
```

**Intent:** Code block at statement level.
**Root cause:** Orphan `{` without preceding `if`/`el`/`lp`/`f=`/`t=`.
**Fix:** Structural issue — brace mismatch from prior match arm or if/el chain.

---

## #10 — 15 files: `unexpected token in expression, got ')'`

### Example 1: `packages/cli/src/session.tk:56`
```
    );
>>>     $ok:v ();
      $err:e ()
```

### Example 2: `packages/cli/src/output.tk:13`
```
  f=printline(s:str):void{
>>>   <()
  };
```

### Example 3: `packages/browser/pages/installer.tk:46`
```
      if(ollamaok=$stopped){
>>>     }el{()}
    };
```

### Example 4: `packages/browser/pages/api/health.tk:20`
```
      if(ollamastatus=$stopped){
>>>     }el{()}
    };
```

### Example 5: `packages/browser/pages/api/tabs.tk:12`
```
  f=tabjson(t:i64):str{
>>>   if(t.pinned){ pinnedstr="true" }el{()};
    <str.concat("{";
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #11 — 12 files: `unexpected token in expression, got '{'`

### Example 1: `packages/mcp-broker/src/aggregator.tk:15`
```
    let resp=http.post(url;body;"application/json");
>>>     $ok:r {
        let parsed=json.parse(r.body);
```

### Example 2: `packages/mcp-broker/src/server.tk:19`
```
    let parsed=json.parse(reqbody);
>>>     $err:e {
        <proto.errorresponse(-32700;"Parse error";e)
```

### Example 3: `packages/core/src/memory/decay.tk:44`
```
    let pruned=0;
>>>     $ok:rows {
        rows.each|row{
```

### Example 4: `packages/core/src/memory/privacy.tk:29`
```
  f=loadprefs(palace:i64):$privacyprefs{
>>>     $ok:rows {
        if(rows.len > 0){
```

### Example 5: `packages/core/src/memory/palace.tk:21`
```
    let path=str.concat(datadir;"/memory.db");
>>>     $ok:conn {
        mt schema.createtables(conn) {
```

**Intent:** Multi-statement logic inside a match arm.
**Root cause:** `mt expr { $ok:v { stmt1; stmt2; <result } }` — blocks not allowed in match arms.
**Fix:** Extract block to helper function, or restructure as nested `let` + single return expression.

---

## #12 — 11 files: `unexpected token`

### Example 1: `packages/core/src/agents/latency.tk:21`
```
>>> let latencyinteractive=$latencyclass{
    name:"interactive";
```

### Example 2: `packages/core/src/feedback/report.tk:26`
```
  };
>>> let typebug = "bug";
  let typefeature = "feature";
```

### Example 3: `src/mcp-broker/registry.tk:34`
```
>>> let gservers:@$serverstate=@();
```

### Example 4: `src/mcp-broker/config.tk:7`
```
>>> m=loke.mcpbroker.config;
  i=str:std.string;
```

### Example 5: `src/mcp-broker/broker.tk:7`
```
>>> m=loke.mcpbroker.broker;
  i=str:std.string;
```

**Intent:** Various structural code patterns that v3 parser rejects.
**Root causes:** Top-level `let` constants, `mut` type modifier in params, qualified types in expressions, `}{` without `el`, duplicate `m=` declarations.
**Fix:** Requires per-file structural analysis — no single regex covers all cases.

---

## #13 — 9 files: `module 'shared.types' not found; available: `

### Example 1: `packages/core/src/privacy/guardian.tk:3`
```
  m=core.privacy.guardian;
>>> i=t:shared.types;
  i=str:std.str;
```

### Example 2: `packages/core/src/memory/types.tk:4`
```
>>> i=t:shared.types;
```

### Example 3: `packages/core/src/providers/types.tk:5`
```
>>> i=t:shared.types;
```

### Example 4: `packages/core/src/agents/observability.tk:3`
```
  m=core.agents.observability;
>>> i=t:shared.types;
  i=at:core.agents.types;
```

### Example 5: `packages/core/src/agents/executor.tk:3`
```
  m=core.agents.executor;
>>> i=t:shared.types;
  i=at:core.agents.types;
```

**Intent:** Importing a module from another package.
**Root cause:** Cross-package module resolution fails in standalone compilation.
**Fix:** Not a syntax error — resolves at link time during `ooke compile`. Can ignore for migration.

---

## #14 — 9 files: `module 'shared.log' not found; available: `

### Example 1: `packages/core/src/storage/keychain.tk:3`
```
  m=core.storage.keychain;
>>> i=log:shared.log;
  i=str:std.str;
```

### Example 2: `packages/core/src/extensions/gateway_hooks.tk:4`
```
>>> i=log:shared.log;
```

### Example 3: `packages/core/src/extensions/pipeline_hooks.tk:4`
```
>>> i=log:shared.log;
```

### Example 4: `packages/core/src/extensions/provider_registry.tk:4`
```
>>> i=log:shared.log;
```

### Example 5: `packages/core/src/installer/models.tk:4`
```
  m=core.installer.models;
>>> i=log:shared.log;
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #15 — 8 files: `expected identifier after '$'`

### Example 1: `packages/core/src/memory/aaak.tk:28`
```
>>>   <$$medium
  };
```

### Example 2: `packages/core/src/models/registry.tk:36`
```
  f=defaultentries():@$modelcapability{
>>>     $modelcapability{modelid:"claude-3-5-sonnet-20241022";provider:$$anthropic;task:$$chat;qualityscore:0.95;speedtoks:80.0;contextwindow:200000;supportstools:true;local:false};
      $modelcapability{modelid:"claude-3-5-sonnet-20241022";provider:$$anthropic;task:$$codegeneration;qualityscore:0.95;speedtoks:80.0;contextwindow:200000;supportstools:true;local:false};
```

### Example 3: `packages/core/src/models/queue.tk:64`
```
      prompt:prompt;
>>>     status:$$pending;
      createdat:"";
```

### Example 4: `packages/core/src/models/hardware.tk:40`
```
      gpuvramgb:0.0;
>>>     disktype:$$unknown;
      diskreadmbs:0.0;
```

### Example 5: `packages/core/src/optimiser/cache.tk:55`
```
    let results=vs.search(col;embedding;1;cfg.threshold);
>>>     <$$none
    }el{
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #16 — 7 files: `expected variant name after '$', got '$'`

### Example 1: `packages/core/src/privacy/test_harness.tk:117`
```
  f=sensitivitytostr(s:$sensitivitylevel):str{
>>>     $$public;       <"PUBLIC";
      $$internal;     <"INTERNAL";
```

### Example 2: `packages/core/src/memory/export.tk:80`
```
  f=buildcontent(rows:@($row);format:$exportformat):str{
>>>     $$json {
        let lines=rows.map|row{ str.concat("  ";rowtojson(row)) };
```

### Example 3: `packages/core/src/providers/dispatcher.tk:33`
```
  f=dispatch(d:$dispatcher;req:i64;provider:$provider):i64!$lokeerr{
>>>     $$anthropic;
        let client=ant.new(d.keys.anthropic);
```

### Example 4: `packages/core/src/feedback/types.tk:65`
```
  f=ratinglabel(r:$feedbackrating):str{
>>>     $$thumbsup;   <"thumbs_up";
      $$thumbsdown; <"thumbs_down";
```

### Example 5: `packages/core/src/governance/dashboard.tk:32`
```
  f=statussymbol(s:$ragstatus):str{
>>>     $$green; <"[OK]";
      $$amber; <"[!!]";
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #17 — 7 files: `expected binding name, got '<'`

### Example 1: `packages/core/src/privacy/template.tk:145`
```
    let parsed=mt json.dec(paramsjson) {
>>>     $err: <result
    };
```

### Example 2: `packages/core/src/feedback/store.tk:25`
```
  )";
>>>     $ok: <$ok(void);
      $err:e <$err($$storageerr("failed to create feedback table"))
```

### Example 3: `packages/core/src/governance/ai_gov.tk:36`
```
  )";
>>>     $ok: <true;
      $err:e <false
```

### Example 4: `packages/core/src/governance/monitoring.tk:43`
```
  )";
>>>     $ok: <$ok(void);
      $err:e <$err($$storageerr("failed to create quality_signals table"))
```

### Example 5: `packages/core/src/governance/dsar.tk:33`
```
  )";
>>>     $ok: <true;
      $err:e <false
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #18 — 6 files: `expected ':', got '('`

### Example 1: `packages/core/src/agents/types.tk:10`
```
  t=$triggertype{
>>>   $schedule(str);
    $filechange(str);
```

### Example 2: `packages/core/src/storage/settings.tk:12`
```
>>>   $strval(str);
    $intval(i64);
```

### Example 3: `packages/core/src/governance/types.tk:24`
```
  t=$policydecision{
>>>   $allowwithwarning(str);
    $requireapproval(str);
```

### Example 4: `packages/shared/src/types.tk:70`
```
>>>   $configerr(str);
    $modelerr(str);
```

### Example 5: `packages/cli/src/health.tk:10`
```
  t=$healthstatus{
>>>   $degraded(str);
    $down(str)
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #19 — 6 files: `module 'core.policy.schema' not found; available: `

### Example 1: `packages/core/src/policy/presets/ccpa.tk:2`
```
>>> i=s:core.policy.schema;
```

### Example 2: `packages/core/src/policy/presets/gdpr.tk:2`
```
>>> i=s:core.policy.schema;
```

### Example 3: `packages/core/src/policy/presets/remaining.tk:2`
```
>>> i=s:core.policy.schema;
```

### Example 4: `packages/core/src/policy/presets/hipaa.tk:2`
```
>>> i=s:core.policy.schema;
```

### Example 5: `packages/core/src/policy/presets/au-privacy.tk:2`
```
>>> i=s:core.policy.schema;
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #20 — 6 files: `expected '=', got '.'`

### Example 1: `packages/moke/tests/unit/feedback_test.tk:6`
```
>>> t.test("feedback entry has required fields";f(){
    let entry = {
```

### Example 2: `packages/moke/tests/unit/memory_test.tk:6`
```
>>> t.test("palace organises drawers into wings";f(){
    let drawers = .get(
```

### Example 3: `packages/moke/tests/unit/moke/pipeline_panel_test.tk:12`
```
>>>   t.test("all 9 stages are defined in types"){
      let stages=pt.allstages();
```

### Example 4: `src/memory/mining.tk:41`
```
>>> m.gjobs:@$miningjob=@();
```

### Example 5: `src/governance/incidents.tk:38`
```
>>> m.gincidents:@$incident=@();
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #21 — 5 files: `expected ':', got '{'`

### Example 1: `packages/mcp-broker/src/proxy.tk:25`
```
    let found=reg.findfortool(registry;toolname);
>>>     $none {
        log.warn(str.concat("no upstream server for tool: ";toolname);"proxy";"proxy_call");
```

### Example 2: `packages/mcp-broker/src/permissions.tk:28`
```
    let found=reg.findfortool(registry;toolname);
>>>     $none {
        <false
```

### Example 3: `src/platform/testing/scaffold.tk:22`
```
  };
>>> f=generatemigration(name:str;dir:str):(str){
    let fname=str.concat(dir;str.concat("/";str.concat(name;".sql")));
```

### Example 4: `src/platform/http/router.tk:43`
```
>>> f=find(reg:$routeregistry;method:str;path:str):($route){
    let count=reg.entries.len();
```

### Example 5: `src/companion/discovery.tk:85`
```
>>> f=getconfirmationcode(state:$discoverystate;id:str):(str){
    let result:(str)=none;
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #22 — 5 files: `unexpected token in expression, got ';'`

### Example 1: `packages/core/src/privacy/presidio.tk:33`
```
    let result=http.gettimeout(url;2000);
>>>     $httperr:e;
        <false
```

### Example 2: `packages/core/src/privacy/pipeline.tk:432`
```
        let nerresult=ner.detectentities(nerclient;text);
>>>         $lokeerr:e;
            log.warn("NER scan failed — skipping";"pipeline";requestid);
```

### Example 3: `packages/core/src/privacy/ner_local.tk:98`
```
      let entities=@();
>>>       $jsonerr:e;
          log.warn("ner_local: failed to parse model JSON response";"ner_local";"");
```

### Example 4: `packages/core/src/router/routellm.tk:38`
```
    let resp=http.post("http://localhost:11431/route";body);
>>>     $lokeerr:e;
        log.warn("routellm: service unavailable, skipping signal";"routellm";"");
```

### Example 5: `packages/cli/src/main.tk:24`
```
>>>     $ask:prompt;
        out.printline(str.concat("Ask: ";prompt));
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #23 — 5 files: `unexpected token in expression, got 'let'`

### Example 1: `packages/core/src/memory/context.tk:40`
```
    mt pal.walk(palace) {
>>>       let lines=str.split(walkstr;"
  ");
```

### Example 2: `packages/core/src/agents/pipeline.tk:62`
```
        mt findresult {
>>>           let errmsg=str.concat("step failed — agent not found: ";step.agentname);
            log.error(errmsg;"agent_pipeline";pl.name);
```

### Example 3: `packages/core/src/installer/pull.tk:44`
```
    mt child {
>>>       let lines=proc.readlines(handle);
        lines.each|line{
```

### Example 4: `packages/core/src/installer/detect.tk:33`
```
    mt handle {
>>>       let code=process.wait(h);
        mt code {
```

### Example 5: `packages/core/src/installer/uninstall.tk:29`
```
    mt resp {
>>>       let parsed=json.parse(r.body);
        let modellist=json.getarr(parsed;"models");
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #24 — 5 files: `unexpected token in type position`

### Example 1: `packages/core/src/auth/oauth.tk:104`
```
      str.concat("&client_id=";str.concat(cfg.clientid;
>>>   let resp=http.post(client;"";str.tobytes(body);"application/x-www-form-urlencoded")!{
      <$oautherr{adapterid:cfg.adapterid;errorcode:"network_error";errordesc:"token request failed"}
```

### Example 2: `packages/core/src/auth/refresh.tk:34`
```
      str.concat("&refresh_token=";str.concat(refreshtok;
>>>   let resp=http.post(client;"";str.tobytes(body);"application/x-www-form-urlencoded")!{
      <$refreshresult{ok:false;accesstoken:"";refreshtoken:"";expiresin:0;status:0;errormsg:"network error"}
```

### Example 3: `src/platform/i18n/locales.tk:7`
```
>>> f=enau():tr.$locale{
    let entries=@(tr.$localeentry);
```

### Example 4: `tests/unit/mcp/test_server.tk:43`
```
  };
>>> f=testconfig():srv.$serverconfig{
    <srv.$serverconfig{
```

### Example 5: `tests/unit/a11y/test_a11y_engine.tk:33`
```
  };
>>> f=hasviolationrule(result:a11y.$a11yresult;rule:str):bool{
    let i=0;
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---

## #25 — 5 files: `character outside allowed character set`

### Example 1: `packages/core/src/mcp/protocol.tk:73`
```
  f=toolresultok(text:str):str{
>>>   let p1=str.concat("{\"content\":[{\"type\":\"text\",\"text\":\"";escaped);
    <str.concat(p1;"\"}]}")
```

### Example 2: `packages/core/src/mcp/client.tk:120`
```
    let cid=log.newcorrelationid();
>>>   let params=str.concat("{\"name\":\"";str.concat(nameescaped;str.concat("\",\"arguments\":";str.concat(argsjson;"}"))));
    let result=sendrequest(client;"tools/call";params);
```

### Example 3: `packages/core/src/governance/trace.tk:107`
```
>>>   let s2=str.replace(s;"\";"\\ ");
    let s3=str.replace(s2;"\"";"\\ \"");
```

### Example 4: `packages/core/src/policy/export.tk:55`
```
      v=(i < arr.len(fields)){ <fields.get(i) }:{ <"" };
>>>     pair=str.concat("\""; k; "\":\""; escapedv; "\"");
      pairs=arr.push(pairs; pair);
```

### Example 5: `packages/mcp-toke/src/tools.tk:112`
```
        let safestr=if(safetosend(run.result.sensitivity)){"true"}el{"false"};
>>>       let origescaped=str.replace(run.result.original;"\"";"\\"");
        let p1=str.concat("{\"anonymised\":\"";anonescaped);
```

**Intent:** Needs investigation.
**Fix:** Per-file analysis required.

---
