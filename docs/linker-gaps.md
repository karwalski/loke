# Linker Gaps — loke build (2026-05-16)

loke compiles all 172 modules to LLVM IR cleanly. Individual `.ll` → `.o` succeeds. The linker fails with 150+ undefined symbols due to **naming mismatches** between what toke's codegen emits and what the C stdlib glue provides.

## Root Cause

toke's codegen emits wrapper calls like `@tk_str_fromu16_w(i64)` but the C glue only has `tk_str_fromi64_w(int64_t)`. Since all toke values are i64 at the ABI level, `str.fromu16(n)` and `str.fromi64(n)` should produce the same C call — but the codegen creates unique symbol names per source-level function name.

## Recommended Fix (in toke)

**Option A — Alias mapping in codegen:** When emitting stdlib calls, map source-level function names to canonical C glue names:
- `str.fromu16` / `str.fromu32` / `str.fromu64` / `str.fromint64` → all emit `@tk_str_fromi64_w`
- `str.fromi32` → `@tk_str_fromi64_w`
- `str.hexid` / `str.randhex` → `@tk_crypto_randomhex_w`
- `str.nowiso8601` / `str.nowunix` → `@tk_time_nowiso8601_w` / `@tk_time_nowunix_w`

**Option B — Thin C aliases:** Add one-line wrappers in the glue for each variant name:
```c
int64_t tk_str_fromu16_w(int64_t n) { return tk_str_fromi64_w(n); }
int64_t tk_str_fromu32_w(int64_t n) { return tk_str_fromi64_w(n); }
```

Option A is cleaner (no code bloat). Option B is quicker.

## Full Symbol List (grouped by module)

### str (45 missing)
| Emitted symbol | Probable alias target |
|---|---|
| `tk_str_fromu16_w` | `tk_str_fromi64_w` |
| `tk_str_fromu32_w` | `tk_str_fromi64_w` |
| `tk_str_fromu64_w` | `tk_str_fromi64_w` |
| `tk_str_fromint64_w` | `tk_str_fromi64_w` |
| `tk_str_fromi32_w` | `tk_str_fromi64_w` |
| `tk_str_frombool_w` | new (return "true"/"false") |
| `tk_str_fromf32_w` | `tk_str_fromfloat_w` |
| `tk_str_hexid_w` | `tk_crypto_randomhex_w` or new |
| `tk_str_randhex_w` | `tk_crypto_randomhex_w` |
| `tk_str_between_w` | new (extract between delimiters) |
| `tk_str_bytelen_w` | `tk_str_len_w` |
| `tk_str_compare_w` | new (strcmp wrapper) |
| `tk_str_containsignorecase_w` | new |
| `tk_str_countre_w` | new (regex count) |
| `tk_str_findall_w` | new (regex findall) |
| `tk_str_isdigit_w` | new |
| `tk_str_lastindexof_w` | `tk_str_lastindex_w` (exists!) |
| `tk_str_matches_w` | new (regex match) |
| `tk_str_nowiso8601_w` | move to time module |
| `tk_str_nowunix_w` | move to time module |
| `tk_str_pad_w` | `tk_str_padright_w` (exists!) |
| `tk_str_parsefloat_w` | `tk_str_tofloat_w` (exists!) |
| `tk_str_parseint_w` | `tk_str_toint_w` (exists!) |
| `tk_str_replaceall_w` | `tk_str_replace_w` (exists!) |
| `tk_str_replacere_w` | new (regex replace) |
| `tk_str_sha256prefix_w` | new |
| `tk_str_splitfirst_w` | new |
| `tk_str_splitwhitespace_w` | new |
| `tk_str_strip_w` | `tk_str_trim_w` (exists!) |
| `tk_str_tof64_w` | `tk_str_tofloat_w` (exists!) |
| `tk_str_toi32_w` | `tk_str_toint_w` (exists!) |
| `tk_str_toi64_w` | `tk_str_toint_w` (exists!) |
| `tk_str_toint64_w` | `tk_str_toint_w` (exists!) |
| `tk_str_trimws_w` | `tk_str_trim_w` (exists!) |
| `tk_str_wordcount_w` | new |
| `tk_string_arrayget_w` | `tk_str_arrayget_w` (exists!) |
| `tk_string_arraylen_w` | `tk_str_arraylen_w` (exists!) |
| `tk_string_charat_w` | `tk_str_charat_w` (exists!) |
| `tk_string_concat_w` | `tk_str_concat_w` (exists!) |
| `tk_string_contains_w` | `tk_str_contains_w` (exists!) |
| `tk_string_fromi32_w` | `tk_str_fromi64_w` |
| `tk_string_fromi64_w` | `tk_str_fromi64_w` |
| `tk_string_len_w` | `tk_str_len_w` (exists!) |
| `tk_string_startswith_w` | `tk_str_startswith_w` (exists!) |
| `tk_string_substr_w` | `tk_str_substr_w` (exists!) |
| `tk_string_trim_w` | `tk_str_trim_w` (exists!) |
| `tk_string_uuid_w` | new |

### json (30 missing)
| Emitted symbol | Probable alias target |
|---|---|
| `tk_json_getstr_w` | new or `tk_json_str_w` |
| `tk_json_encstr_w` | new (JSON-escape a string) |
| `tk_json_encode_w` | new |
| `tk_json_decode_w` | new |
| `tk_json_geti64_w` | new |
| `tk_json_geti32_w` | `tk_json_geti64_w` |
| `tk_json_getf32_w` | new |
| `tk_json_getfloat_w` | new |
| `tk_json_getobj_w` | new |
| `tk_json_getarr_w` | new |
| `tk_json_getarray_w` | `tk_json_getarr_w` |
| `tk_json_getopt_w` | new |
| `tk_json_getval_w` | new |
| `tk_json_getregulations_w` | loke-specific, shouldn't be in stdlib |
| `tk_json_isnullkey_w` | new |
| `tk_json_arr_w` | new |
| `tk_json_arrget_w` | new |
| `tk_json_arrlen_w` | new |
| `tk_json_entries_w` | new |
| `tk_json_kv_w` | new |
| `tk_json_obj_w` | new |
| `tk_json_parsearray_w` | new |
| `tk_json_quote_w` | new |
| `tk_json_strarr_w` | new |
| `tk_json_strarray_w` | `tk_json_strarr_w` |
| `tk_json_tryarr_w` | new |
| `tk_json_trybool_w` / `tryboolkey_w` | new |
| `tk_json_tryfloat_w` / `tryfloatkey_w` | new |
| `tk_json_tryint_w` / `tryintkey_w` | new |
| `tk_json_trystr_w` / `trystrkey_w` | new |

### time (6 missing)
| Emitted symbol | Probably alias |
|---|---|
| `tk_time_nowms_w` | new |
| `tk_time_nowunix_w` | new |
| `tk_time_unixnow_w` | = `tk_time_nowunix_w` |
| `tk_time_elapsedms_w` | new |
| `tk_time_formatnow_w` | new |
| `tk_time_sleepms_w` | new |

### db (12 missing)
| Emitted symbol | Note |
|---|---|
| `tk_db_execparams_w` | new |
| `tk_db_manyparams_w` | new |
| `tk_db_nowms_w` | → time module |
| `tk_db_queryone_w` | new |
| `tk_db_queryoneparams_w` | new |
| `tk_db_queryparams_w` | new |
| `tk_db_rowbool_w` | new |
| `tk_db_rowget_w` | new |
| `tk_db_rowi32_w` | new |
| `tk_db_rowi64_w` | new |
| `tk_db_rowslen_w` | new |
| `tk_db_rowstr_w` | new |

### Other modules (remaining)
- `tk_file_*_w` (5): appendline, ensuredir, listglob, parsetoml, remove
- `tk_fs_*_w` (3): read, write, writetext
- `tk_http_*_w` (6): gettimeout, header, iserror, isok, pathparam, postheaders, queryparam
- `tk_encoding_*_w` (3): base64urlencodenopad, jsonfield, jsonfieldint
- `tk_infer_*_w` (5): embed, generate, load, loadstreaming, unload
- `tk_keychain_*_w` (4): delete, exists, get, set
- `tk_math_pow2neg_w` (1)
- `tk_mdns_*_w` (5): advertise, browse, servicerecord, stopadvertise, stopbrowse
- `tk_mlx_*_w` (3): generate, isavailable, load
- `tk_process_*_w` (5): env, exec, homedir, readlines, spawndetached
- `tk_securemem_*_w` (5): alloc, read, sweep, wipe, write
- `tk_std_homedir_w` (1)
- `tk_sys_*_w` (6): chipname, cpucount, diskfreegb, isarm64, platform, totalramgb
- `tk_tls_*_w` (7): close, connecttls, genselfsigned, listentls, read, tlsconfig, write
- `tk_vecstore_*_w` (6): collection, delete, deletebefore, open, search, upsert

### ooke framework (4 missing)
- `ooke_config_cfgdefault`
- `ooke_config_configload`
- `ooke_serve_serverun`
- `ooke_template_renderfile`

### Bare names (9 — loke import issue)
`getstr`, `getu16`, `html`, `join`, `json`, `len`, `slice`, `take`, `text` — these are method-style calls on objects that toke emits as bare function names instead of `tk_*_w` wrappers. Likely a toke codegen issue for method dispatch on built-in types.

### loke module (4 — sandbox)
`core_agents_sandbox_checkcostlimit`, `checkpermission`, `newsandbox`, `toresult` — functions exist but with `$sandbox` struct parameter type that doesn't match the i64 calling convention.

## Summary

- **~60 symbols are aliases** of existing C functions (naming variant: `tk_string_*` vs `tk_str_*`, `parsefloat` vs `tofloat`, etc.)
- **~70 symbols need new C implementations** (json object access, db row access, time, infer, etc.)
- **~9 are toke codegen issues** (bare method names, `tk_string_*` prefix instead of `tk_str_*`)
- **4 are ooke** framework functions
