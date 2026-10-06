Exports governance reports to CSV, JSON, or plain text format based on the report's format field. Depends on core.governance.reportengine, std.str, and shared.log.

2026-10-07 (GA5.31 Not-done, closed by GA5.32): CSV is RFC 4180 (a field holding a comma, quote, CR or LF is quoted, embedded quotes doubled); JSON carries the rows and escapes every string through `shared.jsonobj.escape`. Also depends on shared.jsonobj.
