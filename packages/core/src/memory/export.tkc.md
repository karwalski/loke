Handles exporting memory palace contents to JSON, CSV, or Markdown formats, and importing from JSON. Queries drawers from the database and formats them for external consumption or backup. Depends on std.db, std.fs, and std.json.

`importjson` reads the file with `json.arr` and `shared.jsonobj.strvalue`/`numtext` (LS1.1k); it used to read JSON elements with `db.rowstr` and crashed. A duplicate id is not counted, and the score row carries the file's `created_at` (M1.7c).
