# toke --migrate Issues — Current Status

**Date:** 2026-05-04
**toke version:** 8c4ff12
**Compile status:** 43/559 files compile clean (7.7%)
**Files with errors:** 516 (minus 19 link-time = 497 real syntax errors)

---

## Category 1: `unexpected token` — 71 files

### Pattern A: `}{` instead of `}el{` (19 files)
```
BEFORE: if(a.len() = 0){ <0.0 }{ if(b.len() = 0){ <0.0 }{
AFTER:  if(a.len() = 0){ <0.0 }el{ if(b.len() = 0){ <0.0 }el{
```
**Fix:** `--migrate` should convert `}{` → `}el{` when preceded by if/el block.

### Pattern B: Top-level `let` (21 files)
```
BEFORE: let defaultwindow=$overnightwindow{ starthour:22; endhour:6 };
AFTER:  (move into function — v3 has no top-level let)
```
**Fix:** MANUAL — wrap in init function or module constant syntax.

### Pattern C: `m=$type{` not converted to `t=` (6 files)
```
BEFORE: m=$memoryinvocation{ toolname:$str; argsjson:$str; timestamp:$str; }
AFTER:  t=$memoryinvocation{ toolname:$str; argsjson:$str; timestamp:$str; };
```
**Fix:** `--migrate` should convert `m=$type{` → `t=$type{`.

### Pattern D: Type annotation on `if` expression (9 files)
```
BEFORE: let costin=if(str.contains(modelid;"claude-3-5-sonnet")):i64{ 0.003 }el{ 0.001 }
AFTER:  let costin=if(str.contains(modelid;"claude35sonnet")){ 0.003 }el{ 0.001 }
```
**Fix:** `--migrate` should strip `:type` between `)` and `{` in if expressions.

### Pattern E: Duplicate `m=` (8 files)
```
BEFORE: m=loke.platform.ui.shell;  (inserted by us)
        ...
        m=loke.platform.ui.shell;  (original in file)
```
**Fix:** Don't insert `m=` if file already contains one.

---

## Category 2: `expected '(' after '@', got '$'` — 59 files

### Pattern: `@$type@()` double-@ in expression
```
BEFORE: let results = @$result@();
AFTER:  let results = @($result);
```
**Fix:** `--migrate` produces `@$type@()` — should be `@($type)` for empty array constructor in expression position.

---

## Category 3: `missing semicolon` — 31 files

### Pattern A: `.each|var{` closure (11 files)
```
BEFORE: checks.each|c{ if(str.eq(c.status;"FAIL")){ result="FAIL" } }
AFTER:  (check if .each|binding{ is valid v3 — ooke uses this pattern)
```
**Fix:** Verify `.each|var{` is valid v3. If not, needs rewrite.

### Pattern B: `|` error union in return type (5 files)
```
BEFORE: f=find(...):$prompttemplate|$lokeerr{
AFTER:  f=find(...):$prompttemplate!$lokeerr{
```
**Fix:** `--migrate` should convert `|$errtype{` in return types to `!$errtype{`.

### Pattern C: `else if` chains (3 files)
```
BEFORE: if(cond){ expr }; else if(cond2){ expr2 }; else{ expr3 };
AFTER:  if(cond){ expr }el{ if(cond2){ expr2 }el{ expr3 } }
```
**Fix:** MANUAL — restructure as nested if/el.

### Pattern D: Bare field:type=value (3 files)
```
BEFORE: firstline:str="";
AFTER:  let firstline="";
```
**Fix:** `--migrate` should convert `name:type=expr` to `let name=expr` inside functions.

---

## Category 4: `expected ':', got '}'` — 31 files

### Pattern: Last enum variant missing `:i64`
```
BEFORE: t=$ollamastatus{ $running:i64; $stopped:i64; $unreachable\n};
AFTER:  t=$ollamastatus{ $running:i64; $stopped:i64; $unreachable:i64 };
```
**Fix:** `--migrate` adds `:i64` to `$var;` but misses last variant before `}` (has no `;`).

---

## Category 5: `expected field, got '$'` — 29 files

### Pattern: Module-prefixed struct literal in expression
```
BEFORE: let route=preg.$pluginroute{ method:"GET"; path:"/test" }
AFTER:  let route=$pluginroute{ method:"GET"; path:"/test" }
```
**Fix:** `--migrate` strips `mod.$type` in TYPE positions but not in EXPRESSION positions (struct constructors). Should strip module prefix from `mod.$type{` in expressions.

---

## Category 6: `unexpected token in expression, got '{'` — 19 files

### Pattern: Block `{...}` inside match arm
```
BEFORE: mt db.query(...) { $ok:rows { rows.each|row{ ... }; <result }; $err:e { <0 } }
AFTER:  mt db.query(...) { $ok:rows doquery(rows); $err:e 0 }
```
**Fix:** MANUAL — v3 match arms are single expressions, not blocks. Multi-statement arms need helper functions.

---

## Summary

| Fix type | Pattern | Files | Effort |
|----------|---------|-------|--------|
| `--migrate` | `}{` → `}el{` | 19 | Auto |
| `--migrate` | `@$type@()` → `@($type)` | 59 | Auto |
| `--migrate` | Last enum variant `:i64` | 31 | Auto |
| `--migrate` | `mod.$type{` in expr → `$type{` | 29 | Auto |
| `--migrate` | `m=$type{` → `t=$type{` | 6 | Auto |
| `--migrate` | `:type` after if() | 9 | Auto |
| `--migrate` | `\|$err` → `!$err` error union | 5 | Auto |
| `--migrate` | `name:type=expr` → `let name=expr` | 3 | Auto |
| `--migrate` | Duplicate m= removal | 8 | Auto |
| Manual | Top-level let | 21 | Rewrite |
| Manual | Match arm blocks | 19 | Rewrite |
| Manual | else if chains | 3 | Rewrite |
| N/A | `.each\|var{` (check if valid) | 11 | Verify |
| N/A | Module not found (link-time) | 19 | N/A |

**Automatable:** 169 files (30% of remaining)
**Manual rewrite:** 43 files (8%)
**Verify/N/A:** 30 files (5%)
**Already passing:** 43 + 19 link-time = 62 files (11%)
