# Document and Image Libraries Required by toke

**Version:** 1.0
**Date:** 2026-09-19
**Audience:** the **toke development team**. Written from a downstream consumer's position so the
requirements are visible before any interface is designed.

This document follows the pattern of [ooke-bindings-required.md](archive/ooke-bindings-required.md), which
worked: downstream states the need and the interface it expects, upstream designs and ships, and the
blocked stories unblock. That document is now complete, and this is the next set.

The need arises from a personal-finance workspace (epic MK21) where a user imports their own bank
statements and everything is analysed on-device. It generalises well beyond that: document ingestion
is a common requirement, and toke currently cannot read the three formats business data actually
arrives in.

---

## What toke already has, verified

Stated first, because it materially narrows the ask and because a request that misstates the current
position wastes everyone's time.

| Capability | Module | Status |
|---|---|---|
| CSV read and write | `std.csv` | **Present.** `csv.reader`, `csv.next`, `csv.header`, `csv.writer`, `csv.writerow`, `csv.flush`, `csv.parse` |
| Image decode and encode | `std.image` | **Present.** PNG, JPEG, WebP, BMP, plus `tograyscale`, `crop`, `resize`, `pixelat`, `fromraw` — all from a single dependency-free `image.c` |
| Numeric and matrix work | `std.math`, `std.vec`, `std.dataframe`, `std.analytics`, `std.ml` | Present |
| Vendoring a C library | `stdlib_deps.c` + `append_vendor_sources()` | Established pattern: `cmark` and `tomlc99` are vendored this way |
| Exposing C to toke | 43 hand-written `*_glue.c` modules | Established pattern. **There is no general FFI**, so every capability is a deliberate glue module plus a `.tki` |

Two constraints that shape every option below:

- **toke is a C99 project.** The link line is `-std=c99` and there are zero C++ files in the stdlib.
  Introducing a C++ dependency is an architectural change, not an addition. This is the single most
  important constraint in this document.
- **No general FFI**, so "just bind an existing library" always means writing and maintaining glue.

## Status summary

| Capability | Priority | Route | Blocks |
|---|---|---|---|
| [1. CSV hardening](#1-csv-hardening) | **P1** | Extend `std.csv` | MK21.3 |
| [2. PDF text extraction](#2-pdf-text-extraction) | **P1** | New `std.pdf`, vendored C | MK21.4, MK21.4a |
| [3. Zip archive reading](#3-zip-archive-reading) | **P1** | New `std.zip`, vendored C | MK21.3a, and much else |
| [4. XLSX reading](#4-xlsx-reading) | P2 | New `std.xlsx` on `std.zip` | MK21.3a |
| [5. OCR](#5-ocr) | P2 | **Standalone repository** — see that section | MK21.4a |
| [6. Image preprocessing gaps](#6-image-preprocessing-gaps) | P3 | Extend `std.image` | MK21.5, OCR |

Priority: **P1** blocks a workspace that cannot ship without it · P2 blocks a named feature · P3 is
quality of result

---

## 1. CSV hardening

**Blocks:** MK21.3 (L)
**Route:** extend the existing `std.csv`. No new module, no vendoring.

`std.csv` works. What it does not yet survive is real-world bank and government exports, which are
notably worse than well-formed CSV. Every item below has been hit in practice:

| Problem | What happens today | What is needed |
|---|---|---|
| **UTF-8 BOM** | The first header becomes `﻿Date` and column mapping fails on a file that looks correct | Detect and strip a BOM |
| **Non-UTF-8 encodings** | Australian and European bank exports are frequently CP1252 or Latin-1. Bytes are misinterpreted silently, so a merchant name is corrupted rather than rejected | Declare an encoding, or detect and transcode; at minimum **fail loudly** rather than producing mojibake |
| **Delimiter variation** | Semicolon-separated is standard in several locales; `sep` is settable but must be known in advance | A sniffer over the first N lines, with the detected delimiter reported so a caller can show it |
| **Quoted multi-line fields** | A description field containing a newline splits one record into two | Honour RFC 4180 quoting across line breaks |
| **Ragged rows** | Trailing-comma and short rows are common in exports | A defined policy — pad, error, or report — chosen by the caller, not guessed |
| **Type-preserving read** | Everything is a string, so leading zeros in a BSB and long account numbers must be handled by every caller | Keep a raw-string accessor as the default and document that numeric coercion is the caller's job. **Do not** auto-coerce: that is how leading zeros get destroyed |

**Interface expected:**

```
csv.sniff(data:[byte]) -> $csvdialect ! $csverr     (* delimiter, quote char, has_header, encoding guess *)
csv.readeropts(data:[byte]; opts:$csvopts) -> $csvreader ! $csverr
```

with `$csvopts` carrying delimiter, quote character, encoding, BOM handling and a ragged-row policy.

**Acceptance:** a fixture set of deliberately awkward exports — BOM, CP1252, semicolon-separated,
embedded newline in a quoted field, ragged rows, leading-zero identifiers — each parsed correctly or
rejected with a message naming the line and the problem. Silence is the failure mode to eliminate.

---

## 2. PDF text extraction

**Blocks:** MK21.4 (L), MK21.4a (XL)
**Route:** new `std.pdf`, vendored C library

**The distinction that matters, and that is usually conflated:** most bank statements, invoices and
government reports are **text PDFs**, where the characters are present in the file and can be
extracted exactly. Only scanned or photographed documents need OCR. Extraction is exact; OCR is
probabilistic. Conflating them means paying OCR's error rate on documents that did not need it.

So text extraction is both the **more valuable** capability and much the **smaller** one, and it
should ship first and separately.

**What is needed, in priority order:**

1. **Text extraction with positions.** Not just a string — each text run with its page number and
   bounding box. Position is what makes tabular extraction possible, and a bank statement is a table.
   A flat string loses the column structure and is close to useless for this purpose.
2. **Page count and per-page access**, so a large statement can be processed incrementally.
3. **Encrypted-PDF detection.** Bank statements are routinely password-protected. Detect it and return
   a distinct error rather than returning empty text, which reads as "no content" and is wrong.
4. **A scanned-document signal.** Report whether a page contains extractable text at all, so a caller
   can route to OCR only where needed. This is what makes item 1 of MK21.4 implementable.
5. Embedded image extraction, for the OCR path. Lower priority.

**Interface expected:**

```
pdf.open(data:[byte]) -> $pdfdoc ! $pdferr        (* $pdferr includes Encrypted, Malformed *)
pdf.pagecount(doc:$pdfdoc) -> u32
pdf.textruns(doc:$pdfdoc; page:u32) -> [$textrun] ! $pdferr
pdf.hastext(doc:$pdfdoc; page:u32) -> bool
pdf.images(doc:$pdfdoc; page:u32) -> [$imgbuf] ! $pdferr
```

`$textrun` carrying `text`, `x`, `y`, `width`, `height`, and font size where available.

**Implementation route.** Vendor a C library, following `cmark` and `tomlc99`. Candidates worth
evaluating, all C and all permissively licensed: **pdfium** is the most capable but is C++ and
therefore disqualified by the C99 constraint unless a C shim is accepted; **mupdf** is C with a
suitable licence but large; **podofo** is C++. A **purpose-built minimal extractor** is also viable
and should be costed, because the subset actually required — parse the xref table, decompress Flate
streams, walk the content stream for text-showing operators, apply the font's encoding map — is far
smaller than a full renderer. toke already vendors zlib-equivalent inflate for other purposes; confirm
before assuming.

**The honest warning:** PDF text extraction is notoriously fiddly. Font encoding maps, ligatures,
ToUnicode CMaps, and text drawn out of reading order all produce plausible-looking wrong output.
Budget for a fixture suite from real-world documents, and treat "extracted something" as a much weaker
result than "extracted correctly".

---

## 3. Zip archive reading

**Blocks:** MK21.3a (M), and more than its size suggests
**Route:** new `std.zip`, vendored C

Small, self-contained, and it unblocks disproportionately: XLSX, ODS, DOCX, EPUB, many government
bulk-data downloads, and any future archive handling are all zip containers. This is the highest
ratio of unblocked capability to implementation cost in this document.

**Interface expected:**

```
zip.open(data:[byte]) -> $ziparchive ! $ziperr
zip.entries(a:$ziparchive) -> [$zipentry]          (* name, size, compressed size, is_dir *)
zip.read(a:$ziparchive; name:str) -> [byte] ! $ziperr
```

Read-only is sufficient for every consumer named here. Writing can wait.

**Implementation route.** **miniz** is the obvious candidate: single-file C, public domain, and it is
already the answer most projects reach for. Store and Deflate are the only methods needed in practice.

**Security constraints, not optional.** An archive is attacker-controlled input:

- Reject path traversal in entry names — `../` and absolute paths
- Enforce an uncompressed-size cap and a compression-ratio cap, so a zip bomb fails rather than
  exhausting memory
- Cap the entry count

---

## 4. XLSX reading

**Blocks:** MK21.3a (M)
**Route:** new `std.xlsx`, built on `std.zip`. Do not vendor a second library for this.

XLSX is a zip of XML. With `std.zip` in place this becomes a focused parser over
`xl/worksheets/sheet*.xml`, `xl/sharedStrings.xml` and `xl/workbook.xml`.

**The three things that catch every first implementation:**

1. **Shared strings.** Cell text is usually an index into `sharedStrings.xml`, not inline. A parser
   that reads only the sheet gets integers where it expected text.
2. **Dates are numbers.** A date cell holds a serial number interpreted through the workbook's date
   system, and the 1900 system contains a deliberate leap-year bug that must be reproduced to match
   Excel. Getting this wrong silently shifts every date in a bank statement by a day or two.
3. **Sparse rows and columns.** Cells carry references like `C7` and absent cells are simply missing,
   so position cannot be inferred from order.

**Interface expected:**

```
xlsx.open(data:[byte]) -> $workbook ! $xlsxerr
xlsx.sheets(wb:$workbook) -> [str]
xlsx.rows(wb:$workbook; sheet:str) -> [[$cell]] ! $xlsxerr   (* $cell: raw string, type, and resolved value *)
```

**Scope discipline.** Read cell values only. No formula evaluation, no styling, no charts, no pivot
tables. A formula's cached value is what a data-import consumer wants, and evaluating formulae is an
unbounded project with no relevance to reading a bank statement.

---

## 5. OCR

**Blocks:** MK21.4a (XL)
**Route:** **a standalone repository**, not the standard library. This section argues for that, and is
deliberately more cautious than the others.

### Why not the standard library

OCR is categorically unlike the items above. PDF and zip are parsers: bounded, deterministic, testable
against fixtures, and each a few thousand lines. OCR is a recognition system with an accuracy
distribution, model artefacts, a training pipeline, and per-language and per-font behaviour. Putting it
in `stdlib/` would mean the standard library ships model weights and acquires an accuracy metric, which
is not what a standard library is for.

### Why not vendor Tesseract

This is the obvious suggestion and it should be rejected explicitly, for one decisive reason and
several supporting ones:

- **Tesseract is C++, and toke is a C99 project with zero C++ files.** Vendoring it means adding a C++
  toolchain requirement to every toke build, on every platform, forever. That is an architectural
  decision about what toke is, and it should not be made in order to read a bank statement.
- It requires **Leptonica** as well, so it is two large dependencies.
- It ships **model files** measured in tens of megabytes per language, which have to be located,
  versioned and distributed.
- Its accuracy is highly sensitive to preprocessing, so vendoring it does not remove the need for the
  pipeline work below — it only removes the classifier.

### The three routes, honestly compared

| Route | Effort | Portability | Accuracy | Verdict |
|---|---|---|---|---|
| **A. Platform binding** — bind the OS text recogniser (macOS Vision, Windows OCR API) | Small, per platform | Poor by construction: different engine per platform, none on bare Linux | High, and maintained by someone else | **Best short-term answer.** Ship this first |
| **B. Vendor Tesseract** | Medium | Good | High | **Rejected** on the C++ constraint above |
| **C. Standalone toke-native engine** | Large | Total | Unknown, and the honest answer is "lower, at first" | **The interesting long-term answer.** See below |

**Recommendation: A now, C as a separate project, B not at all.** A platform binding is a small glue
module that makes MK21.4a shippable on macOS immediately. C is a genuine project with genuine value
and should not be rushed to meet a demo deadline.

### Route C: a standalone toke-native OCR — `toke-ocr`

Its own repository, its own release cadence, consumed as a dependency. What makes this more plausible
than it first sounds is that **toke already has most of the preprocessing primitives**: `std.image`
decodes PNG, JPEG, WebP and BMP and provides `tograyscale`, `crop`, `resize` and `pixelat`, and
`std.math`, `std.vec` and `std.ml` cover the numeric work. The missing piece is recognition, not
infrastructure.

**Scope it narrowly and it becomes tractable.** Do not attempt general OCR. Target **clean,
machine-printed, high-contrast documents in a Latin script** — which is exactly what bank statements,
invoices, payslips and government letters are. Handwriting, low-resolution photographs, dense
multi-column layouts and non-Latin scripts are explicitly out of scope, and saying so is what keeps the
project finishable.

Proposed stories for `toke-ocr`:

| Story | Size | Summary |
|---|---|---|
| OCR1.1 | M | **Binarisation** — adaptive thresholding (Sauvola or Niblack) rather than a global threshold, because statement scans have uneven illumination. Works on `std.image`'s greyscale output |
| OCR1.2 | M | **Deskew** — estimate page rotation by projection profile or Hough transform and correct it. A one-degree skew materially degrades line segmentation, so this is not optional polish |
| OCR1.3 | M | **Line and word segmentation** — horizontal projection for lines, connected-component analysis with a gap threshold for words. The main output that everything downstream depends on |
| OCR1.4 | L | **Glyph segmentation** — connected components with splitting for touching characters and merging for `i`, `j` and accents. Historically the hardest classical stage and where most errors originate |
| OCR1.5 | L | **Glyph classification** — normalise each glyph to a fixed grid and classify. A k-nearest-neighbour or small decision-tree model over `std.ml` is a credible baseline; a small convolutional model via `std.infer` is the stronger option if the dependency is acceptable |
| OCR1.6 | M | **Training pipeline and model artefact** — render a glyph corpus from known fonts at several sizes and degradations, train, and ship a versioned model file. Synthetic training data is entirely adequate for machine-printed text and avoids any corpus-licensing question |
| OCR1.7 | M | **Per-glyph and per-field confidence** — non-negotiable, and the reason the whole project is safe to use. A recognised character carries its confidence so a consumer can flag low-confidence fields for review instead of accepting them. MK21.5 depends on exactly this |
| OCR1.8 | M | **Layout reconstruction** — group words into cells and rows using position, so a statement table comes back as a table. Without this the output is a bag of words and the downstream work is guesswork |
| OCR1.9 | M | **Lexicon and pattern post-correction** — a huge accuracy win for this domain. Amounts, dates, BSBs and account numbers have rigid formats, so a candidate that fails the format can often be corrected with high confidence. `1` against `l` and `0` against `O` are the classic confusions and both are resolvable from context |
| OCR1.10 | L | **Accuracy benchmark, published with its caveats** | Character and word error rate on a held-out set of rendered and scanned documents, reported per font and per degradation level, with **no aggregate figure quoted without the distribution behind it**. Publish the negative results too: an engine that is honest about where it fails is usable, whereas one quoting a single accuracy number is not |

**The thing to be honest about up front:** route C will start out less accurate than Tesseract, and
possibly for a long time. It is worth doing for portability, for having no C++ dependency, for the
confidence plumbing being designed in rather than bolted on, and for it being written in toke. It is
not worth doing if the goal is to beat Tesseract on accuracy, and the project should say so in its own
README so nobody adopts it under a misapprehension.

---

## 6. Image preprocessing gaps

**Blocks:** MK21.5 (L), and route C above
**Route:** extend `std.image`

`std.image` covers more than expected. Four gaps matter for document work specifically:

| Gap | Why it matters |
|---|---|
| **Rotation by arbitrary angle** | `fliph` and `flipv` exist; deskew needs arbitrary-angle rotation with interpolation |
| **Adaptive thresholding** | The single most valuable addition. Global thresholding fails on unevenly lit scans, which is most scans |
| **Convolution or a blur primitive** | Needed for noise reduction before thresholding, and reusable well beyond OCR |
| **TIFF decode** | Scanners and fax-derived documents produce TIFF, and multi-page TIFF is still common in financial and legal document flows. Currently unsupported |

These are small, individually useful, and belong in `std.image` rather than in an OCR project, because
other consumers want them too.

---

## Recommended order

1. **`std.zip`** — smallest, and unblocks the most. miniz, plus the archive-safety constraints
2. **`std.csv` hardening** — small, and the workspace fails on real exports without it
3. **`std.pdf` text extraction** — the highest-value document capability, and the one that removes most
   of the need for OCR by handling text PDFs exactly
4. **`std.xlsx`** — follows `std.zip` naturally
5. **Platform OCR binding** — makes the scanned path shippable on macOS
6. **`std.image` additions** — rotation, adaptive threshold, convolution, TIFF
7. **`toke-ocr` as a separate repository** — begun deliberately, not against a demo deadline

Items 1 to 4 are conventional parser work with clear acceptance criteria. Item 7 is a research-flavoured
project and should be resourced and judged differently from the rest.

## What downstream will do in the meantime

So that nothing here reads as a blocking dependency: loke's MK21 ships **CSV only**, states that
limitation plainly rather than listing Excel support it does not have, and handles extraction through a
**local sidecar process** following the precedent at `packages/privacy-filter/`. That keeps extraction
on-device, which is the property that actually matters for the workspace, without waiting on any of
this. These libraries would let that sidecar be retired, which is the goal — a sidecar is a process
dependency and an install problem, and the existing one demonstrates the risk: its checked-in
virtualenv does not contain its own dependencies and cannot run.
