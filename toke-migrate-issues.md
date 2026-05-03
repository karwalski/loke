# toke --migrate Issues Found During loke Migration

559 .tk files, 115 migrated (21%), 444 failed (79%), 0 compile after migration.

## Issue 1: Migrator rejects `$` and `@` in valid positions
- Files with `$` at certain offsets get "character outside Profile 1 character set"
- `$` is in the 55-char set and is used extensively for type names
- Example: `packages/mcp-broker/src/registry.tk` offset 39 = `$` (start of a type name in struct field)
- Example: `packages/mcp-broker/src/main.tk` offset 85 = `@` (array type)

## Issue 2: Migrator doesn't handle UTF-8 in comments
- Files with em dash `—` (0xe2 0x80 0x94) in `//` comments fail
- The migrator should strip comments before checking character set
- Example: `packages/core/src/privacy/placeholder_store.tk` offset 8 = 0xe2

## Issue 3: Migrated files still have syntax errors
- Files that `--migrate` outputs successfully still fail `--emit-llvm`
- Example: `packages/core/src/pipeline/types.tk` — migrated output has `@$stagedetail)` with trailing paren
- The `@($type)` → `@$type` transform leaves orphan `)` in some contexts

## Issue 4: `pub` keyword not stripped in all positions
- `pub m.$typename{` → should become `t=$typename{` but some output still has `pub`
- `pub f=` → should become `f=`

## Issue 5: Match syntax in complex expressions
- Simple `expr|{...}` works
- Chained/nested matches like `a|{$ok:v v|{...};$err:e e}` may not transform correctly

## Reproduction
```bash
cd /Users/matthew.watt/loke/loke
# Restore clean v0.2 source:
git checkout -- packages/ src/ tests/
# Migrate a single file:
toke --migrate packages/core/src/pipeline/types.tk > /tmp/migrated.tk
# Check it compiles:
toke --emit-llvm --out /dev/null /tmp/migrated.tk
```

## Counts
- Total files: 559
- `$` character failures: ~200+
- UTF-8 comment failures: ~50
- Post-migration syntax errors: all 115 "successfully" migrated files
