# Upstream Asks — toke and ooke

**Version:** 1.0
**Verified:** 2026-09-19 against toke `main` (past `b66bd8e`) and ooke `3.0.0-dev`
**Story:** F10.10

The single register of what loke needs from toke and ooke. It replaces four documents that each
accumulated gaps and none of which was ever re-checked:

| Retired document | Outcome on re-verification |
|---|---|
| `docs/linker-gaps.md` | **Obsolete.** 0 of its 131 symbols are genuine upstream gaps — see below |
| `ooke-gaps.md` | **Obsolete.** 0 of its 6 gaps remain open |
| `docs/ooke-bindings-required.md` | Already marked COMPLETE by the ooke team; retained as a record of a process that worked |
| `toke-migrate-issues.md` | Superseded. It was a migration working log; `build/break-report.txt` now produces the same information from the build itself |

**The headline is that there is almost nothing to file.** Every historical gap has closed. Had these
documents been filed as written, loke would have reported roughly 137 already-fixed problems to its
own upstream and buried the few real items. That is the argument for this register existing: a gap
document that is never re-verified becomes misinformation.

---

## Open asks

### 1. Document and image libraries — P1 to P2

Fully specified in **[`docs/toke-libraries-required.md`](docs/toke-libraries-required.md)**, which
states the expected interface, the implementation route and the constraints for each:

| Ask | Priority | Route |
|---|---|---|
| `std.zip` | **P1** | Vendor miniz. Smallest job, unblocks XLSX, ODS, DOCX, EPUB and government bulk data |
| `std.csv` hardening | **P1** | Extend the existing module — BOM, non-UTF-8 encodings, delimiter sniffing, quoted newlines, ragged rows |
| `std.pdf` text extraction | **P1** | Vendor C. Highest-value document capability, and it removes most of the need for OCR |
| `std.xlsx` | P2 | Build on `std.zip`; do not vendor a second library |
| `std.image` additions | P3 | Arbitrary-angle rotation, adaptive thresholding, convolution, TIFF decode |
| OCR | P2 | **Not the standard library.** Bind the platform recogniser now; run a toke-native engine as its own repository. Vendoring Tesseract is rejected — it is C++, and toke is a C99 project with zero C++ files |

### 2. Documentation correction — P3, trivial

Three toke documents state that **toke has no comment syntax**, which stopped being true when
`(* ... *)` block comments shipped on 2026-04-27 (`docs/progress.md` story 7.6.3, with the decision to
keep them at story 75.1.2):

- `docs/companion-file-spec.md`
- `docs/companion-fidelity-methodology.md`
- `docs/conventions.md`

Downstream consumers read these as normative. loke's own house rule is still to keep `.tk` source
comment-free, for token density, but that is now a project choice rather than a language constraint —
and the documents should say which it is.

---

## Closed, with the evidence

Recorded so that nobody reopens these from an older document.

### `docs/linker-gaps.md` — 131 symbols, 0 genuine gaps

Dated 2026-05-16, it reported 150+ undefined symbols and was cited as the reason 54 test files were
stubbed rather than importing the modules they test. Re-checked symbol by symbol:

- **115 of 131 now exist** in `~/tk/toke/src/stdlib/`.
- **14 of the remaining 16 are not symbol names at all** — they are prose fragments the extraction
  picked up, such as `tk_file_` and `tk_http_` from sentences about "the `tk_file_*` functions".
- The **two that looked real are both loke bugs, not upstream gaps:**

| Apparent gap | Reality |
|---|---|
| `str.nowiso8601` — 5 loke files call it | The capability exists, in the **wrong module**. `std.time` provides `time.now`, `time.format`, `time.parse`, `time.toparts` and 20 more. loke should call `std.time`. **This is worth fixing for its own sake:** `storage/audit.tk` writes the literal string `'now()'` into `created_at` (GA5.1), and a missing timestamp helper is a plausible reason why |
| `str.between` — 2 call sites in `privacy/content.tk` | A convenience composition, not a capability. `str.indexof` and `str.slice` both exist, so a five-line local helper covers it. `packages/core/src/util/strings.tk` is the natural home |

**Consequence beyond the filing.** The stubbed-test excuse is dead. `tests/unit/privacy/test_guardian.tk:6`
carries `(* i=guardian:core.privacy.guardian; -- linker issue, stubbed below *)`, and that linker issue
no longer exists. Story X7 should proceed on that basis once the build is green.

### `ooke-gaps.md` — 6 gaps, 0 remain

| Gap | Evidence it is closed |
|---|---|
| GET handlers not registered | `scripts/gen_handlers.sh` detects and registers `f=get(` |
| POST handlers not registered | Same, for `f=post(` |
| Page handler must call `renderfile` or the route is not registered | `serve.tk::serveregisterstatic` now takes `handledpaths` and skips its own registration for claimed paths (`:37-38`) |
| No CORS headers for localhost cross-port | `serve.tk` calls `http.setcors(corsorigins)`; `corsorigins` is threaded through `serverun` |
| Page `get()` bypassed when a matching template exists | Same `handledpaths` mechanism — the handler claims the path first |
| No API route namespace prefix | `apiprefix` is a config field and is threaded through `serverun`; `serve.tk:109-110` honours it |

### The `<a<b` parser ambiguity — fixed

Returning a comparison was previously indistinguishable from a return followed by a less-than, so
`<a<b` failed to parse and had to be written `<(a<b)`. Re-tested on current toke: `<a<b` now compiles
clean. Nothing to file.

---

## The rule this register exists to enforce

**Verify before filing.** Every gap here was real when it was written and most were fixed without
anyone telling loke, because loke never asked again. So:

1. A gap is recorded here with the date it was verified, not the date it was discovered.
2. Before filing anything upstream, re-verify it against a current checkout. A four-month-old gap
   document is a source of misinformation, not a backlog.
3. When a gap closes, it moves to the section above with the evidence, rather than being deleted —
   otherwise it gets rediscovered and refiled.
4. The register is re-verified as part of every toolchain-currency pass (F10), and the currency pass
   now runs on a schedule rather than when somebody notices.
