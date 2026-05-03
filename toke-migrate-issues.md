# toke --migrate Issues — Current Status

**Date:** 2026-05-04
**toke version:** 75e906f (parser accepts @($type))
**Compile status:** 86/559 files compile clean (15.4%)
**Files with errors:** 547

---

### #1 — 107 files: `missing semicolon`

**Example 1:** `packages/mcp-broker/src/proxy.tk:16`
```
  }else{
```

**Example 2:** `packages/core/src/privacy/placeholder.tk:46`
```
  loop{
```

**Example 3:** `packages/core/src/privacy/regex.tk:38`
```
  }else{
```

**Fix:** `--migrate` not adding `};` to close blocks, or `}else{` not converted to `}el{` (missing `;` before next statement).

---

### #2 — 71 files: `unexpected token`

**Example 1:** `packages/mcp-broker/src/server.tk:13`
```
let defaultport=11436;
```

**Example 2:** `packages/core/src/privacy/guardian.tk:9`
```
let guardianversion="1.0.0"
```

**Example 3:** `packages/core/src/memory/mining.tk:30`
```
let sourceclipboard=$minesource{
```

**Fix:** Various — qualified types in params (`mod.$type`), top-level `let`, `mut` modifier, or structural issues from agent-generated code.

---

### #3 — 54 files: `expected '(' after '@', got '$'`

**Example 1:** `packages/core/src/installer/uninstall.tk:25`
```
  let models=@$removablemodel@();
```

**Example 2:** `packages/browser/_handlers.tk:123`
```
  let paths=mut.@$str;
```

**Example 3:** `packages/browser/src/_handlers.tk:123`
```
  let paths=mut.@$str;
```

**Fix:** `--migrate` produces mangled `@$type@()` — double @ from array literal conversion. Should be `@($type)` or `@$type`.

---

### #4 — 31 files: `expected ':', got '}'`

**Example 1:** `packages/core/src/privacy/pipeline.tk:31`
```
};
```

**Example 2:** `packages/core/src/memory/export.tk:17`
```
};
```

**Example 3:** `packages/core/src/memory/aaak.tk:29`
```
};
```

**Fix:** Match arm variant without `:binding` — `$variant expr` needs `$variant:v expr`.

---

### #5 — 22 files: `expected ')', got '.'`

**Example 1:** `packages/core/src/metrics/collector.tk:39`
```
f=record(conn:i64;event:i64;extconfig:$external.$externalconfig|void):void|$lokeerr{
```

**Example 2:** `packages/core/src/memory/graph.tk:35`
```
f=upsertentity(palace:$memtypes.palace;e:$entity):bool{
```

**Example 3:** `packages/core/src/memory/privacy.tk:27`
```
f=loadprefs(palace:$memtypes.palace):$privacyprefs{
```

**Fix:** Qualified type `mod.$typename` in function signature — replace with `i64`.

---

### #6 — 19 files: `module 'ooke.template' not found; available: `

**Example 1:** `packages/browser/pages/tabs.tk:3`
```
i=tpl:ooke.template;
```

**Example 2:** `packages/browser/pages/index.tk:3`
```
i=tpl:ooke.template;
```

**Example 3:** `packages/browser/pages/sysmon.tk:3`
```
i=tpl:ooke.template;
```

**Fix:** Link-time dependency — not a syntax error. Resolves during `ooke compile`.

---

### #7 — 17 files: `expected ')' to close array literal, got '@'`

**Example 1:** `tests/unit/auth/test-oauth.tk:35`
```
  let results=mut.@($result@();
```

**Example 2:** `tests/unit/mcp/test_broker.tk:48`
```
  let results=mut.@($result@();
```

**Example 3:** `tests/unit/mcp/test_protocol.tk:41`
```
  let results=mut.@($result@();
```

**Fix:** `@(item1;item2;...` with struct literals inside — `--migrate` doesn't handle multi-line array literals with complex elements.

---

### #8 — 14 files: `unexpected token in expression, got '='`

**Example 1:** `packages/core/src/auth/refresh.tk:22`
```
  <now>=threshold
```

**Example 2:** `packages/core/src/governance/scorecard.tk:63`
```
  if(len >= width){
```

**Example 3:** `packages/core/src/installer/models.tk:17`
```
  if(ramgb >= 64){
```

**Fix:** Struct field init using `=` instead of `:` — `field=value` should be `field:value`.

---

### #9 — 14 files: `expected ')', got '{'`

**Example 1:** `packages/cli/src/policy.tk:10`
```
f=run(args:@$str{
```

**Example 2:** `packages/cli/src/feedback.tk:8`
```
f=run(args:@$str{
```

**Example 3:** `packages/cli/src/report.tk:9`
```
f=run(conn:i64;args:@$str{
```

**Fix:** Function parameter type `@$str{` — array type `@$str` followed by `{` block start, missing `)` to close params.

---

### #10 — 13 files: `expected field, got '$'`

**Example 1:** `packages/mcp-broker/src/main.tk:7`
```
  let cfg=s.$brokerconfig{ port:s.defaultport; datadir:"./data" };
```

**Example 2:** `packages/core/src/models/streaming.tk:14`
```
  opts=inf.$streamopts{ ramceilinggb:cfg.ramceilinggb; prefetchlayers:cfg.prefetchlayers; requiresnvme:true };
```

**Example 3:** `packages/core/src/models/infer.tk:34`
```
  let opts=inf.$inferopts{ngpulayers:99;nthreads:4;seed:0};
```

**Fix:** `$variant` inside struct literal being parsed as field name — structural confusion from `--migrate` output.

---

### #11 — 11 files: `expected '}', got '.'`

**Example 1:** `packages/core/src/pipeline/history.tk:6`
```
  runs:@$pt.pipelinerun);
```

**Example 2:** `packages/core/src/pipeline/emitter.tk:9`
```
  events:@$pt.stageevent);
```

**Example 3:** `packages/core/src/providers/anthropic.tk:13`
```
  config:$pt.providerconfig
```

**Fix:** Needs investigation.

---

### #12 — 9 files: `square brackets are not allowed in default mode; use @() for arrays/maps`

**Example 1:** `packages/mcp-broker/src/registry.tk:25`
```
  <[toke;memory]
```

**Example 2:** `packages/core/src/auth/oauth.tk:105`
```
  let hdrs=@(@str).get(["Content-Type";"application/x-www-form-urlencoded"]);
```

**Example 3:** `packages/core/src/eval/bench.tk:37`
```
defaultcases:@$benchcase = [
```

**Fix:** Needs investigation.

---

### #13 — 9 files: `invalid escape sequence in string literal`

**Example 1:** `packages/core/src/privacy/patterns.tk:5`
```
let patemail="[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}"
```

**Example 2:** `packages/core/src/privacy/content.tk:21`
```
  let noscript=str.replacere(html;"<script[^>]*>[\s\S]*?</script>";"";"gi");
```

**Example 3:** `packages/core/src/feedback/draft.tk:82`
```
\
```

**Fix:** Needs investigation.

---

### #14 — 9 files: `unexpected token in expression, got 'if'`

**Example 1:** `packages/core/src/memory/shorthand.tk:70`
```
  let s=if str.contains(s;startabbrev){
```

**Example 2:** `packages/core/src/setup/wizard.tk:39`
```
  log.info(str.concat("RAM: ";str.concat(str.fromint(ram);str.concat("GB, cores: ";str.concat(str.fromint(cores);str.concat(", Apple Silicon: ";if(applesilicon){"yes"}el{"no"})))));"setup.wizard";"system");
```

**Example 3:** `packages/core/src/feedback/reporter.tk:64`
```
  let out=str.concat("{\"id\":\"";str.concat(report.id;str.concat("\",\"type\":\"";str.concat(report.reporttype;str.concat("\",\"title\":\"";str.concat(report.title;str.concat("\",\"description\":\"";str.concat(report.description;str.concat("\",\"privacy_scanned\":";str.concat(if(report.privacyscanned){"true"}el{"false"};"}"))))))))));
```

**Fix:** Needs investigation.

---

### #15 — 9 files: `unexpected token in expression, got '{'`

**Example 1:** `packages/core/src/governance/report.tk:29`
```
    $ok:rows {
```

**Example 2:** `packages/core/src/companion/executor.tk:14`
```
  mt  { connopt.$none:
```

**Example 3:** `packages/cli/src/doctor.tk:20`
```
    $ok:resp{
```

**Fix:** Needs investigation.

---

### #16 — 8 files: `unexpected token at statement level, got '{'`

**Example 1:** `packages/cli/src/portable.tk:99`
```
  }{
```

**Example 2:** `src/core/cache/semantic.tk:63`
```
  }{
```

**Example 3:** `src/core/storage/vector.tk:39`
```
  }{
```

**Fix:** Needs investigation.

---

### #17 — 7 files: `expected ')', got ':'`

**Example 1:** `packages/mcp-broker/src/permissions.tk:25`
```
f=checktoolpermission(registry:i64:i64;toolname:$str):bool{
```

**Example 2:** `packages/core/src/governance/violation-types.tk:58`
```
f=highestseverity(violations:@$violation:$str{
```

**Example 3:** `packages/core/src/governance/response-scanner.tk:8`
```
f=scanresponse(rawresponse:$str;restoredresponse:$str;requestid:$str;blockedentities:@$str:$vt.scanresult{
```

**Fix:** Needs investigation.

---

### #18 — 7 files: `character outside allowed character set`

**Example 1:** `packages/core/src/mcp/protocol.tk:89`
```
  let p1=str.concat("{\"content\":[{\"type\":\"text\",\"text\":\"";escaped);
```

**Example 2:** `packages/core/src/mcp/client.tk:143`
```
  let params=str.concat("{\"name\":\"";str.concat(nameescaped;str.concat("\",\"arguments\":";str.concat(argsjson;"}"))));
```

**Example 3:** `packages/core/src/optimiser/toon.tk:473`
```
      <str.concat("\"";str.concat(escaped;"\""))
```

**Fix:** Needs investigation.

---

### #19 — 6 files: `expected ':', got '{'`

**Example 1:** `packages/core/src/models/tiers.tk:37`
```
    $interactive {
```

**Example 2:** `packages/core/src/models/mlx.tk:22`
```
f=generate(pool:$mlxpool;modelid:str;prompt:str;maxtokens:i32):(str){
```

**Example 3:** `packages/core/src/optimiser/cache.tk:65`
```
f=lookup(col:i64;prompt:str;pool:i64;cfg:$cacheconfig):($cachehit){
```

**Fix:** Needs investigation.

---

### #20 — 5 files: `expected ':', got 'e'`

**Example 1:** `packages/core/src/privacy/presidio.tk:33`
```
    $httperr e;
```

**Example 2:** `packages/core/src/privacy/ner.tk:27`
```
    $httperr e;
```

**Example 3:** `packages/core/src/optimiser/llmlingua.tk:41`
```
    $httperr e;
```

**Fix:** Needs investigation.

---
