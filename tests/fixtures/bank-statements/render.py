# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Writers for the synthetic statement fixtures that are not CSV (story MK21.12).

Standard library only, and deterministic byte for byte: no timestamps, no random ids, no
floating point in the scan's geometry. None of openpyxl, reportlab or Pillow is needed, so the
fixtures regenerate identically on any machine, including CI, which installs none of them.

  xlsx(...)   a workbook the way Excel writes one: shared strings, date serials with a date
              number format, sparse rows and cells, a formula with a cached value
  pdf(...)    a text PDF in the standard Helvetica font: characters are extractable, and no
              recognition is needed to read it
  png(...)    an 8-bit greyscale PNG, and the scan simulation in `scan()`: a page of text in a
              bitmap face, rotated and offset as a sheet fed crooked, with speckle, a streak and
              punch holes

Each writer's output is checked by tests/fixtures/bank-statements/test_fixtures.py, which
reads it back with an independent reader and compares it with the ground truth.
"""

from __future__ import annotations

import random
import struct
import zipfile
import zlib
from io import BytesIO
from xml.sax.saxutils import escape

# ── XLSX ────────────────────────────────────────────────────────────────────────

ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    '</Types>'
)
ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)
WORKBOOK = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<workbookPr/><sheets><sheet name="Transactions" sheetId="1" r:id="rId1"/></sheets></workbook>'
)
WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '</Relationships>'
)
# Style 0 general; 1 a date (built-in numFmt 14); 2 money with negatives in red (custom 164).
STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00;[Red]\\-#,##0.00"/></numFmts>'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="3">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '</cellXfs></styleSheet>'
)
STYLE_DATE, STYLE_MONEY = 1, 2


def col_letter(col: int) -> str:
    out = ""
    while col:
        col, rem = divmod(col - 1, 26)
        out = chr(65 + rem) + out
    return out


class SharedStrings:
    """The pool Excel writes: each distinct string once, cells refer to it by index."""

    def __init__(self):
        self.items: list[str] = []      # serialised <si> bodies
        self.index: dict[str, int] = {}
        self.count = 0

    def add(self, text: str) -> int:
        self.count += 1
        if text not in self.index:
            self.index[text] = len(self.items)
            self.items.append(f"<t>{escape(text)}</t>")
        return self.index[text]

    def add_rich(self, runs: list[str], phonetic: str | None = None) -> int:
        """One string stored as several formatting runs, optionally with a phonetic run that is
        NOT part of its text. A reader that keeps only the first <t> truncates it; one that
        concatenates every <t> includes the phonetic text."""
        self.count += 1
        body = "".join(
            f'<r><rPr><b val="{1 if i == 0 else 0}"/><sz val="11"/></rPr><t xml:space="preserve">{escape(r)}</t></r>'
            for i, r in enumerate(runs))
        if phonetic:
            body += f'<rPh sb="0" eb="1"><t>{escape(phonetic)}</t></rPh>'
        self.items.append(body)
        return len(self.items) - 1

    def xml(self) -> str:
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                f'count="{self.count}" uniqueCount="{len(self.items)}">'
                + "".join(f"<si>{b}</si>" for b in self.items) + "</sst>")


def sheet_xml(rows: dict[int, list[str]]) -> str:
    """rows: row number -> list of pre-rendered <c> elements. Absent rows are simply absent."""
    body = "".join(f'<row r="{r}">{"".join(cells)}</row>' for r, cells in sorted(rows.items()))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{body}</sheetData></worksheet>')


def cell_s(ref: str, idx: int) -> str:
    return f'<c r="{ref}" t="s"><v>{idx}</v></c>'


def cell_n(ref: str, value: str, style: int = 0) -> str:
    s = f' s="{style}"' if style else ""
    return f'<c r="{ref}"{s}><v>{value}</v></c>'


def cell_f(ref: str, formula: str, cached: str, style: int = 0) -> str:
    s = f' s="{style}"' if style else ""
    return f'<c r="{ref}"{s}><f>{escape(formula)}</f><v>{cached}</v></c>'


def xlsx(sheet: str, sst: SharedStrings) -> bytes:
    """Zip the parts. Stored, not deflated, and dated 1980-01-01, so the bytes depend on
    nothing but the content (deflate output can differ between zlib builds)."""
    buf = BytesIO()
    parts = [
        ("[Content_Types].xml", CONTENT_TYPES),
        ("_rels/.rels", ROOT_RELS),
        ("xl/workbook.xml", WORKBOOK),
        ("xl/_rels/workbook.xml.rels", WORKBOOK_RELS),
        ("xl/styles.xml", STYLES),
        ("xl/sharedStrings.xml", sst.xml()),
        ("xl/worksheets/sheet1.xml", sheet),
    ]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for name, text in parts:
            info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            info.external_attr = 0o644 << 16
            info.create_system = 3
            z.writestr(info, text.encode("utf-8"))
    return buf.getvalue()


# ── PDF ─────────────────────────────────────────────────────────────────────────

def pdf_string(text: str) -> str:
    return "(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def pdf(pages: list[list[tuple[float, float, float, str]]], width=595, height=842) -> bytes:
    """A text PDF. Each page is a list of (x, y, size, text) draws, emitted in the order given,
    so the caller decides the content-stream order (and can make it differ from reading order).
    Helvetica is one of the 14 standard fonts, so nothing is embedded. No /Info, no /ID, no
    dates: the file depends on nothing but its content."""
    objs: list[bytes] = []

    def add(body: str | bytes) -> int:
        objs.append(body.encode("latin-1") if isinstance(body, str) else body)
        return len(objs)

    catalog = add("")          # filled in below, once the pages object's number is known
    pages_obj = add("")
    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    kids = []
    for draws in pages:
        ops = []
        for x, y, size, text in draws:
            ops.append(f"BT /F1 {size:g} Tf {x:.2f} {y:.2f} Td {pdf_string(text)} Tj ET")
        stream = ("\n".join(ops) + "\n").encode("latin-1")
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream")
        kids.append(add(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content} 0 R >>"))
    objs[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("latin-1")
    objs[pages_obj - 1] = (f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] "
                           f"/Count {len(kids)} >>").encode("latin-1")

    out = BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
              % (len(objs) + 1, catalog, xref))
    return out.getvalue()


# Helvetica advance widths (AFM, units of 1/1000 em) for the characters the statements use,
# so right-aligned amounts land where a real renderer would put them.
_HELV = {
    " ": 278, "!": 278, "&": 667, "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278,
    "-": 333, ".": 278, "/": 278, ":": 278, "#": 556, "$": 556,
    **{d: 556 for d in "0123456789"},
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778, "H": 722, "I": 278,
    "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778, "P": 667, "Q": 778, "R": 722,
    "S": 667, "T": 611, "U": 722, "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
}


def helv_width(text: str, size: float) -> float:
    return sum(_HELV.get(ch, 556) for ch in text) * size / 1000.0


# ── PNG and the scan ────────────────────────────────────────────────────────────

def png(width: int, height: int, pixels: bytes) -> bytes:
    """8-bit greyscale PNG. `pixels` is width*height bytes, row-major."""
    raw = b"".join(b"\x00" + pixels[y * width:(y + 1) * width] for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def png_pixels(data: bytes) -> tuple[int, int, bytes]:
    """Decode what png() writes: (width, height, pixels). For content comparison, since
    zlib builds may deflate differently while inflating to the same bytes."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4])
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
            if body[8:10] != b"\x08\x00":
                raise ValueError("not 8-bit greyscale")
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    rows = []
    for y in range(h):
        line = raw[y * (w + 1):(y + 1) * (w + 1)]
        if line[0] != 0:
            raise ValueError("only filter type 0 is written")
        rows.append(line[1:])
    return w, h, b"".join(rows)


# A 5x7 bitmap face, drawn for this file, for the characters a statement needs. Upper case
# only: the scanned statement is printed in capitals, as many are.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "10001", "11001", "10101", "10011", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    " ": ["00000"] * 7,
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ",": ["00000", "00000", "00000", "00000", "01100", "00100", "01000"],
    "/": ["00000", "00001", "00010", "00100", "01000", "10000", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "*": ["00000", "00100", "10101", "01110", "10101", "00100", "00000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
    "'": ["01100", "00100", "01000", "00000", "00000", "00000", "00000"],
    "&": ["01100", "10010", "10100", "01000", "10101", "10010", "01101"],
    "#": ["01010", "01010", "11111", "01010", "11111", "01010", "01010"],
    "$": ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
}

FIX = 16                 # fixed-point fraction bits for the scan geometry
ONE = 1 << FIX


def scan(lines: list[tuple[int, int, str]], width: int, height: int, *, seed: int,
         scale: int, rot_sin_q: int, rot_cos_q: int, shift_x: int, shift_y: int) -> bytes:
    """Render text lines onto a page, then feed the page through a crooked scanner.

    `lines` is (x, y, text) in page pixels. The rotation is given as its sine and cosine in
    FIX-bit fixed point, and every step is integer arithmetic, so the pixels are the same on
    every platform (a libm's sin() is not). Returns width*height greyscale bytes.
    """
    rng = random.Random(seed)
    page = bytearray([255]) * (width * height)
    cw = 6 * scale
    for x0, y0, text in lines:
        for i, c in enumerate(text):
            glyph = FONT.get(c)
            if glyph is None:
                raise ValueError(f"no glyph for {c!r}")
            ink = 20 + rng.randrange(40)            # uneven toner, per character
            gx = x0 + i * cw
            for gy, bits in enumerate(glyph):
                for gxx, bit in enumerate(bits):
                    if bit != "1":
                        continue
                    for dy in range(scale):
                        row = (y0 + gy * scale + dy) * width
                        for dx in range(scale):
                            px = gx + gxx * scale + dx
                            if 0 <= px < width and 0 <= row // width < height:
                                page[row + px] = ink

    # Inverse-map every output pixel into the page, bilinear, in fixed point. Outside the
    # sheet is the scanner lid: mid grey.
    out = bytearray(width * height)
    cx, cy = width // 2, height // 2
    lid = 150
    for oy in range(height):
        ry = oy - cy - shift_y
        base_x = -(rot_sin_q * ry)          # contribution of y to the page x, fixed point
        base_y = rot_cos_q * ry
        for ox in range(width):
            rx = ox - cx - shift_x
            sx = rot_cos_q * rx - base_x + cx * ONE      # page x, fixed point
            sy = base_y - rot_sin_q * rx + cy * ONE
            ix, iy = sx >> FIX, sy >> FIX
            if ix < 0 or iy < 0 or ix >= width - 1 or iy >= height - 1:
                out[oy * width + ox] = lid
                continue
            fx, fy = sx & (ONE - 1), sy & (ONE - 1)
            p = iy * width + ix
            a, b, c, d = page[p], page[p + 1], page[p + width], page[p + width + 1]
            top = a * (ONE - fx) + b * fx
            bot = c * (ONE - fx) + d * fx
            # Paper tone falling off towards the bottom of the sheet.
            v = (top * (ONE - fy) + bot * fy) >> (2 * FIX)
            out[oy * width + ox] = max(0, v - 12 * iy // height)

    # Speckle, a vertical streak from a dirty scanner glass, and two punch holes in the
    # left margin.
    for _ in range(width * height // 900):
        x, y = rng.randrange(width), rng.randrange(height)
        out[y * width + x] = rng.randrange(60, 170)
    streak = width * 7 // 10
    for y in range(height):
        for x in (streak, streak + 1):
            out[y * width + x] = max(0, out[y * width + x] - 35)
    for hy in (height * 3 // 10, height * 7 // 10):
        hx, r = 22, 11
        for y in range(hy - r, hy + r + 1):
            for x in range(hx - r, hx + r + 1):
                if (x - hx) ** 2 + (y - hy) ** 2 <= r * r and 0 <= x < width:
                    out[y * width + x] = 60
    return bytes(out)
