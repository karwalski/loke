# v3 Migration Batch Instructions

For each .tk file in your batch:

## Step 1: Understand Intent
- Read the file
- Check for any companion docs, comments (may have been stripped), or related spec files in docs/specifications/
- Look at imports to understand what modules it depends on
- Note: the file has ALREADY been through `toke --migrate` — it's partially v3 but may have errors

## Step 2: Check Compiler Errors
- Run: `/Users/matthew.watt/tk/toke/toke --emit-llvm --out /dev/null <file>`
- If it passes: move to Step 4
- If errors: read the error messages carefully

## Step 3: Fix (up to 5 iterations)
Key v3 syntax rules (from ooke source that compiles):
- `f=name(params):returntype{ body };` — functions end with `};`
- `t=$typename{ field:$str; field2:i64 };` — types end with `};`
- `t=$enumtype{ $variant1:i64; $variant2:i64 };` — enum variants need `:i64` payload
- `if(condition){ body }el{ other }` — parens required, `el` not `else`
- `lp(let i=0;i<n;i=i+1){ body };` — three-part loop
- `lp(let lv=0;true;lv=lv){ body };` — infinite loop idiom
- `mt expr { Ok:v result; Err:e fallback }` — match expression (single expression per arm, NO blocks)
- `let x=mut.initialval;` — mutable binding
- `@($type)` — array literal/constructor in expressions
- `@$type` — array type annotation (after `:`)
- `str` is valid as a type (lowercase scalar)
- No `pub`, no `_` in identifiers, no `[]`, no `//` comments, no `?`
- No top-level `let` — all bindings inside functions
- `!$errtype` for error unions (not `|$errtype`)
- `<expr` for return
- Import alias `mt` is reserved — use different name

## Step 4: Create Companion File
- Create `<filename>.tkc.md` next to the .tk file
- Content: 1-3 sentences explaining what the module does, its dependencies, and any notes

## Step 5: If Unclear
- Mark the file as "deferred" and move on
- Return to it after other files in the batch have companion files for context
