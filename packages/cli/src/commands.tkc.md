CLI argument parser that maps subcommands (ask, pipeline, queue list/cancel, models list/recommend, memory search, agents list, overnight status, doctor, help, version) to a typed $command record with kind and arg fields. Also provides the top-level usage text. Exports the $command type and the parse and usage functions. Depends on std.str.

G1.6: `loke kill-switch <on|off> [--use-case <id> | --agent <id> | --provider <name>]` and `loke kill-switch status` parse to kinds `killswitch.<on|off>.<global|use_case|agent|provider>` and `killswitch.status`, with the target in arg; cli.main applies them to loke.db through core.governance.killswitch.

DA1.10: `loke audit verify` parses to kind `auditverify`; cli.main runs `core.storage.audit.verifychain` and `core.audit.reconcile.reconcile` and exits 0 only if the chain is intact and nothing is orphaned.
