/**
 * MK9.7 — CSV/Excel URL Import for Moke
 *
 * Fetches CSV or Excel files from a URL and loads them as datasets.
 * Supports: direct file URLs, Google Sheets published CSV, S3 presigned URLs,
 * Dropbox links, GitHub raw URLs.
 *
 * Auto-detects delimiter, encoding, header row.
 * No external dependencies.
 */
(function () {
  'use strict';

  // -------------------------------------------------------------------
  // Constants
  // -------------------------------------------------------------------

  var DELIMITERS = {
    comma:     ',',
    tab:       '\t',
    semicolon: ';',
    pipe:      '|'
  };

  var DELIMITER_NAMES = {
    ',':  'comma',
    '\t': 'tab',
    ';':  'semicolon',
    '|':  'pipe'
  };

  // -------------------------------------------------------------------
  // detectFileType(url, contentType)
  // -------------------------------------------------------------------
  /**
   * Auto-detect file type from URL extension or Content-Type header.
   *
   * @param {string} url          — the source URL
   * @param {string} [contentType] — HTTP Content-Type header value
   * @returns {'csv'|'tsv'|'excel'|'unknown'}
   */
  function detectFileType(url, contentType) {
    var ct = (contentType || '').toLowerCase();

    // Content-Type based detection
    if (ct.indexOf('text/csv') !== -1 || ct.indexOf('text/comma-separated') !== -1) {
      return 'csv';
    }
    if (ct.indexOf('text/tab-separated') !== -1) {
      return 'tsv';
    }
    if (ct.indexOf('spreadsheetml') !== -1 ||
        ct.indexOf('application/vnd.ms-excel') !== -1 ||
        ct.indexOf('application/vnd.openxmlformats') !== -1) {
      return 'excel';
    }

    // URL extension based detection (strip query string first)
    var path = url.split('?')[0].split('#')[0].toLowerCase();
    if (path.match(/\.csv$/)) return 'csv';
    if (path.match(/\.tsv$/)) return 'tsv';
    if (path.match(/\.xlsx?$/)) return 'excel';

    // Google Sheets export URL is CSV
    if (url.indexOf('docs.google.com/spreadsheets') !== -1 &&
        url.indexOf('export') !== -1 &&
        url.indexOf('format=csv') !== -1) {
      return 'csv';
    }

    // Default: if content-type is text-ish, assume CSV
    if (ct.indexOf('text/plain') !== -1 || ct.indexOf('text/') !== -1) {
      return 'csv';
    }

    return 'unknown';
  }

  // -------------------------------------------------------------------
  // detectDelimiter(firstLines)
  // -------------------------------------------------------------------
  /**
   * Auto-detect CSV delimiter by counting occurrences of common delimiters
   * across the first few lines and picking the most consistent one.
   *
   * @param {string[]} firstLines — first 5 lines of the file
   * @returns {string} — the detected delimiter character
   */
  function detectDelimiter(firstLines) {
    var candidates = [',', '\t', ';', '|'];
    var bestDelim = ',';
    var bestScore = -1;

    for (var d = 0; d < candidates.length; d++) {
      var delim = candidates[d];
      var counts = [];

      for (var i = 0; i < firstLines.length; i++) {
        var line = firstLines[i];
        if (line.trim().length === 0) continue;

        // Count delimiter occurrences outside quoted fields
        var count = 0;
        var inQuote = false;
        for (var c = 0; c < line.length; c++) {
          if (line[c] === '"') {
            inQuote = !inQuote;
          } else if (!inQuote && line[c] === delim) {
            count++;
          }
        }
        counts.push(count);
      }

      if (counts.length === 0) continue;

      // Score: high count + low variance = good delimiter
      var total = 0;
      for (var s = 0; s < counts.length; s++) total += counts[s];
      var avg = total / counts.length;

      if (avg === 0) continue;

      // Compute variance
      var variance = 0;
      for (var v = 0; v < counts.length; v++) {
        var diff = counts[v] - avg;
        variance += diff * diff;
      }
      variance = variance / counts.length;

      // Consistency score: higher average with lower variance wins
      var score = avg / (1 + variance);
      if (score > bestScore) {
        bestScore = score;
        bestDelim = delim;
      }
    }

    return bestDelim;
  }

  // -------------------------------------------------------------------
  // detectHeaderRow(rows)
  // -------------------------------------------------------------------
  /**
   * Detect whether the first row is likely a header row.
   *
   * Heuristic: if first row values are all strings and subsequent rows
   * have mixed types (numbers, booleans, etc.), first row is a header.
   *
   * @param {string[][]} rows — parsed rows (arrays of string values)
   * @returns {boolean}
   */
  function detectHeaderRow(rows) {
    if (rows.length < 2) return true;

    var firstRow = rows[0];
    var sampleRows = rows.slice(1, Math.min(rows.length, 11));

    // Check if first row is all non-numeric strings
    var firstRowAllStrings = true;
    for (var i = 0; i < firstRow.length; i++) {
      var val = firstRow[i].trim();
      if (val.length > 0 && !isNaN(Number(val)) && val !== '') {
        firstRowAllStrings = false;
        break;
      }
    }

    // Check if subsequent rows contain numeric values
    var dataRowsHaveNumbers = false;
    for (var r = 0; r < sampleRows.length; r++) {
      for (var c = 0; c < sampleRows[r].length; c++) {
        var cellVal = sampleRows[r][c].trim();
        if (cellVal.length > 0 && !isNaN(Number(cellVal))) {
          dataRowsHaveNumbers = true;
          break;
        }
      }
      if (dataRowsHaveNumbers) break;
    }

    // If first row is all strings and data rows have numbers, it is a header
    if (firstRowAllStrings && dataRowsHaveNumbers) return true;

    // Additional check: header values tend to be unique and descriptive
    var uniqueFirst = {};
    var allUnique = true;
    for (var u = 0; u < firstRow.length; u++) {
      var key = firstRow[u].trim().toLowerCase();
      if (uniqueFirst[key]) { allUnique = false; break; }
      uniqueFirst[key] = true;
    }

    return allUnique && firstRowAllStrings;
  }

  // -------------------------------------------------------------------
  // parseCSV(text, options)
  // -------------------------------------------------------------------
  /**
   * Parse CSV text with auto-detection of delimiter and header row.
   *
   * Handles: quoted fields, escaped quotes (""), newlines within quotes,
   * different line endings (CRLF, LF, CR).
   *
   * @param {string} text           — raw CSV/TSV text
   * @param {Object} [options]
   * @param {string} [options.delimiter] — explicit delimiter (auto-detected if omitted)
   * @param {boolean} [options.headerRow] — explicit header row flag (auto-detected if omitted)
   * @returns {{ headers: string[], rows: Array<Object> }}
   */
  function parseCSV(text, options) {
    var opts = options || {};

    // Normalise line endings to \n
    text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // Remove BOM if present
    if (text.charCodeAt(0) === 0xFEFF) {
      text = text.substring(1);
    }

    // Auto-detect delimiter from first 5 non-empty lines
    var delimiter = opts.delimiter;
    if (!delimiter) {
      var previewLines = [];
      var previewIdx = 0;
      var previewInQuote = false;
      var previewLine = '';
      while (previewIdx < text.length && previewLines.length < 5) {
        var ch = text[previewIdx];
        if (ch === '"') {
          previewInQuote = !previewInQuote;
          previewLine += ch;
        } else if (ch === '\n' && !previewInQuote) {
          if (previewLine.trim().length > 0) {
            previewLines.push(previewLine);
          }
          previewLine = '';
        } else {
          previewLine += ch;
        }
        previewIdx++;
      }
      if (previewLine.trim().length > 0 && previewLines.length < 5) {
        previewLines.push(previewLine);
      }
      delimiter = detectDelimiter(previewLines);
    }

    // Parse all rows using a proper state machine
    var allRows = [];
    var currentRow = [];
    var currentField = '';
    var inQuotes = false;
    var pos = 0;

    while (pos <= text.length) {
      if (pos === text.length) {
        // End of input — commit final field and row
        currentRow.push(currentField);
        if (currentRow.length > 1 || (currentRow.length === 1 && currentRow[0].trim().length > 0)) {
          allRows.push(currentRow);
        }
        break;
      }

      var char = text[pos];

      if (inQuotes) {
        if (char === '"') {
          // Peek ahead for escaped quote
          if (pos + 1 < text.length && text[pos + 1] === '"') {
            currentField += '"';
            pos += 2;
          } else {
            // End of quoted field
            inQuotes = false;
            pos++;
          }
        } else {
          currentField += char;
          pos++;
        }
      } else {
        if (char === '"' && currentField.length === 0) {
          // Start of quoted field
          inQuotes = true;
          pos++;
        } else if (char === delimiter) {
          currentRow.push(currentField);
          currentField = '';
          pos++;
        } else if (char === '\n') {
          currentRow.push(currentField);
          currentField = '';
          if (currentRow.length > 1 || (currentRow.length === 1 && currentRow[0].trim().length > 0)) {
            allRows.push(currentRow);
          }
          currentRow = [];
          pos++;
        } else {
          currentField += char;
          pos++;
        }
      }
    }

    if (allRows.length === 0) {
      return { headers: [], rows: [] };
    }

    // Detect or use explicit header row setting
    var hasHeader = opts.headerRow !== undefined ? opts.headerRow : detectHeaderRow(allRows);

    var headers;
    var dataRows;
    if (hasHeader) {
      headers = allRows[0].map(function (h) { return h.trim(); });
      dataRows = allRows.slice(1);
    } else {
      // Generate column names: Column1, Column2, ...
      headers = [];
      for (var g = 0; g < allRows[0].length; g++) {
        headers.push('Column' + (g + 1));
      }
      dataRows = allRows;
    }

    // Convert to array of objects
    var objectRows = [];
    for (var r = 0; r < dataRows.length; r++) {
      var row = dataRows[r];
      var obj = {};
      for (var c = 0; c < headers.length; c++) {
        obj[headers[c]] = c < row.length ? row[c] : '';
      }
      objectRows.push(obj);
    }

    return { headers: headers, rows: objectRows };
  }

  // -------------------------------------------------------------------
  // parseExcel(arrayBuffer)
  // -------------------------------------------------------------------
  /**
   * Basic .xlsx parser — reads Sheet1 from an Excel file.
   *
   * XLSX files are ZIP archives. This performs minimal ZIP parsing to
   * extract xl/sharedStrings.xml and xl/worksheets/sheet1.xml, then
   * reads cell values from the sheet XML.
   *
   * Best-effort for simple spreadsheets; complex formatting, formulas
   * referencing other sheets, merged cells, etc. may not parse correctly.
   *
   * @param {ArrayBuffer} arrayBuffer — the raw .xlsx file bytes
   * @returns {{ headers: string[], rows: Array<Object> }}
   */
  function parseExcel(arrayBuffer) {
    var bytes = new Uint8Array(arrayBuffer);

    // ------ Minimal ZIP reader ------

    /**
     * Find all local file entries in a ZIP archive.
     * Returns an array of { name, compressedData, compressionMethod }.
     */
    function readZipEntries(data) {
      var entries = [];
      var offset = 0;

      while (offset < data.length - 4) {
        // Look for local file header signature: PK\x03\x04
        if (data[offset] === 0x50 && data[offset + 1] === 0x4B &&
            data[offset + 2] === 0x03 && data[offset + 3] === 0x04) {

          var compressionMethod = data[offset + 8] | (data[offset + 9] << 8);
          var compressedSize = data[offset + 18] | (data[offset + 19] << 8) |
                               (data[offset + 20] << 16) | (data[offset + 21] << 24);
          var uncompressedSize = data[offset + 22] | (data[offset + 23] << 8) |
                                 (data[offset + 24] << 16) | (data[offset + 25] << 24);
          var nameLen = data[offset + 26] | (data[offset + 27] << 8);
          var extraLen = data[offset + 28] | (data[offset + 29] << 8);

          var name = '';
          for (var n = 0; n < nameLen; n++) {
            name += String.fromCharCode(data[offset + 30 + n]);
          }

          var dataStart = offset + 30 + nameLen + extraLen;

          // Handle data descriptor (bit 3 of general purpose flag)
          var gpFlag = data[offset + 6] | (data[offset + 7] << 8);
          var hasDataDescriptor = (gpFlag & 0x08) !== 0;

          if (hasDataDescriptor && compressedSize === 0) {
            // Need to find the data descriptor to get the real size.
            // Search for PK signature of next entry or data descriptor signature.
            var searchPos = dataStart;
            while (searchPos < data.length - 4) {
              if (data[searchPos] === 0x50 && data[searchPos + 1] === 0x4B) {
                break;
              }
              searchPos++;
            }
            // Data descriptor is 12 or 16 bytes before the next PK signature
            // Try to find PK\x07\x08 (data descriptor signature)
            if (searchPos >= dataStart + 16 &&
                data[searchPos - 16] === 0x50 && data[searchPos - 16 + 1] === 0x4B &&
                data[searchPos - 16 + 2] === 0x07 && data[searchPos - 16 + 3] === 0x08) {
              compressedSize = searchPos - dataStart - 16;
            } else if (searchPos >= dataStart + 12) {
              compressedSize = searchPos - dataStart - 12;
            } else {
              compressedSize = searchPos - dataStart;
            }
            if (compressedSize < 0) compressedSize = 0;
          }

          var compressedData = data.slice(dataStart, dataStart + compressedSize);

          entries.push({
            name: name,
            compressionMethod: compressionMethod,
            compressedData: compressedData,
            uncompressedSize: uncompressedSize
          });

          offset = dataStart + compressedSize;
        } else {
          offset++;
        }
      }

      return entries;
    }

    /**
     * Decompress a DEFLATE-compressed buffer using the browser's
     * DecompressionStream API (where available) or a minimal inflate.
     * Falls back to returning raw data if decompression fails.
     */
    function decompressEntry(entry) {
      if (entry.compressionMethod === 0) {
        // Stored (no compression)
        return Promise.resolve(entry.compressedData);
      }

      // Method 8 = DEFLATE
      if (entry.compressionMethod === 8) {
        // Use DecompressionStream if available (modern browsers)
        if (typeof DecompressionStream !== 'undefined') {
          var rawStream = new Blob([entry.compressedData]).stream();
          var ds = new DecompressionStream('deflate-raw');
          var decompressed = rawStream.pipeThrough(ds);
          return new Response(decompressed).arrayBuffer().then(function (buf) {
            return new Uint8Array(buf);
          });
        }

        // Fallback: return raw data (will likely produce garbled results)
        return Promise.resolve(entry.compressedData);
      }

      // Unknown compression method
      return Promise.resolve(entry.compressedData);
    }

    /**
     * Decode a Uint8Array as UTF-8 string.
     */
    function decodeUtf8(data) {
      if (typeof TextDecoder !== 'undefined') {
        return new TextDecoder('utf-8').decode(data);
      }
      // Fallback for very old browsers
      var str = '';
      for (var i = 0; i < data.length; i++) {
        str += String.fromCharCode(data[i]);
      }
      return str;
    }

    /**
     * Parse shared strings from xl/sharedStrings.xml.
     * Each <si> element contains one string; we extract the text content.
     */
    function parseSharedStrings(xml) {
      var strings = [];
      // Match each <si>...</si> block
      var siRegex = /<si[^>]*>([\s\S]*?)<\/si>/g;
      var match;
      while ((match = siRegex.exec(xml)) !== null) {
        var siContent = match[1];
        // Extract text from <t> elements within this <si>
        var text = '';
        var tRegex = /<t[^>]*>([\s\S]*?)<\/t>/g;
        var tMatch;
        while ((tMatch = tRegex.exec(siContent)) !== null) {
          text += decodeXmlEntities(tMatch[1]);
        }
        strings.push(text);
      }
      return strings;
    }

    /**
     * Decode basic XML entities.
     */
    function decodeXmlEntities(str) {
      return str
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&apos;/g, "'");
    }

    /**
     * Parse column letter reference (e.g. "A", "B", "AA") to 0-based index.
     */
    function colRefToIndex(ref) {
      var col = 0;
      for (var i = 0; i < ref.length; i++) {
        col = col * 26 + (ref.charCodeAt(i) - 64);
      }
      return col - 1;
    }

    /**
     * Parse xl/worksheets/sheet1.xml and return rows of cell values.
     */
    function parseSheet(xml, sharedStrings) {
      var rows = [];
      // Match each <row> element
      var rowRegex = /<row[^>]*>([\s\S]*?)<\/row>/g;
      var rowMatch;

      while ((rowMatch = rowRegex.exec(xml)) !== null) {
        var rowContent = rowMatch[1];
        var cells = [];

        // Match each <c> cell element
        var cellRegex = /<c\s([^>]*)(?:\/>|>([\s\S]*?)<\/c>)/g;
        var cellMatch;

        while ((cellMatch = cellRegex.exec(rowContent)) !== null) {
          var attrs = cellMatch[1];
          var cellContent = cellMatch[2] || '';

          // Extract cell reference (r attribute) and type (t attribute)
          var refMatch = attrs.match(/r="([A-Z]+)\d+"/);
          var typeMatch = attrs.match(/t="([^"]+)"/);

          var colIndex = 0;
          if (refMatch) {
            colIndex = colRefToIndex(refMatch[1]);
          }

          var cellType = typeMatch ? typeMatch[1] : '';
          var value = '';

          // Extract <v> value
          var vMatch = cellContent.match(/<v[^>]*>([\s\S]*?)<\/v>/);
          if (vMatch) {
            value = vMatch[1];
          }

          // Resolve value based on type
          if (cellType === 's' && sharedStrings) {
            // Shared string reference
            var ssIdx = parseInt(value, 10);
            value = (ssIdx >= 0 && ssIdx < sharedStrings.length)
              ? sharedStrings[ssIdx]
              : '';
          } else if (cellType === 'inlineStr') {
            // Inline string — extract from <is><t>...</t></is>
            var isMatch = cellContent.match(/<is[^>]*>[\s\S]*?<t[^>]*>([\s\S]*?)<\/t>/);
            value = isMatch ? decodeXmlEntities(isMatch[1]) : '';
          } else {
            value = decodeXmlEntities(value);
          }

          // Ensure cells array is large enough
          while (cells.length <= colIndex) {
            cells.push('');
          }
          cells[colIndex] = value;
        }

        if (cells.length > 0) {
          rows.push(cells);
        }
      }

      return rows;
    }

    // ------ Main Excel parsing logic ------

    var zipEntries = readZipEntries(bytes);

    // Find required files
    var sharedStringsEntry = null;
    var sheet1Entry = null;
    for (var e = 0; e < zipEntries.length; e++) {
      var entryName = zipEntries[e].name.toLowerCase();
      if (entryName === 'xl/sharedstrings.xml') {
        sharedStringsEntry = zipEntries[e];
      }
      if (entryName === 'xl/worksheets/sheet1.xml') {
        sheet1Entry = zipEntries[e];
      }
    }

    if (!sheet1Entry) {
      return Promise.resolve({ headers: [], rows: [] });
    }

    // Decompress entries
    var decompressPromises = [];
    decompressPromises.push(decompressEntry(sheet1Entry));
    if (sharedStringsEntry) {
      decompressPromises.push(decompressEntry(sharedStringsEntry));
    } else {
      decompressPromises.push(Promise.resolve(null));
    }

    return Promise.all(decompressPromises).then(function (results) {
      var sheetXml = decodeUtf8(results[0]);
      var sharedStrings = results[1] ? parseSharedStrings(decodeUtf8(results[1])) : [];

      var allRows = parseSheet(sheetXml, sharedStrings);

      if (allRows.length === 0) {
        return { headers: [], rows: [] };
      }

      // Normalise row lengths to match the widest row
      var maxCols = 0;
      for (var r = 0; r < allRows.length; r++) {
        if (allRows[r].length > maxCols) maxCols = allRows[r].length;
      }
      for (var r2 = 0; r2 < allRows.length; r2++) {
        while (allRows[r2].length < maxCols) {
          allRows[r2].push('');
        }
      }

      // Detect header row
      var hasHeader = detectHeaderRow(allRows);

      var headers;
      var dataRows;
      if (hasHeader) {
        headers = allRows[0].map(function (h) { return h.trim() || ('Column' + (allRows[0].indexOf(h) + 1)); });
        dataRows = allRows.slice(1);
      } else {
        headers = [];
        for (var g = 0; g < maxCols; g++) {
          headers.push('Column' + (g + 1));
        }
        dataRows = allRows;
      }

      // Deduplicate header names
      var seen = {};
      headers = headers.map(function (h) {
        if (seen[h]) {
          var suffix = 2;
          while (seen[h + '_' + suffix]) suffix++;
          h = h + '_' + suffix;
        }
        seen[h] = true;
        return h;
      });

      // Convert to array of objects
      var objectRows = [];
      for (var dr = 0; dr < dataRows.length; dr++) {
        var obj = {};
        for (var col = 0; col < headers.length; col++) {
          obj[headers[col]] = col < dataRows[dr].length ? dataRows[dr][col] : '';
        }
        objectRows.push(obj);
      }

      return { headers: headers, rows: objectRows };
    });
  }

  // -------------------------------------------------------------------
  // transformGoogleSheetsUrl(url)
  // -------------------------------------------------------------------
  /**
   * Convert a Google Sheets edit/view URL to a published CSV export URL.
   *
   * Input:  https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit#gid=0
   * Output: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=0
   *
   * @param {string} url
   * @returns {string} — the CSV export URL, or the original URL if not a Sheets URL
   */
  function transformGoogleSheetsUrl(url) {
    // Match Google Sheets URL patterns
    var sheetsRegex = /^https?:\/\/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9_-]+)(\/.*)?/;
    var match = url.match(sheetsRegex);
    if (!match) return url;

    var spreadsheetId = match[1];
    var rest = match[2] || '';

    // Extract gid if present
    var gidMatch = rest.match(/gid=(\d+)/);
    var gid = gidMatch ? gidMatch[1] : '0';

    return 'https://docs.google.com/spreadsheets/d/' + spreadsheetId +
           '/export?format=csv&gid=' + gid;
  }

  // -------------------------------------------------------------------
  // normaliseUrl(url)
  // -------------------------------------------------------------------
  /**
   * Detect and transform special URLs for direct download.
   *
   * Handles:
   *   - Google Sheets → export?format=csv
   *   - Dropbox → append ?dl=1
   *   - GitHub blob URLs → raw.githubusercontent.com
   *
   * @param {string} url
   * @returns {string} — the normalised URL
   */
  function normaliseUrl(url) {
    url = url.trim();

    // Google Sheets
    if (url.indexOf('docs.google.com/spreadsheets') !== -1) {
      // Only transform if it is not already an export URL
      if (url.indexOf('/export') === -1) {
        return transformGoogleSheetsUrl(url);
      }
      return url;
    }

    // Dropbox — ensure direct download
    if (url.indexOf('dropbox.com') !== -1) {
      // Replace dl=0 with dl=1, or add dl=1
      if (url.indexOf('dl=0') !== -1) {
        return url.replace('dl=0', 'dl=1');
      }
      if (url.indexOf('dl=1') === -1) {
        var sep = url.indexOf('?') !== -1 ? '&' : '?';
        return url + sep + 'dl=1';
      }
      return url;
    }

    // GitHub blob → raw
    // https://github.com/user/repo/blob/branch/path
    // → https://raw.githubusercontent.com/user/repo/branch/path
    var ghBlobRegex = /^https?:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\/(.+)/;
    var ghMatch = url.match(ghBlobRegex);
    if (ghMatch) {
      return 'https://raw.githubusercontent.com/' + ghMatch[1] + '/' +
             ghMatch[2] + '/' + ghMatch[3];
    }

    return url;
  }

  // -------------------------------------------------------------------
  // toDataset(name, headers, rows, sourceUrl)
  // -------------------------------------------------------------------
  /**
   * Convert parsed data into moke's dataset format.
   *
   * @param {string} name           — dataset name
   * @param {string[]} headers      — column headers
   * @param {Array<Object>} rows    — array of row objects
   * @param {string} sourceUrl      — original source URL
   * @returns {{ name: string, headers: string[], rows: Array<Object>, meta: Object, source: string }}
   */
  function toDataset(name, headers, rows, sourceUrl) {
    return {
      name: name || 'Untitled',
      headers: headers,
      rows: rows,
      meta: {
        rowCount: rows.length,
        columnCount: headers.length,
        importedAt: new Date().toISOString(),
        sourceType: 'url'
      },
      source: sourceUrl
    };
  }

  // -------------------------------------------------------------------
  // importFromUrl(url, options)
  // -------------------------------------------------------------------
  /**
   * Fetch and parse a CSV or Excel file from a URL.
   *
   * Fetches via the loke proxy endpoint, auto-detects file type,
   * parses the content, and returns a dataset.
   *
   * @param {string} url         — the URL to fetch
   * @param {Object} [options]
   * @param {string} [options.delimiter]  — explicit delimiter (auto-detected if omitted)
   * @param {string} [options.encoding]   — explicit encoding (auto-detected if omitted)
   * @param {boolean} [options.headerRow] — explicit header flag (auto-detected if omitted)
   * @param {string} [options.name]       — dataset name (defaults to filename or 'Imported Data')
   * @param {function} [options.onProgress] — progress callback: fn(message)
   * @returns {Promise<{ name: string, headers: string[], rows: Array<Object>, meta: Object, source: string }>}
   */
  function importFromUrl(url, options) {
    var opts = options || {};
    var progress = opts.onProgress || function () {};
    var originalUrl = url;

    // Normalise the URL for special services
    url = normaliseUrl(url);

    progress('Preparing request\u2026');

    // Build the proxy request
    var proxyUrl = ((window.LOKE_URL || '') || '').replace(/\/+$/, '') + '/api/proxy';

    progress('Fetching file\u2026');

    return fetch(proxyUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url,
        method: 'GET',
        responseType: 'auto'
      })
    }).then(function (response) {
      if (!response.ok) {
        throw new Error('Failed to fetch URL: HTTP ' + response.status);
      }

      var contentType = response.headers.get('content-type') || '';
      var fileType = detectFileType(url, contentType);

      progress('Downloaded. Detecting file type\u2026');

      // Derive a name from the URL if not provided
      var name = opts.name;
      if (!name) {
        var pathParts = url.split('?')[0].split('/');
        var lastPart = pathParts[pathParts.length - 1] || 'Imported Data';
        // Strip extension for the name
        name = lastPart.replace(/\.(csv|tsv|xlsx?)$/i, '') || 'Imported Data';
        // Decode URI components
        try { name = decodeURIComponent(name); } catch (e) { /* ignore */ }
      }

      // If type is unknown, try to determine from response body
      if (fileType === 'unknown' || fileType === 'csv' || fileType === 'tsv') {
        // Text-based: read as text
        return response.text().then(function (text) {
          progress('Parsing\u2026');

          // Re-check: if we thought it was unknown but content looks like CSV, treat as CSV
          if (fileType === 'unknown') {
            fileType = 'csv';
          }

          var delimiter = opts.delimiter;
          if (fileType === 'tsv' && !delimiter) {
            delimiter = '\t';
          }

          var parsed = parseCSV(text, {
            delimiter: delimiter,
            headerRow: opts.headerRow
          });

          progress('Done. ' + parsed.rows.length + ' rows loaded.');

          return toDataset(name, parsed.headers, parsed.rows, originalUrl);
        });
      }

      if (fileType === 'excel') {
        return response.arrayBuffer().then(function (buffer) {
          progress('Parsing Excel file\u2026');

          return parseExcel(buffer).then(function (parsed) {
            progress('Done. ' + parsed.rows.length + ' rows loaded.');
            return toDataset(name, parsed.headers, parsed.rows, originalUrl);
          });
        });
      }

      throw new Error('Unsupported file type: ' + fileType);
    });
  }

  // -------------------------------------------------------------------
  // renderImportForm(containerId)
  // -------------------------------------------------------------------
  /**
   * Render an URL import form into a container element.
   *
   * Creates a form with:
   *   - URL input field
   *   - Delimiter dropdown (auto/comma/tab/semicolon/pipe)
   *   - Encoding dropdown (auto/utf-8/latin1)
   *   - Import button
   *   - Progress/status indicator
   *
   * @param {string} containerId — the ID of the container element
   * @returns {{ getResult: function, reset: function }}
   */
  function renderImportForm(containerId) {
    var container = document.getElementById(containerId);
    if (!container) {
      throw new Error('Container element not found: ' + containerId);
    }

    var formId = containerId + '_urlimport';
    var result = null;

    var html = [
      '<div class="moke-url-import" id="' + formId + '">',
      '  <div class="moke-url-import__field">',
      '    <label for="' + formId + '_url">URL</label>',
      '    <input type="url" id="' + formId + '_url" ',
      '           placeholder="https://example.com/data.csv or Google Sheets URL" ',
      '           autocomplete="off" />',
      '  </div>',
      '  <div class="moke-url-import__options">',
      '    <div class="moke-url-import__field moke-url-import__field--small">',
      '      <label for="' + formId + '_delimiter">Delimiter</label>',
      '      <select id="' + formId + '_delimiter">',
      '        <option value="auto" selected>Auto-detect</option>',
      '        <option value=",">Comma (,)</option>',
      '        <option value="&#9;">Tab (\\t)</option>',
      '        <option value=";">Semicolon (;)</option>',
      '        <option value="|">Pipe (|)</option>',
      '      </select>',
      '    </div>',
      '    <div class="moke-url-import__field moke-url-import__field--small">',
      '      <label for="' + formId + '_encoding">Encoding</label>',
      '      <select id="' + formId + '_encoding">',
      '        <option value="auto" selected>Auto-detect</option>',
      '        <option value="utf-8">UTF-8</option>',
      '        <option value="latin1">Latin-1 (ISO-8859-1)</option>',
      '      </select>',
      '    </div>',
      '  </div>',
      '  <div class="moke-url-import__actions">',
      '    <button type="button" id="' + formId + '_btn" class="btn btn-primary">',
      '      Import',
      '    </button>',
      '    <span id="' + formId + '_status" class="moke-url-import__status"></span>',
      '  </div>',
      '</div>'
    ].join('\n');

    container.innerHTML = html;

    // Bind events
    var urlInput = document.getElementById(formId + '_url');
    var delimSelect = document.getElementById(formId + '_delimiter');
    var encodingSelect = document.getElementById(formId + '_encoding');
    var importBtn = document.getElementById(formId + '_btn');
    var statusEl = document.getElementById(formId + '_status');

    function setStatus(msg, isError) {
      statusEl.textContent = msg;
      statusEl.style.color = isError ? '#c0392b' : '#666';
    }

    function setEnabled(enabled) {
      importBtn.disabled = !enabled;
      urlInput.disabled = !enabled;
      delimSelect.disabled = !enabled;
      encodingSelect.disabled = !enabled;
    }

    importBtn.addEventListener('click', function () {
      var url = urlInput.value.trim();
      if (!url) {
        setStatus('Please enter a URL.', true);
        return;
      }

      // Basic URL validation
      if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0) {
        setStatus('URL must start with http:// or https://', true);
        return;
      }

      setEnabled(false);
      setStatus('Starting import\u2026', false);
      result = null;

      var delimValue = delimSelect.value;
      var delimiter = delimValue === 'auto' ? undefined : delimValue;

      var encodingValue = encodingSelect.value;
      var encoding = encodingValue === 'auto' ? undefined : encodingValue;

      importFromUrl(url, {
        delimiter: delimiter,
        encoding: encoding,
        onProgress: function (msg) {
          setStatus(msg, false);
        }
      }).then(function (dataset) {
        result = dataset;
        setStatus('Imported ' + dataset.rows.length + ' rows, ' +
                  dataset.headers.length + ' columns.', false);
        setEnabled(true);

        // Dispatch custom event so parent code can react
        var event;
        try {
          event = new CustomEvent('moke-url-import', { detail: dataset });
        } catch (e) {
          // IE fallback
          event = document.createEvent('CustomEvent');
          event.initCustomEvent('moke-url-import', true, true, dataset);
        }
        container.dispatchEvent(event);
      }).catch(function (err) {
        setStatus('Error: ' + err.message, true);
        setEnabled(true);
      });
    });

    // Allow Enter key to trigger import
    urlInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.keyCode === 13) {
        e.preventDefault();
        importBtn.click();
      }
    });

    return {
      /** Get the last successfully imported dataset, or null. */
      getResult: function () { return result; },

      /** Reset the form to its initial state. */
      reset: function () {
        result = null;
        urlInput.value = '';
        delimSelect.value = 'auto';
        encodingSelect.value = 'auto';
        setStatus('', false);
        setEnabled(true);
      }
    };
  }

  // -------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------
  window.MokeUrlImport = {
    importFromUrl:           importFromUrl,
    detectFileType:          detectFileType,
    detectDelimiter:         detectDelimiter,
    detectHeaderRow:         detectHeaderRow,
    parseCSV:                parseCSV,
    parseExcel:              parseExcel,
    transformGoogleSheetsUrl: transformGoogleSheetsUrl,
    normaliseUrl:            normaliseUrl,
    renderImportForm:        renderImportForm,
    toDataset:               toDataset
  };

})();
