# core.memory.schema — the memory palace's tables

## What was wrong, and why nothing reported it

This module is the **only** place in the tree that issues `CREATE TABLE` for a `memory_*`
table. No migration does. And every one of its five statements was passed to `std.db.exec`
with the wrong arity:

```toke
mt db.exec(conn;"CREATE TABLE IF NOT EXISTS memory_drawers ( ... )")
```

`std.db.exec` is declared `(str, [str])` — the statement and its parameters. There is no
connection argument; `exec` uses the connection `db.open` established (there is only one, per
upstream T-30). So the call is **arity-compatible**: it type-checks, then reads the connection
pointer as a SQL string and the SQL string as a parameter array. It crashed before creating the
first table.

`core/storage/db.tk` carries a comment describing this identical defect being fixed in five of
its own calls. These five were missed, which is the usual shape of a sweep: the files somebody
was looking at got fixed and the ones they were not looking at did not.

So, measured: after a normal loke store is opened and its migrations have run, **none of the
four memory tables existed** — and `memory_scores` was not in this file at all, so it had no
creator anywhere, although `memory/decay.tk`, `memory/export.tk` and `memory/privacy.tk` all
read and write it. That is the empirical content of M1.7.

## Why decay had to be fixed first

`core.memory.decay.sweeprows` deletes a row when its decayed score falls below `prunebelow`,
and `apply` returned a bare `f32` — corrupted to `-inf` across a module boundary (T-20). A
comparison against `-inf` is true for every row.

It could not fire, because `memory_scores` did not exist, so `db.many` failed and `sweep`
returned early. **Creating these tables without fixing decay first would have made the first
sweep a total loss of the user's memory palace.** `decay.applybp` and the `agereadable` guard
landed in the same commit as this file, before it, and `tests/unit/memory/test_decay.tk` and
`tests/unit/memory/test_palace_drawers.tk` cross-reference each other so the ordering is not
rediscovered by whoever touches this next.

There was a second edge of the same knife: `created_at` was written as the literal SQL text
`now()` until 2026-09-23 (GA5.1), so `db.rowi64` reads **0** for every row written before that
date — 1970, maximally aged, below `prunebelow`. `agereadable` refuses to treat an
unreadable age as evidence of age.

## Error handling

`createtables` returns a plain `bool`, not `i64!$lokeerr`. Two reasons, and neither is style.
A result whose error side is a user-declared sum always takes arm 0 (T-18), so the `$err` arms
it used to carry were dead code — `palace.tk` could not have told a failure from a success. And
the four statements before the last one were bare `mt` statements in expression position, so
their results were **discarded**: a failure to create `memory_closets` could not stop the
function, let alone reach a caller. Each step is now checked and returns early, with the table
named in the log.

`conn:$dbconn` is kept in the signature although `exec` ignores it, because `palace.tk` passes
it and because T-30 means the single global connection is the one `db.open` set — the parameter
documents which connection the caller believes it is operating on, even though the library
gives it no choice.

## What this does NOT fix

**Nothing inserts into `memory_scores`.** Repo-wide there is one `UPDATE`, several `SELECT`s
and a `DELETE`, and no `INSERT` — so the table is created and stays empty. The reading paths
are written to cope (`COALESCE(ms.score,1.0)` in the export joins), but `memory/privacy.tk`'s
`WHERE pii_flagged=1` can never match and decay has nothing to sweep. Filed as **M1.7a**.
