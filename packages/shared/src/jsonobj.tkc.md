# shared.jsonobj — reading a NESTED value out of JSON

## Why this module exists

`std.json` has no way to read a nested value. That is not a figure of speech; every route
was measured at toke `0b0bc4e` and each one fails differently:

| attempt | result |
|---|---|
| `json.str(o;"usage")` then `json.dec` on it | `$jsonerr` — `usage` is an object, and `json.str` is typed `str!JsonErr`, so it refuses a non-string. This is what `providers/anthropic` and `providers/openai` both did |
| `json.i64(o;"usage.input_tokens")` — a dotted path | `$jsonerr`. Dotted paths are not supported, in any of the typed accessors |
| `json.getval(o;"usage")` then `json.i64` | **SIGSEGV** |
| `str.matchbracket(rest)` on the remainder | `$bracketerr` |

The typed API is seven functions — `enc`, `dec`, `str`, `u64`, `i64`, `f64`, `bool`, `arr` —
and every accessor among them takes a `Json` plus a **flat** key. There is no
`json.obj(Json, str) -> Json!JsonErr`, so a document one level deep is unreachable.

The other fifty-odd `json.*` names in `std.json`'s interface are all `(i64, i64) -> i64`:
`getval`, `getobj`, `getstr`, `getint`, `has`, `keys` and the rest. They are raw runtime
helpers that operate on a different representation, reached through `json.parse` — which is
upstream **T-17**, a name that links to an unrelated symbol. Handing one of them the typed
`$json` struct is what produces the segfault above: struct and handle share an ABI, so it
compiles, links, and dereferences whatever the struct's first word happens to be.

Filed upstream as **T-32**. The ask is one function.

## How this works instead

Two facts make a workaround possible, both measured:

1. `$json` is declared `{ raw:str }`, and `o.raw` holds the **whole** document text.
2. `$json{raw:"<text>"}` can be constructed in loke code and the typed accessors read it
   correctly. `json.i64($json{raw:"{\"input_tokens\":150}"};"input_tokens")` returns 150.

So `nested` finds `"key":` in `o.raw`, brace-matches the object that follows, and re-wraps
that substring. From there the ordinary typed accessor works on a flat key.

`objend` is a real scanner, not a `}` search, because the shortcut is wrong on data that
occurs in practice: a response containing `"note":"a } brace"` would end the object early.
It tracks string state and backslash escapes. All four cases are asserted in
`tests/unit/shared/test_jsonobj.tk`: a brace inside a string value, an escaped quote inside
a string value, an absent key, and an object nested one level deeper than the one asked for.

## What it does not do

- **Arrays.** `objend` matches `{}`, not `[]`. `json.arr` is typed and works, so an array of
  objects is reachable by other means; nothing needed it yet.
- **Duplicate keys.** `str.indexof` finds the first `"key":` in the document, which is the
  first *textual* occurrence anywhere — including one nested inside a different object
  earlier in the text. For provider responses, where `usage` appears once at the top level,
  that is sound. It is not a general JSON path.
- **Missing is not an error.** An absent key yields `$json{raw:"{}"}`, so the accessor that
  follows takes its own `$jsonerr` arm and the caller's fallback applies. `hasnested` is
  there for a caller that needs to tell "absent" from "present but zero" — which
  `providers` does not, but an audit reader might.

Every `mt` in this module writes `$ok` first, because arms bind by position (**T-31**).
