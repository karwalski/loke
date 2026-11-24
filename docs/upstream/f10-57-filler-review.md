# F10.57 — review of F10.55's zero-filled `T!E` sites

**Story:** F10.57 in [`../epics-and-stories.md`](../epics-and-stories.md). **Reviewed:** 2026-11-24, at the
base commit `49dd5ca2` (line numbers below are that commit's; the fixes shift a few).

F10.55's mechanical pass (toke's `migrate_std_errunion.py`) rewrote every std `T!E` read as
`mt X{$ok:okv okv;$err:errv <zero>}`, which is exactly what toke 3.2.0 did silently on a failure.
This file classifies every one of those sites. The commit message says 283 sites; counting each
`{$ok:okv okv;$err:errv …}` occurrence (nested ones separately, e.g. `str.tof64(mt str.substr(…))`)
gives **288**, all listed.

- **(a) SAFE** — the failure cannot happen (bounds already checked, a number parsed from the text
  `str.fromint` just made), or the zero is already the code's own "absent / invalid / refuse" value.
- **(b) DEFECT** — a failure produced a value the code then used as valid.

## Counts

| class | sites | fixed | filed |
|---|---|---|---|
| (a) SAFE | 268 | — | — |
| (b) DEFECT | 20 | 10 (7 functions) | 10 (F10.60) |
| **total** | **288** | | |

## The defects fixed, each with a test on the production module, seen to fail on the base code

| site(s) | what went wrong | fix | test (RED on `49dd5ca2`, GREEN after) |
|---|---|---|---|
| `core/privacy/ner.tk:119` | an NER item with no string `value` became an entity with value `""`: a detection of nothing, handed to `str.replace` as the text to mask | the item is skipped | `tests/unit/privacy/test_ner_parse.tk` |
| `cli/proxy.tk:71` | `loke proxy --port 90x0` became port 0 (any free port, announced as `localhost:0`) | keeps the default port | `tests/unit/cli/test_proxy_opts.tk` (new) |
| `core/governance/rules_engine.tk:62,84,96` | a non-numeric comparand read as 0, so `sensitivity gt high` matched every request above 0 | the condition does not match, as an unknown op | `tests/unit/governance/test_rules_engine.tk` |
| `core/optimiser/llmlingua.tk:89` | an absent `compressed_tokens` read as 0 and the result claimed 100% savings | a zero count is "not reported"; no savings computed | `tests/unit/optimiser/test_llmlingua.tk` |
| `core/memory/privacy.tk:47,48` | a stored prefs document missing a field read as 0 days and `auto_forget_pii` false, where an unparsable one gives 365 / true | each missing field takes its default | `tests/unit/memory/test_privacy_prefs.tk` (new) |
| `core/mcp/client.tk:132` | a listed tool with no name was listed as `""` | skipped | `tests/unit/mcp/test_client_json.tk` |
| `core/installer/updater.tk:45` | a stored `installer.update_interval_days` that is not a number read as 0 days, so every `loke models` run was due a registry check | default 7, as for an absent key | `tests/unit/installer/test_update_interval.tk` (new) |

## The defects filed, not fixed (F10.60)

`core/companion/executor.tk:54-56`, `core/feedback/draft.tk:54,63,83`, `core/mcp/protocol.tk:49`,
`packages/browser/src/components/form.tk:52,55`. Reasons in the table; none of the first three
modules has a production importer except `core.mcp.protocol` (mcp-toke's server), whose fix needs
`$jsonrpcrequest.id` to carry the raw id; `packages/browser/src/` is outside this wave.

## Every site

| # | file:line (at 49dd5ca2) | call | filler | class | reason | action |
|---|---|---|---|---|---|---|
| 1 | `packages/browser/pages/api/approve.tk:76` | `json.str(…)` | `""` | a | "" is refused with 400 "approval_id is required" | left |
| 2 | `packages/browser/pages/api/approve.tk:84` | `json.str(…)` | `""` | a | "" is not approve/decline; respond() answers 400 | left |
| 3 | `packages/browser/pages/api/layermetrics.tk:48` | `str.slice(…)` | `""` | a | bounds from indexof/startswith; "" is not one of the four window names and get() refuses it | left |
| 4 | `packages/browser/pages/api/layermetrics.tk:52` | `str.slice(…)` | `""` | a | bounds from indexof/startswith; "" is not one of the four window names and get() refuses it | left |
| 5 | `packages/browser/pages/api/settings.tk:37` | `str.slice(…)` | `""` | a | len checked >=5 first | left |
| 6 | `packages/browser/pages/api/settings.tk:116` | `json.str(…)` | `""` | a | "" is "no key", masked to the default display | left |
| 7 | `packages/browser/src/components/form.tk:52` | `str.toint(…)` | `0` | b | a min_length/max_length rule whose value is not a number reads as 0: min passes any non-empty value, max fails all | FILED F10.60 (packages/browser/src is out of scope for this wave) |
| 8 | `packages/browser/src/components/form.tk:55` | `str.toint(…)` | `0` | b | a min_length/max_length rule whose value is not a number reads as 0: min passes any non-empty value, max fails all | FILED F10.60 (packages/browser/src is out of scope for this wave) |
| 9 | `packages/browser/src/components/form.tk:60` | `str.substr(…)` | `""` | a | slice after an `@` indexof found; "" fails the dot check, i.e. invalid | left |
| 10 | `packages/cli/src/code_profile.tk:63` | `str.slice(…)` | `""` | a | bounds from indexof of a character `str.contains` just found; cannot fail | left |
| 11 | `packages/cli/src/code_profile.tk:130` | `str.slice(…)` | `""` | a | bounds from indexof of a character `str.contains` just found; cannot fail | left |
| 12 | `packages/cli/src/code_profile.tk:131` | `str.slice(…)` | `""` | a | bounds from indexof of a character `str.contains` just found; cannot fail | left |
| 13 | `packages/cli/src/code_profile.tk:166` | `str.slice(…)` | `""` | a | bounds from indexof of a character `str.contains` just found; cannot fail | left |
| 14 | `packages/cli/src/code_profile.tk:168` | `str.slice(…)` | `""` | a | bounds from indexof of a character `str.contains` just found; cannot fail | left |
| 15 | `packages/cli/src/commands.tk:168` | `str.toint(…)` | `0` | a | isdigits: 0 round-trips only for "0", so a failure is "not digits" | left |
| 16 | `packages/cli/src/commands.tk:178` | `str.toint(…)` | `0` | a | guarded by length/isdigits; 0 is the function's own "not a date part" and is rejected by the n<1 / y<1970 checks | left |
| 17 | `packages/cli/src/commands.tk:186` | `str.toint(…)` | `0` | a | guarded by length/isdigits; 0 is the function's own "not a date part" and is rejected by the n<1 / y<1970 checks | left |
| 18 | `packages/cli/src/commands.tk:214` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 19 | `packages/cli/src/commands.tk:215` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 20 | `packages/cli/src/commands.tk:216` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 21 | `packages/cli/src/commands.tk:217` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 22 | `packages/cli/src/commands.tk:219` | `str.toint(…)` | `0` | a | guarded by length/isdigits; 0 is the function's own "not a date part" and is rejected by the n<1 / y<1970 checks | left |
| 23 | `packages/cli/src/commands.tk:223` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 24 | `packages/cli/src/commands.tk:224` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 25 | `packages/cli/src/commands.tk:225` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 26 | `packages/cli/src/commands.tk:246` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 27 | `packages/cli/src/commands.tk:246` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 28 | `packages/cli/src/commands.tk:247` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 29 | `packages/cli/src/commands.tk:248` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 30 | `packages/cli/src/commands.tk:250` | `str.slice(…)` | `""` | a | fixed offsets inside a string whose length was checked (7 or 10) | left |
| 31 | `packages/cli/src/commands.tk:251` | `str.toint(…)` | `0` | a | guarded by length/isdigits; 0 is the function's own "not a date part" and is rejected by the n<1 / y<1970 checks | left |
| 32 | `packages/cli/src/commands.tk:372` | `str.toint(…)` | `0` | a | isplaincount requires n>0 and a round-trip, so 0 is "not a count" | left |
| 33 | `packages/cli/src/commands.tk:416` | `str.toint(…)` | `0` | a | parsebenchmark already refused a non-numeric --runs; 0 is "use core.eval.bench's default" | left |
| 34 | `packages/cli/src/proxy.tk:71` | `str.toint(…)` | `0` | b | `loke proxy --port 90x0` became port 0: the OS picked any free port and the proxy announced `localhost:0` | FIXED: keeps the default port (tests/unit/cli/test_proxy_opts.tk) |
| 35 | `packages/cli/src/updater.tk:132` | `json.str(…)` | `""` | a | "" tag is never newer (versiongt) and empty notes are just empty | left |
| 36 | `packages/cli/src/updater.tk:133` | `json.str(…)` | `""` | a | "" tag is never newer (versiongt) and empty notes are just empty | left |
| 37 | `packages/cli/src/updater.tk:142` | `json.str(…)` | `""` | a | "" name matches no platform asset; "" url means no download, refused downstream | left |
| 38 | `packages/cli/src/updater.tk:143` | `json.str(…)` | `""` | a | "" name matches no platform asset; "" url means no download, refused downstream | left |
| 39 | `packages/cli/src/updater.tk:232` | `str.toint(…)` | `0` | a | 0 is nowsecs's own "unknown" (it already answers 0 for empty output) | left |
| 40 | `packages/cli/src/updater.tk:251` | `str.toint(…)` | `0` | a | corrupt snooze reads as expired: the prompt shows, nothing is skipped | left |
| 41 | `packages/cli/src/updater.tk:271` | `str.toint(…)` | `0` | a | version parts; 0 is never newer than a real part, so a malformed tag is not an update | left |
| 42 | `packages/cli/src/updater.tk:272` | `str.toint(…)` | `0` | a | version parts; 0 is never newer than a real part, so a malformed tag is not an update | left |
| 43 | `packages/cli/src/updater.tk:275` | `str.toint(…)` | `0` | a | version parts; 0 is never newer than a real part, so a malformed tag is not an update | left |
| 44 | `packages/cli/src/updater.tk:276` | `str.toint(…)` | `0` | a | version parts; 0 is never newer than a real part, so a malformed tag is not an update | left |
| 45 | `packages/cli/src/updater.tk:279` | `str.toint(…)` | `0` | a | version parts; 0 is never newer than a real part, so a malformed tag is not an update | left |
| 46 | `packages/cli/src/updater.tk:279` | `str.toint(…)` | `0` | a | version parts; 0 is never newer than a real part, so a malformed tag is not an update | left |
| 47 | `packages/core/src/a11y/colour.tk:56` | `str.slice(…)` | `""` | a | after a startswith check / hexdigit-validated length 3; cannot fail | left |
| 48 | `packages/core/src/a11y/colour.tk:63` | `str.slice(…)` | `""` | a | after a startswith check / hexdigit-validated length 3; cannot fail | left |
| 49 | `packages/core/src/a11y/colour.tk:64` | `str.slice(…)` | `""` | a | after a startswith check / hexdigit-validated length 3; cannot fail | left |
| 50 | `packages/core/src/a11y/colour.tk:65` | `str.slice(…)` | `""` | a | after a startswith check / hexdigit-validated length 3; cannot fail | left |
| 51 | `packages/core/src/a11y/testing.tk:56` | `str.slice(…)` | `""` | a | bounds from indexof results already checked >=0; cannot fail | left |
| 52 | `packages/core/src/a11y/testing.tk:77` | `str.slice(…)` | `""` | a | bounds from indexof results already checked >=0; cannot fail | left |
| 53 | `packages/core/src/a11y/testing.tk:80` | `str.slice(…)` | `""` | a | bounds from indexof results already checked >=0; cannot fail | left |
| 54 | `packages/core/src/a11y/testing.tk:87` | `str.slice(…)` | `""` | a | bounds from indexof results already checked >=0; cannot fail | left |
| 55 | `packages/core/src/audit/layer_metrics.tk:159` | `str.slice(…)` | `""` | a | at>=0 from indexof; cannot fail | left |
| 56 | `packages/core/src/companion/executor.tk:54` | `json.str(…)` | `""` | b | parseremoteresponse answers ok:true with text "" for a reply carrying an error or no text (module has no production importer) | FILED F10.60 |
| 57 | `packages/core/src/companion/executor.tk:55` | `json.i64(…)` | `0` | b | parseremoteresponse answers ok:true with text "" for a reply carrying an error or no text (module has no production importer) | FILED F10.60 |
| 58 | `packages/core/src/companion/executor.tk:56` | `json.i64(…)` | `0` | b | parseremoteresponse answers ok:true with text "" for a reply carrying an error or no text (module has no production importer) | FILED F10.60 |
| 59 | `packages/core/src/companion/exo.tk:94` | `json.str(…)` | `""` | a | node id/device are display labels of a discovered cluster; "" is shown as blank (no production importer) | left |
| 60 | `packages/core/src/companion/exo.tk:94` | `json.str(…)` | `""` | a | node id/device are display labels of a discovered cluster; "" is shown as blank (no production importer) | left |
| 61 | `packages/core/src/eval/bench.tk:127` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 62 | `packages/core/src/eval/bench.tk:127` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 63 | `packages/core/src/eval/interval.tk:264` | `str.slice(…)` | `""` | a | slice of a 7-digit number it just built; cannot fail | left |
| 64 | `packages/core/src/feedback/draft.tk:49` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 65 | `packages/core/src/feedback/draft.tk:51` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 66 | `packages/core/src/feedback/draft.tk:52` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 67 | `packages/core/src/feedback/draft.tk:54` | `str.slice(…)` | `""` | b | an unterminated title/body becomes "" instead of the "Untitled issue"/"" default path | FILED F10.60 |
| 68 | `packages/core/src/feedback/draft.tk:58` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 69 | `packages/core/src/feedback/draft.tk:60` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 70 | `packages/core/src/feedback/draft.tk:61` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 71 | `packages/core/src/feedback/draft.tk:63` | `str.slice(…)` | `""` | b | an unterminated title/body becomes "" instead of the "Untitled issue"/"" default path | FILED F10.60 |
| 72 | `packages/core/src/feedback/draft.tk:81` | `str.slice(…)` | `""` | a | bounds from indexof of a key `str.contains` just found; a failure yields "" which the next step treats as not found | left |
| 73 | `packages/core/src/feedback/draft.tk:83` | `str.slice(…)` | `""` | b | confidence reads 0.0 when the value lies within 9 characters of the end or is followed by `}`/`,` (hand-rolled JSON; no production importer) | FILED F10.60 |
| 74 | `packages/core/src/feedback/draft.tk:83` | `str.tof64(…)` | `0.0` | b | confidence reads 0.0 when the value lies within 9 characters of the end or is followed by `}`/`,` (hand-rolled JSON; no production importer) | FILED F10.60 |
| 75 | `packages/core/src/feedback/learning.tk:59` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 76 | `packages/core/src/feedback/learning.tk:59` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 77 | `packages/core/src/feedback/learning.tk:327` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 78 | `packages/core/src/feedback/store.tk:67` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 79 | `packages/core/src/feedback/store.tk:67` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 80 | `packages/core/src/governance/ai_gov.tk:166` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 81 | `packages/core/src/governance/dashboard.tk:166` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 82 | `packages/core/src/governance/dashboard.tk:179` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 83 | `packages/core/src/governance/dashboard.tk:183` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 84 | `packages/core/src/governance/forecast.tk:27` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 85 | `packages/core/src/governance/forecast.tk:44` | `str.toint(…)` | `0` | a | toint of a fromfloat result; test_forecast asserts 18390 and 141, so it parses | left |
| 86 | `packages/core/src/governance/forecast.tk:45` | `str.toint(…)` | `0` | a | toint of a fromfloat result; test_forecast asserts 18390 and 141, so it parses | left |
| 87 | `packages/core/src/governance/kill_switch.tk:48` | `str.toint(…)` | `0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 88 | `packages/core/src/governance/monitoring.tk:105` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 89 | `packages/core/src/governance/monitoring.tk:106` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 90 | `packages/core/src/governance/quota.tk:115` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 91 | `packages/core/src/governance/quota.tk:115` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 92 | `packages/core/src/governance/rules_engine.tk:62` | `str.toint(…)` | `0` | b | a non-numeric comparand read as 0, so `sensitivity gt high` matched every request above 0 | FIXED: condition does not match, as an unknown op (test_rules_engine) |
| 93 | `packages/core/src/governance/rules_engine.tk:84` | `str.toint(…)` | `0` | b | a non-numeric comparand read as 0, so `sensitivity gt high` matched every request above 0 | FIXED: condition does not match, as an unknown op (test_rules_engine) |
| 94 | `packages/core/src/governance/rules_engine.tk:96` | `str.toint(…)` | `0` | b | a non-numeric comparand read as 0, so `sensitivity gt high` matched every request above 0 | FIXED: condition does not match, as an unknown op (test_rules_engine) |
| 95 | `packages/core/src/governance/value.tk:43` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 96 | `packages/core/src/governance/value.tk:44` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 97 | `packages/core/src/governance/value.tk:63` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 98 | `packages/core/src/governance/value.tk:64` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 99 | `packages/core/src/governance/value.tk:133` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 100 | `packages/core/src/governance/value.tk:134` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 101 | `packages/core/src/governance/value.tk:143` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 102 | `packages/core/src/i18n/layout.tk:31` | `str.slice(…)` | `""` | a | dash/under >0 from indexof; cannot fail | left |
| 103 | `packages/core/src/i18n/layout.tk:32` | `str.slice(…)` | `""` | a | dash/under >0 from indexof; cannot fail | left |
| 104 | `packages/core/src/installer/models.tk:115` | `str.tof64(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 105 | `packages/core/src/installer/pull.tk:132` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 106 | `packages/core/src/installer/pull.tk:132` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 107 | `packages/core/src/installer/pull.tk:135` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 108 | `packages/core/src/installer/pull.tk:135` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 109 | `packages/core/src/installer/pull.tk:148` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 110 | `packages/core/src/installer/pull.tk:149` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 111 | `packages/core/src/installer/pull.tk:155` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 112 | `packages/core/src/installer/pull.tk:156` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 113 | `packages/core/src/installer/pull.tk:157` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 114 | `packages/core/src/installer/pull.tk:158` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 115 | `packages/core/src/installer/pull.tk:163` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 116 | `packages/core/src/installer/pull.tk:164` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 117 | `packages/core/src/installer/pull.tk:165` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 118 | `packages/core/src/installer/pull.tk:166` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 119 | `packages/core/src/installer/pull.tk:174` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 120 | `packages/core/src/installer/pull.tk:175` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 121 | `packages/core/src/installer/pull.tk:181` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 122 | `packages/core/src/installer/pull.tk:182` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 123 | `packages/core/src/installer/pull.tk:183` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 124 | `packages/core/src/installer/pull.tk:184` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 125 | `packages/core/src/installer/pull.tk:189` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 126 | `packages/core/src/installer/pull.tk:190` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 127 | `packages/core/src/installer/pull.tk:191` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 128 | `packages/core/src/installer/pull.tk:192` | `str.tof64(…)` | `0.0` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 129 | `packages/core/src/installer/pull.tk:208` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 130 | `packages/core/src/installer/pull.tk:213` | `str.substr(…)` | `""` | a | ollama pull progress display only; digit-run bounds, and 0 is "no progress known" | left |
| 131 | `packages/core/src/installer/updater.tk:45` | `str.toint(…)` | `0` | b | a stored `installer.update_interval_days` that is not a number read as 0 days: every `loke models` run was due a registry check (cli.modelmgmt imports it) | FIXED: default 7, as an absent key (tests/unit/installer/test_update_interval.tk) |
| 132 | `packages/core/src/installer/updater.tk:53` | `str.toint(…)` | `0` | a | corrupt last-check time reads as epoch, so a check is due: the conservative answer | left |
| 133 | `packages/core/src/mcp/client.tk:132` | `json.str(…)` | `""` | b | a listed tool with no name was listed with name "" | FIXED: skipped (test_client_json) |
| 134 | `packages/core/src/mcp/client.tk:133` | `json.str(…)` | `""` | a | description/text "" is an empty description or an empty content part, not a substitute for a value | left |
| 135 | `packages/core/src/mcp/client.tk:168` | `json.str(…)` | `""` | a | description/text "" is an empty description or an empty content part, not a substitute for a value | left |
| 136 | `packages/core/src/mcp/protocol.tk:49` | `json.i64(…)` | `0` | b | a JSON-RPC id that is a string or absent (a notification) reads as 0 and is answered as id 0 (mcp-toke server) | FILED F10.60 (needs $jsonrpcrequest.id to carry the raw id) |
| 137 | `packages/core/src/mcp/protocol.tk:50` | `json.str(…)` | `""` | a | method "" is an unknown method, answered with the JSON-RPC error | left |
| 138 | `packages/core/src/memory/privacy.tk:47` | `json.i64(…)` | `0` | b | a stored prefs document missing the field read as 0 days / auto_forget_pii false; an unparsable one gives the defaults 365 / true | FIXED: per-field default (tests/unit/memory/test_privacy_prefs.tk) |
| 139 | `packages/core/src/memory/privacy.tk:48` | `json.bool(…)` | `false` | b | a stored prefs document missing the field read as 0 days / auto_forget_pii false; an unparsable one gives the defaults 365 / true | FIXED: per-field default (tests/unit/memory/test_privacy_prefs.tk) |
| 140 | `packages/core/src/memory/privacy.tk:49` | `json.bool(…)` | `false` | a | zero is false, which is the default; now taken from defaultprivacyprefs() with its neighbours | left |
| 141 | `packages/core/src/models/queue.tk:245` | `str.slice(…)` | `""` | a | fixed-width slice of a string padded past that width; cannot fail | left |
| 142 | `packages/core/src/models/queue.tk:246` | `str.slice(…)` | `""` | a | fixed-width slice of a string padded past that width; cannot fail | left |
| 143 | `packages/core/src/models/queue.tk:247` | `str.slice(…)` | `""` | a | fixed-width slice of a string padded past that width; cannot fail | left |
| 144 | `packages/core/src/monitoring/sysmon.tk:95` | `str.slice(…)` | `""` | a | bounds checked (endswith ".", end>0); cannot fail | left |
| 145 | `packages/core/src/monitoring/sysmon.tk:235` | `str.slice(…)` | `""` | a | bounds checked (endswith ".", end>0); cannot fail | left |
| 146 | `packages/core/src/optimiser/llmlingua.tk:89` | `str.toint(…)` | `0` | b | an absent `compressed_tokens` read as 0 and `buildcompressresult` claimed 100% savings (a figure) | FIXED: zero count is "not reported", no savings computed (test_llmlingua) |
| 147 | `packages/core/src/optimiser/profiler.tk:90` | `str.slice(…)` | `""` | a | length checked (==10, len>0) first; cannot fail | left |
| 148 | `packages/core/src/optimiser/profiler.tk:91` | `str.slice(…)` | `""` | a | length checked (==10, len>0) first; cannot fail | left |
| 149 | `packages/core/src/optimiser/profiler.tk:374` | `str.slice(…)` | `""` | a | length checked (==10, len>0) first; cannot fail | left |
| 150 | `packages/core/src/optimiser/toon.tk:70` | `str.slice(…)` | `""` | a | bounds from indexof/len checks; "" for an empty remainder is the right answer | left |
| 151 | `packages/core/src/optimiser/toon.tk:283` | `str.slice(…)` | `""` | a | bounds from indexof/len checks; "" for an empty remainder is the right answer | left |
| 152 | `packages/core/src/optimiser/toon.tk:313` | `str.slice(…)` | `""` | a | bounds from indexof/len checks; "" for an empty remainder is the right answer | left |
| 153 | `packages/core/src/optimiser/toon.tk:314` | `str.slice(…)` | `""` | a | bounds from indexof/len checks; "" for an empty remainder is the right answer | left |
| 154 | `packages/core/src/optimiser/toon.tk:315` | `str.slice(…)` | `""` | a | bounds from indexof/len checks; "" for an empty remainder is the right answer | left |
| 155 | `packages/core/src/policy/feedback.tk:87` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 156 | `packages/core/src/policy/feedback.tk:87` | `str.tofloat(…)` | `0.0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 157 | `packages/core/src/privacy/comparison.tk:366` | `str.slice(…)` | `""` | a | eq>0 from indexof; cannot fail | left |
| 158 | `packages/core/src/privacy/consensus.tk:89` | `str.tof64(…)` | `0.0` | a | a non-numeric threshold reads 0.0, which masks every group: fails closed (the module's stated rule) | left |
| 159 | `packages/core/src/privacy/evaluation.tk:419` | `json.bool(…)` | `false` | a | a labelled item without expected_detected is not a scored item; excluded only under --scored-only | left |
| 160 | `packages/core/src/privacy/evaluation.tk:462` | `str.slice(…)` | `""` | a | from<n loop bound; cannot fail | left |
| 161 | `packages/core/src/privacy/ner.tk:116` | `json.str(…)` | `""` | a | type "" only labels; the item is now dropped unless it has a value (line 119) | left |
| 162 | `packages/core/src/privacy/ner.tk:119` | `json.str(…)` | `""` | b | an NER item with no string `value` became an entity with value "": counted as a detection and handed to `str.replace` as the text to mask | FIXED: item skipped (test_ner_parse) |
| 163 | `packages/core/src/privacy/ner.tk:140` | `json.str(…)` | `""` | a | "" content parses to zero entities, the same as an empty reply; the layer still reports `ok` only after a real /api/chat answer | left |
| 164 | `packages/core/src/privacy/placeholder.tk:77` | `str.substr(…)` | `""` | a | len>=4 checked first; cannot fail | left |
| 165 | `packages/core/src/privacy/presidio.tk:80` | `json.str(…)` | `""` | a | type "" maps to no loke type downstream; Presidio always sends entity_type | left |
| 166 | `packages/core/src/privacy/presidio.tk:81` | `json.i64(…)` | `0` | a | a missing start/end gives an empty or inverted span, which presidio.place cannot place (counted unplaced), never a mask of the wrong text | left |
| 167 | `packages/core/src/privacy/presidio.tk:82` | `json.i64(…)` | `0` | a | a missing start/end gives an empty or inverted span, which presidio.place cannot place (counted unplaced), never a mask of the wrong text | left |
| 168 | `packages/core/src/privacy/regex.tk:152` | `str.substr(…)` | `""` | a | i<len loop bound; cannot fail | left |
| 169 | `packages/core/src/privacy/regex.tk:176` | `str.substr(…)` | `""` | a | i<len loop bound; cannot fail | left |
| 170 | `packages/core/src/privacy/regex.tk:280` | `str.substr(…)` | `""` | a | i<len loop bound; cannot fail | left |
| 171 | `packages/core/src/privacy/regex.tk:308` | `str.substr(…)` | `""` | a | length checked ==9 first; cannot fail | left |
| 172 | `packages/core/src/privacy/regex.tk:309` | `str.substr(…)` | `""` | a | length checked ==9 first; cannot fail | left |
| 173 | `packages/core/src/privacy/regex.tk:310` | `str.substr(…)` | `""` | a | length checked ==9 first; cannot fail | left |
| 174 | `packages/core/src/privacy/regex.tk:463` | `str.substr(…)` | `""` | a | from<hi<=textlen; cannot fail | left |
| 175 | `packages/core/src/privacy/regex.tk:505` | `str.substr(…)` | `""` | a | contextstart answers 0..len; cannot fail | left |
| 176 | `packages/core/src/privacy/sidecar_client.tk:118` | `str.slice(…)` | `""` | a | end in 0..len; cannot fail | left |
| 177 | `packages/core/src/privacy/sidecar_client.tk:159` | `str.toint(…)` | `0` | a | diagnostic counts reported alongside the hits; never used to decide masking | left |
| 178 | `packages/core/src/privacy/sidecar_client.tk:160` | `str.toint(…)` | `0` | a | diagnostic counts reported alongside the hits; never used to decide masking | left |
| 179 | `packages/core/src/privacy/template.tk:208` | `json.str(…)` | `""` | a | "" is "parameter absent", and a required one is refused on that path | left |
| 180 | `packages/core/src/providers/anthropic.tk:113` | `json.str(…)` | `""` | a | modelid "" is the module's failure sentinel: providers.types.iscompletion is str.len(modelid)>0, so a reply without model is an error | left |
| 181 | `packages/core/src/providers/openai.tk:179` | `json.str(…)` | `""` | a | modelid "" is the module's failure sentinel: providers.types.iscompletion is str.len(modelid)>0, so a reply without model is an error | left |
| 182 | `packages/core/src/router/intent.tk:256` | `json.str(…)` | `""` | a | "" content falls back to the keyword classification (fast) | left |
| 183 | `packages/core/src/storage/audit.tk:195` | `str.slice(…)` | `""` | a | at>=1 from a scan; tail checked isdigit; cannot fail | left |
| 184 | `packages/core/src/storage/audit.tk:197` | `str.slice(…)` | `""` | a | at>=1 from a scan; tail checked isdigit; cannot fail | left |
| 185 | `packages/core/src/storage/dashboard.tk:74` | `json.str(…)` | `""` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 186 | `packages/core/src/storage/dashboard.tk:75` | `json.bool(…)` | `false` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 187 | `packages/core/src/storage/dashboard.tk:76` | `json.str(…)` | `""` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 188 | `packages/core/src/storage/dashboard.tk:77` | `json.str(…)` | `""` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 189 | `packages/core/src/storage/dashboard.tk:78` | `json.i64(…)` | `0` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 190 | `packages/core/src/storage/dashboard.tk:83` | `json.str(…)` | `""` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 191 | `packages/core/src/storage/dashboard.tk:84` | `json.bool(…)` | `false` | a | UI layout preferences; "" / false / 0 are the blank defaults of a widget (no production importer) | left |
| 192 | `packages/core/src/storage/db.tk:580` | `row.str(…)` | `""` | a | row accessor helpers whose contract is zero for an absent or NULL column (as rowi32 beside them always was); presence is checked by callers | left |
| 193 | `packages/core/src/storage/db.tk:584` | `row.i64(…)` | `0` | a | row accessor helpers whose contract is zero for an absent or NULL column (as rowi32 beside them always was); presence is checked by callers | left |
| 194 | `packages/core/src/storage/db.tk:592` | `row.bool(…)` | `false` | a | row accessor helpers whose contract is zero for an absent or NULL column (as rowi32 beside them always was); presence is checked by callers | left |
| 195 | `packages/core/src/storage/db.tk:615` | `str.tofloat(…)` | `0.0` | a | text of a REAL column written by loke; "" is handled above as 0, the column's own default | left |
| 196 | `packages/core/src/storage/ephemeral.tk:54` | `str.slice(…)` | `""` | a | len>=3 checked first; cannot fail | left |
| 197 | `packages/core/src/update/checker.tk:50` | `json.str(…)` | `""` | a | "" tag is never newer (isnewer), so no update is offered; url/notes "" are empty | left |
| 198 | `packages/core/src/update/checker.tk:53` | `tag.slice(…)` | `""` | a | "" tag is never newer (isnewer), so no update is offered; url/notes "" are empty | left |
| 199 | `packages/core/src/update/checker.tk:55` | `json.str(…)` | `""` | a | "" tag is never newer (isnewer), so no update is offered; url/notes "" are empty | left |
| 200 | `packages/core/src/update/checker.tk:56` | `json.str(…)` | `""` | a | "" tag is never newer (isnewer), so no update is offered; url/notes "" are empty | left |
| 201 | `packages/core/src/update/checker.tk:84` | `str.toint(…)` | `0` | a | cannot fail: parses the text `str.fromint`/`str.fromfloat` just produced | left |
| 202 | `packages/core/src/update/checker.tk:91` | `str.toint(…)` | `0` | a | corrupt cache time reads as epoch: the cache is stale and a fresh check runs | left |
| 203 | `packages/core/src/update/checker.tk:145` | `str.toint(…)` | `0` | a | version parts; 0 is never newer, so a malformed tag is not an update | left |
| 204 | `packages/core/src/update/checker.tk:146` | `str.toint(…)` | `0` | a | version parts; 0 is never newer, so a malformed tag is not an update | left |
| 205 | `packages/core/src/update/checker.tk:153` | `str.toint(…)` | `0` | a | version parts; 0 is never newer, so a malformed tag is not an update | left |
| 206 | `packages/core/src/update/checker.tk:154` | `str.toint(…)` | `0` | a | version parts; 0 is never newer, so a malformed tag is not an update | left |
| 207 | `packages/core/src/update/checker.tk:161` | `str.toint(…)` | `0` | a | version parts; 0 is never newer, so a malformed tag is not an update | left |
| 208 | `packages/core/src/update/checker.tk:162` | `str.toint(…)` | `0` | a | version parts; 0 is never newer, so a malformed tag is not an update | left |
| 209 | `packages/core/src/util/strings.tk:10` | `str.substr(…)` | `""` | a | a short input slices to "", which is "no prefix/suffix" - the right answer; 39 masks more, not less | left |
| 210 | `packages/core/src/util/strings.tk:17` | `str.substr(…)` | `""` | a | a short input slices to "", which is "no prefix/suffix" - the right answer; 39 masks more, not less | left |
| 211 | `packages/core/src/util/strings.tk:24` | `str.substr(…)` | `""` | a | a short input slices to "", which is "no prefix/suffix" - the right answer; 39 masks more, not less | left |
| 212 | `packages/core/src/util/strings.tk:24` | `str.substr(…)` | `""` | a | a short input slices to "", which is "no prefix/suffix" - the right answer; 39 masks more, not less | left |
| 213 | `packages/core/src/util/strings.tk:39` | `str.substr(…)` | `""` | a | a short input slices to "", which is "no prefix/suffix" - the right answer; 39 masks more, not less | left |
| 214 | `packages/mcp-broker/src/permissions.tk:57` | `str.slice(…)` | `""` | a | startswith(prefix) checked first; cannot fail | left |
| 215 | `packages/mcp-broker/src/permissions.tk:125` | `str.slice(…)` | `""` | a | endbracket>13 checked; cannot fail | left |
| 216 | `packages/mcp-broker/src/permissions.tk:172` | `str.slice(…)` | `""` | a | bracketend>bracketstart checked; cannot fail | left |
| 217 | `packages/mcp-broker/src/permissions.tk:176` | `str.slice(…)` | `""` | a | a lone `"` slices to "", which is skipped (len>0 check) | left |
| 218 | `packages/mcp-broker/src/permissions.tk:189` | `str.slice(…)` | `""` | a | eqpos>=0 checked; the slice cannot fail (the str.toint around 189 is W126's) | left |
| 219 | `packages/mcp-broker/src/permissions.tk:196` | `str.slice(…)` | `""` | a | eqpos>=0 checked; the slice cannot fail (the str.toint around 189 is W126's) | left |
| 220 | `packages/mcp-broker/src/proxy.tk:45` | `str.slice(…)` | `""` | a | startswith(prefix) checked first; cannot fail | left |
| 221 | `packages/mcp-broker/src/server.tk:106` | `str.slice(…)` | `""` | a | at>=0 from indexof; cannot fail | left |
| 222 | `packages/shared/src/origin.tk:33` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 223 | `packages/shared/src/origin.tk:42` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 224 | `packages/shared/src/origin.tk:50` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 225 | `packages/shared/src/origin.tk:53` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 226 | `packages/shared/src/origin.tk:56` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 227 | `packages/shared/src/origin.tk:75` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 228 | `packages/shared/src/origin.tk:76` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 229 | `packages/shared/src/origin.tk:77` | `str.slice(…)` | `""` | a | every slice follows a startswith of at least its offset, or k<n; cannot fail, so the origin/host decision never sees a filler | left |
| 230 | `packages/shared/src/reachability.tk:31` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0; cannot fail | left |
| 231 | `packages/shared/src/reachability.tk:42` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0; cannot fail | left |
| 232 | `packages/shared/src/reachability.tk:46` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0; cannot fail | left |
| 233 | `packages/shared/src/reachability.tk:48` | `str.toint(…)` | `0` | a | a non-numeric port reads 0; localserviceup then answers DOWN (a bind on 0 succeeds and nc to port 0 fails), the fail-closed answer | left |
| 234 | `packages/shared/src/reachability.tk:61` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0; cannot fail | left |
| 235 | `packages/shared/src/reachability.tk:65` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0; cannot fail | left |
| 236 | `packages/shared/src/reachability.tk:74` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0; cannot fail | left |
| 237 | `packages/shared/src/types.tk:184` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 238 | `packages/shared/src/types.tk:188` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 239 | `packages/shared/src/types.tk:189` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 240 | `packages/shared/src/types.tk:201` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 241 | `packages/shared/src/types.tk:206` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 242 | `packages/shared/src/types.tk:220` | `str.slice(…)` | `""` | a | strslice: shared helper whose contract is "" for an out-of-range slice; its callers bound-check | left |
| 243 | `packages/shared/src/types.tk:299` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 244 | `packages/shared/src/types.tk:382` | `str.slice(…)` | `""` | a | bounds from indexof results checked >=0, or n>=2; cannot fail | left |
| 245 | `packages/shared/src/utf8.tk:41` | `str.slice(…)` | `""` | a | boundary answers 0..limit<len; cannot fail | left |
| 246 | `tests/integration/test_browser_fallback.tk:233` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 247 | `tests/integration/test_cut_body.tk:103` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 248 | `tests/integration/test_degrade_local.tk:239` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 249 | `tests/integration/test_hop_facts_parity.tk:207` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 250 | `tests/integration/test_keychain_e2e.tk:58` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 251 | `tests/integration/test_local_gets_broker.tk:70` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 252 | `tests/integration/test_local_gets_broker.tk:72` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 253 | `tests/integration/test_local_posts.tk:111` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 254 | `tests/integration/test_local_posts.tk:119` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 255 | `tests/integration/test_local_posts_broker.tk:62` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 256 | `tests/unit/browser/test_evaluate_handler.tk:68` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 257 | `tests/unit/browser/test_evaluate_handler.tk:71` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 258 | `tests/unit/browser/test_evaluate_handler.tk:150` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 259 | `tests/unit/browser/test_installer_page.tk:25` | `json.i64(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 260 | `tests/unit/governance/test_trace_truncate.tk:78` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 261 | `tests/unit/mcp_broker/test_broker_args.tk:82` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 262 | `tests/unit/mcp_broker/test_proxy_json.tk:92` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 263 | `tests/unit/mcp_broker/test_server_args.tk:64` | `str.toint(…)` | `0` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 264 | `tests/unit/mcp_toke/test_anonymise_destination.tk:106` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 265 | `tests/unit/mcp_toke/test_privacy_tools.tk:71` | `str.slice(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 266 | `tests/unit/nocustody/test_limits.tk:55` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 267 | `tests/unit/nocustody/test_limits.tk:56` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 268 | `tests/unit/nocustody/test_policy_limits.tk:59` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 269 | `tests/unit/nocustody/test_policy_limits.tk:60` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 270 | `tests/unit/privacy/test_entity_routing_pipeline.tk:111` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 271 | `tests/unit/privacy/test_entity_routing_pipeline.tk:112` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 272 | `tests/unit/privacy/test_layer_config_pipeline.tk:132` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 273 | `tests/unit/privacy/test_layer_config_pipeline.tk:133` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 274 | `tests/unit/privacy/test_ner_parse.tk:30` | `c(…)` | `@()` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 275 | `tests/unit/privacy/test_ner_parse.tk:44` | `r(…)` | `@()` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 276 | `tests/unit/privacy/test_ner_parse.tk:48` | `none(…)` | `@()` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 277 | `tests/unit/privacy/test_org_policy.tk:34` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 278 | `tests/unit/privacy/test_org_policy.tk:35` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 279 | `tests/unit/privacy/test_org_policy_callers.tk:57` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 280 | `tests/unit/privacy/test_org_policy_callers.tk:58` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 281 | `tests/unit/privacy/test_org_policy_pipeline.tk:130` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 282 | `tests/unit/privacy/test_org_policy_pipeline.tk:131` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 283 | `tests/unit/privacy/test_pipeline.tk:119` | `str.substr(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 284 | `tests/unit/privacy/test_placeholder_store.tk:69` | `str.substr(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 285 | `tests/unit/privacy/test_placeholder_store.tk:70` | `str.substr(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 286 | `tests/unit/privacy/test_regex_spans.tk:51` | `str.substr(…)` | `""` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 287 | `tests/unit/shared/test_config_loaded.tk:30` | `file.mkdir(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
| 288 | `tests/unit/shared/test_config_loaded.tk:31` | `file.write(…)` | `false` | a | test code: a failure fails the test loudly (no port, no prefix, a false write the test asserts) | left |
