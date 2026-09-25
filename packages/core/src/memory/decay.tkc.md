Memory decay module that applies time-based score degradation to stored memories using a half-life formula. Provides sweep functionality to prune low-scoring memories and refresh access timestamps. Depends on std.db for persistence and core.memory.types for shared type definitions.

`sweep` normalises `created_at` in its query, because the column holds both epoch seconds and `datetime('now')` TEXT, and `agereadable` rejects anything below `epochfloor()` (2020-01-01) (M1.7c).
