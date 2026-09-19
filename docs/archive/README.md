# Archive

Files kept for provenance, not for use. Every file here carries its own archival notice; this index
says what superseded it.

| File | Superseded by |
|---|---|
| `linker-gaps.md` | [`UPSTREAM.md`](../../UPSTREAM.md) |
| `ooke-bindings-required.md` | [`UPSTREAM.md`](../../UPSTREAM.md) |
| `ooke-gaps.md` | [`UPSTREAM.md`](../../UPSTREAM.md) |
| `toke-migrate-issues.md` | [`UPSTREAM.md`](../../UPSTREAM.md) |
| `progress.json.retired-2026-09-19` | [`epics-and-stories.md`](../epics-and-stories.md) — see below |

**Do not file anything from an archived gap document.** All four were re-verified before archiving and
their gaps had closed; filing them as written would report already-fixed problems upstream.

## `progress.json.retired-2026-09-19`

The project's second backlog, last updated 2026-05-04 at v0.3.0. Retired because maintaining two
backlogs produced exactly the failures you would predict:

- **ID collisions with different meanings.** `P` was *Platform* in `docs/epics-and-stories.md` and
  *Accessibility & Polish* here; `W` was *Website* there and *Wire Stdlib Bindings* here; `T` was
  *Test Suite* there and *Test Infrastructure & Coverage* here. `MK8` and `MK9` named different
  epics in each file.
- **Stale statuses.** The `V3`/`V3B` epics still read `not_started` and `in_progress` four months
  after the v3 migration completed at 562/562 files.
- **No reconciliation.** `scripts/check_backlog.py` was planned and never written, so nothing ever
  compared the two.

Its twelve open items were re-verified against the committed tree and migrated as **Epic BG1** in
[`../epics-and-stories.md`](../epics-and-stories.md) — nine were already closed, with the evidence
recorded there. Everything else it held was marked done and duplicated in that file.

**`docs/epics-and-stories.md` is now the only backlog.** Do not add a second one.
