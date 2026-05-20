/**
 * MK9.6 — data.gov.au Integration for Moke
 *
 * Discover and connect to Australian government open data via the CKAN API.
 * Search datasets, filter by format/organisation/tags, download CSV data,
 * and auto-configure API connections.
 *
 * All network requests go through the loke proxy to avoid CORS issues.
 * No external dependencies.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  var BASE_URL = 'https://data.gov.au/api/3/action';

  /**
   * Pre-populated suggested datasets for quick access.
   */
  var SUGGESTED = [
    { query: 'ABS employment statistics', label: 'ABS Employment Statistics', org: 'Australian Bureau of Statistics' },
    { query: 'Medicare benefits schedule', label: 'Medicare Statistics', org: 'Department of Health' },
    { query: 'Bureau of Meteorology weather observations', label: 'Bureau of Meteorology', org: 'Bureau of Meteorology' },
    { query: 'NSW transport train delays', label: 'NSW Transport', org: 'Transport for NSW' },
    { query: 'water quality monitoring', label: 'Water Quality Data', org: '' },
    { query: 'energy consumption renewable', label: 'Energy & Renewables', org: '' }
  ];

  /**
   * Format badge colour map for dataset cards.
   */
  var FORMAT_COLOURS = {
    'CSV':  { bg: '#2d6a4f', fg: '#b7e4c7' },
    'JSON': { bg: '#1d3557', fg: '#a8dadc' },
    'API':  { bg: '#6a040f', fg: '#ffb3c1' },
    'XML':  { bg: '#5a189a', fg: '#e0aaff' },
    'XLS':  { bg: '#774936', fg: '#ddb892' },
    'XLSX': { bg: '#774936', fg: '#ddb892' },
    'GeoJSON': { bg: '#3a5a40', fg: '#a3b18a' },
    'WMS':  { bg: '#6a040f', fg: '#ffb3c1' },
    'WFS':  { bg: '#6a040f', fg: '#ffb3c1' }
  };

  var DEFAULT_FORMAT_COLOUR = { bg: '#495057', fg: '#dee2e6' };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Resolve the loke proxy URL. Falls back to current origin if LOKE_URL is
   * not set on the window.
   */
  function proxyUrl() {
    var base = (window.LOKE_URL || '') || '';
    return base.replace(/\/+$/, '') + '/api/proxy';
  }

  /**
   * Make a GET request through the loke proxy.
   *
   * @param {string} targetUrl - The upstream URL to fetch.
   * @returns {Promise<*>} Parsed JSON response body.
   */
  async function proxyGet(targetUrl) {
    var response = await fetch(proxyUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-Loke-Target': targetUrl,
        'X-Loke-Method': 'GET'
      },
      body: JSON.stringify({ _proxyMethod: 'GET' })
    });

    if (!response.ok) {
      var errText = await response.text();
      throw new Error('Proxy request failed (' + response.status + '): ' + errText);
    }

    return response.json();
  }

  /**
   * Fetch raw text content through the loke proxy.
   *
   * @param {string} targetUrl - The upstream URL to fetch.
   * @returns {Promise<string>} Response body as text.
   */
  async function proxyGetText(targetUrl) {
    var response = await fetch(proxyUrl(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/csv, text/plain, */*',
        'X-Loke-Target': targetUrl,
        'X-Loke-Method': 'GET'
      },
      body: JSON.stringify({ _proxyMethod: 'GET' })
    });

    if (!response.ok) {
      var errText = await response.text();
      throw new Error('Proxy request failed (' + response.status + '): ' + errText);
    }

    return response.text();
  }

  /**
   * Truncate text to a maximum length, appending ellipsis if needed.
   */
  function truncate(text, maxLen) {
    if (!text) return '';
    if (text.length <= maxLen) return text;
    return text.substring(0, maxLen - 1) + '\u2026';
  }

  /**
   * Escape HTML special characters to prevent XSS.
   */
  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Format an ISO date string into a human-readable form.
   */
  function formatDate(isoStr) {
    if (!isoStr) return 'Unknown';
    try {
      var d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleDateString('en-AU', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    } catch (e) {
      return isoStr;
    }
  }

  /**
   * Format byte size into human-readable form.
   */
  function formatSize(bytes) {
    if (!bytes && bytes !== 0) return '';
    var n = Number(bytes);
    if (isNaN(n) || n === 0) return '';
    var units = ['B', 'KB', 'MB', 'GB'];
    var idx = 0;
    while (n >= 1024 && idx < units.length - 1) {
      n /= 1024;
      idx++;
    }
    return n.toFixed(idx === 0 ? 0 : 1) + ' ' + units[idx];
  }

  /**
   * Extract unique formats from a CKAN package's resources.
   */
  function extractFormats(resources) {
    var seen = {};
    var formats = [];
    if (!Array.isArray(resources)) return formats;
    for (var i = 0; i < resources.length; i++) {
      var fmt = (resources[i].format || '').toUpperCase().trim();
      if (fmt && !seen[fmt]) {
        seen[fmt] = true;
        formats.push(fmt);
      }
    }
    return formats;
  }

  // ---------------------------------------------------------------------------
  // CSV Parser
  // ---------------------------------------------------------------------------

  /**
   * Parse CSV text into headers and rows.
   *
   * Handles:
   * - Quoted fields (double quotes)
   * - Commas within quoted values
   * - Newlines within quoted values
   * - Escaped quotes (doubled: "")
   * - Common encodings (UTF-8 BOM stripped)
   *
   * @param {string} csvText - Raw CSV text.
   * @returns {{ headers: string[], rows: string[][] }}
   */
  function parseCSV(csvText) {
    if (!csvText || typeof csvText !== 'string') {
      return { headers: [], rows: [] };
    }

    // Strip UTF-8 BOM if present
    if (csvText.charCodeAt(0) === 0xFEFF) {
      csvText = csvText.substring(1);
    }

    var rows = [];
    var currentRow = [];
    var currentField = '';
    var inQuotes = false;
    var i = 0;
    var len = csvText.length;

    while (i < len) {
      var ch = csvText[i];

      if (inQuotes) {
        if (ch === '"') {
          // Check for escaped quote (doubled)
          if (i + 1 < len && csvText[i + 1] === '"') {
            currentField += '"';
            i += 2;
          } else {
            // End of quoted field
            inQuotes = false;
            i++;
          }
        } else {
          currentField += ch;
          i++;
        }
      } else {
        if (ch === '"') {
          // Start of quoted field
          inQuotes = true;
          i++;
        } else if (ch === ',') {
          currentRow.push(currentField.trim());
          currentField = '';
          i++;
        } else if (ch === '\r') {
          // Handle \r\n and \r line endings
          currentRow.push(currentField.trim());
          currentField = '';
          if (currentRow.length > 0) {
            rows.push(currentRow);
          }
          currentRow = [];
          i++;
          if (i < len && csvText[i] === '\n') {
            i++;
          }
        } else if (ch === '\n') {
          currentRow.push(currentField.trim());
          currentField = '';
          if (currentRow.length > 0) {
            rows.push(currentRow);
          }
          currentRow = [];
          i++;
        } else {
          currentField += ch;
          i++;
        }
      }
    }

    // Handle last field and row
    if (currentField || currentRow.length > 0) {
      currentRow.push(currentField.trim());
      if (currentRow.length > 0) {
        rows.push(currentRow);
      }
    }

    if (rows.length === 0) {
      return { headers: [], rows: [] };
    }

    var headers = rows[0];
    var dataRows = rows.slice(1);

    // Remove trailing empty rows
    while (dataRows.length > 0) {
      var lastRow = dataRows[dataRows.length - 1];
      var allEmpty = true;
      for (var j = 0; j < lastRow.length; j++) {
        if (lastRow[j] !== '') {
          allEmpty = false;
          break;
        }
      }
      if (allEmpty) {
        dataRows.pop();
      } else {
        break;
      }
    }

    return { headers: headers, rows: dataRows };
  }

  // ---------------------------------------------------------------------------
  // Core API
  // ---------------------------------------------------------------------------

  /**
   * Search data.gov.au datasets via the CKAN package_search API.
   *
   * @param {string} query - Free-text search query.
   * @param {object} [options] - Search options.
   * @param {string} [options.format] - Filter by resource format (CSV, JSON, API).
   * @param {string} [options.organisation] - Filter by organisation name.
   * @param {string|string[]} [options.tags] - Filter by tag(s).
   * @param {number} [options.rows] - Number of results to return (default 10).
   * @param {number} [options.start] - Result offset for pagination (default 0).
   * @returns {Promise<{ count: number, results: object[] }>}
   */
  async function search(query, options) {
    var opts = options || {};
    var rows = opts.rows || 10;
    var start = opts.start || 0;

    // Build the search query with optional filters
    var fqParts = [];
    if (opts.format) {
      fqParts.push('res_format:' + opts.format.toUpperCase());
    }
    if (opts.organisation) {
      fqParts.push('organization:' + opts.organisation);
    }
    if (opts.tags) {
      var tagList = Array.isArray(opts.tags) ? opts.tags : [opts.tags];
      for (var i = 0; i < tagList.length; i++) {
        fqParts.push('tags:' + tagList[i]);
      }
    }

    var params = [
      'q=' + encodeURIComponent(query || ''),
      'rows=' + rows,
      'start=' + start
    ];
    if (fqParts.length > 0) {
      params.push('fq=' + encodeURIComponent(fqParts.join(' AND ')));
    }

    var url = BASE_URL + '/package_search?' + params.join('&');
    var json = await proxyGet(url);

    if (!json.success) {
      throw new Error('CKAN API error: ' + JSON.stringify(json.error || 'Unknown error'));
    }

    var resultData = json.result || {};
    var packages = resultData.results || [];

    // Normalise each package into our standard format
    var results = packages.map(function (pkg) {
      return {
        id: pkg.id || pkg.name,
        title: pkg.title || pkg.name || 'Untitled',
        description: pkg.notes || '',
        organisation: (pkg.organization && pkg.organization.title) || '',
        formats: extractFormats(pkg.resources),
        resources: pkg.resources || [],
        lastUpdated: pkg.metadata_modified || pkg.metadata_created || '',
        tags: (pkg.tags || []).map(function (t) { return t.display_name || t.name; }),
        url: pkg.url || ''
      };
    });

    return {
      count: resultData.count || 0,
      results: results
    };
  }

  /**
   * Get full detail for a single dataset by ID.
   *
   * @param {string} datasetId - The CKAN package ID or name.
   * @returns {Promise<object>} Normalised dataset object.
   */
  async function getDataset(datasetId) {
    if (!datasetId) {
      throw new Error('Dataset ID is required');
    }

    var url = BASE_URL + '/package_show?id=' + encodeURIComponent(datasetId);
    var json = await proxyGet(url);

    if (!json.success) {
      throw new Error('CKAN API error: ' + JSON.stringify(json.error || 'Unknown error'));
    }

    var pkg = json.result || {};
    return {
      id: pkg.id || pkg.name,
      title: pkg.title || pkg.name || 'Untitled',
      description: pkg.notes || '',
      organisation: (pkg.organization && pkg.organization.title) || '',
      formats: extractFormats(pkg.resources),
      resources: pkg.resources || [],
      lastUpdated: pkg.metadata_modified || pkg.metadata_created || '',
      tags: (pkg.tags || []).map(function (t) { return t.display_name || t.name; }),
      url: pkg.url || ''
    };
  }

  /**
   * List resources (files/APIs) for a dataset, normalised to a standard shape.
   *
   * @param {object} dataset - A dataset object (from search() or getDataset()).
   * @returns {object[]} Array of resource objects.
   */
  function getResources(dataset) {
    if (!dataset || !Array.isArray(dataset.resources)) {
      return [];
    }

    return dataset.resources.map(function (r) {
      return {
        id: r.id || '',
        name: r.name || r.description || 'Unnamed resource',
        format: (r.format || '').toUpperCase().trim(),
        url: r.url || '',
        size: r.size || null,
        lastModified: r.last_modified || r.created || '',
        description: r.description || ''
      };
    });
  }

  /**
   * Download a CSV resource via loke proxy and convert to moke dataset format.
   *
   * @param {string} resourceUrl - The URL of the CSV resource.
   * @param {string} [name] - Optional name for the dataset.
   * @returns {Promise<object>} Moke dataset: { name, headers, rows, meta, source }.
   */
  async function downloadCSV(resourceUrl, name) {
    if (!resourceUrl) {
      throw new Error('Resource URL is required');
    }

    var csvText = await proxyGetText(resourceUrl);
    var parsed = parseCSV(csvText);

    return {
      name: name || 'data.gov.au dataset',
      headers: parsed.headers,
      rows: parsed.rows,
      meta: {
        rowCount: parsed.rows.length,
        columnCount: parsed.headers.length,
        sourceUrl: resourceUrl,
        downloadedAt: new Date().toISOString()
      },
      source: 'data.gov.au'
    };
  }

  /**
   * Auto-configure a connection from an API-type resource.
   *
   * @param {object} resource - A resource object (from getResources()).
   * @returns {object} Connection configuration for moke.
   */
  function toConnectionConfig(resource) {
    if (!resource) {
      throw new Error('Resource is required');
    }

    var format = (resource.format || '').toUpperCase();
    var isApi = format === 'API' || format === 'WMS' || format === 'WFS';

    return {
      name: resource.name || 'data.gov.au connection',
      type: isApi ? 'api' : 'file',
      url: resource.url || '',
      format: format,
      method: 'GET',
      headers: {},
      auth: null,
      source: 'data.gov.au',
      resourceId: resource.id || '',
      description: resource.description || '',
      lastModified: resource.lastModified || ''
    };
  }

  // ---------------------------------------------------------------------------
  // UI Rendering
  // ---------------------------------------------------------------------------

  /**
   * Render a format badge with colour coding.
   */
  function renderFormatBadge(format) {
    var colours = FORMAT_COLOURS[format] || DEFAULT_FORMAT_COLOUR;
    return '<span style="display:inline-block;padding:2px 8px;border-radius:3px;' +
      'font-size:11px;font-weight:600;margin-right:4px;margin-bottom:2px;' +
      'background:' + colours.bg + ';color:' + colours.fg + ';">' +
      escapeHtml(format) + '</span>';
  }

  /**
   * Render a dataset card HTML string.
   *
   * @param {object} dataset - Normalised dataset object.
   * @returns {string} HTML string for the card.
   */
  function renderDatasetCard(dataset) {
    var formatBadges = '';
    for (var i = 0; i < dataset.formats.length; i++) {
      formatBadges += renderFormatBadge(dataset.formats[i]);
    }

    var orgBadge = '';
    if (dataset.organisation) {
      orgBadge = '<span style="display:inline-block;padding:2px 8px;border-radius:3px;' +
        'font-size:11px;background:var(--bg-tertiary, #2d2d2d);color:var(--text-secondary, #aaa);' +
        'margin-right:8px;">' + escapeHtml(dataset.organisation) + '</span>';
    }

    var descExcerpt = truncate(dataset.description, 200);
    // Strip HTML tags from description for clean display
    var cleanDesc = descExcerpt.replace(/<[^>]*>/g, '');

    var html = '<div class="datagov-card" data-dataset-id="' + escapeHtml(dataset.id) + '" style="' +
      'border:1px solid var(--border-colour, #333);border-radius:6px;padding:12px 16px;' +
      'margin-bottom:8px;background:var(--bg-secondary, #1e1e1e);cursor:pointer;' +
      'transition:border-color 0.15s;"' +
      ' onmouseover="this.style.borderColor=\'var(--accent, #4fc3f7)\'"' +
      ' onmouseout="this.style.borderColor=\'var(--border-colour, #333)\'">' +
      '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">' +
        '<div style="font-weight:600;color:var(--text-primary, #eee);font-size:14px;flex:1;">' +
          escapeHtml(dataset.title) +
        '</div>' +
        '<div style="font-size:11px;color:var(--text-muted, #666);white-space:nowrap;margin-left:12px;">' +
          formatDate(dataset.lastUpdated) +
        '</div>' +
      '</div>' +
      '<div style="margin-bottom:6px;">' + orgBadge + formatBadges + '</div>' +
      '<div style="font-size:12px;color:var(--text-secondary, #aaa);line-height:1.4;margin-bottom:8px;">' +
        escapeHtml(cleanDesc) +
      '</div>' +
      '<div style="display:flex;gap:6px;">' +
        '<button class="datagov-load-btn" data-dataset-id="' + escapeHtml(dataset.id) + '" style="' +
          'padding:4px 12px;border-radius:4px;border:1px solid var(--accent, #4fc3f7);' +
          'background:transparent;color:var(--accent, #4fc3f7);font-size:12px;cursor:pointer;' +
          'transition:background 0.15s,color 0.15s;"' +
          ' onmouseover="this.style.background=\'var(--accent, #4fc3f7)\';this.style.color=\'#000\'"' +
          ' onmouseout="this.style.background=\'transparent\';this.style.color=\'var(--accent, #4fc3f7)\'"' +
        '>Load</button>' +
      '</div>' +
    '</div>';

    return html;
  }

  /**
   * Render a resource list HTML string.
   *
   * @param {object[]} resources - Array of normalised resource objects.
   * @param {string} [datasetName] - Name of the parent dataset.
   * @returns {string} HTML string for the resource list.
   */
  function renderResources(resources, datasetName) {
    if (!resources || resources.length === 0) {
      return '<div style="color:var(--text-muted, #666);font-size:13px;padding:8px 0;">No resources available.</div>';
    }

    var html = '<div class="datagov-resources" style="margin-top:8px;">';

    for (var i = 0; i < resources.length; i++) {
      var r = resources[i];
      var isCSV = r.format === 'CSV';
      var isApi = r.format === 'API' || r.format === 'WMS' || r.format === 'WFS';
      var sizeStr = formatSize(r.size);

      html += '<div class="datagov-resource" style="' +
        'display:flex;align-items:center;justify-content:space-between;' +
        'padding:8px 12px;border:1px solid var(--border-colour, #333);border-radius:4px;' +
        'margin-bottom:4px;background:var(--bg-tertiary, #252525);">' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-size:13px;color:var(--text-primary, #eee);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
            escapeHtml(r.name) +
          '</div>' +
          '<div style="font-size:11px;color:var(--text-muted, #666);margin-top:2px;">' +
            renderFormatBadge(r.format) +
            (sizeStr ? ' <span style="margin-left:4px;">' + sizeStr + '</span>' : '') +
            (r.lastModified ? ' <span style="margin-left:8px;">' + formatDate(r.lastModified) + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<div style="display:flex;gap:4px;margin-left:8px;">';

      if (isCSV) {
        html += '<button class="datagov-download-csv" ' +
          'data-resource-url="' + escapeHtml(r.url) + '" ' +
          'data-resource-name="' + escapeHtml(datasetName || r.name) + '" ' +
          'style="padding:3px 10px;border-radius:3px;border:1px solid #2d6a4f;' +
          'background:transparent;color:#b7e4c7;font-size:11px;cursor:pointer;' +
          'transition:background 0.15s;"' +
          ' onmouseover="this.style.background=\'#2d6a4f\'"' +
          ' onmouseout="this.style.background=\'transparent\'"' +
          '>Download CSV</button>';
      }

      if (isApi) {
        html += '<button class="datagov-connect-api" ' +
          'data-resource-id="' + escapeHtml(r.id) + '" ' +
          'data-resource-url="' + escapeHtml(r.url) + '" ' +
          'data-resource-name="' + escapeHtml(r.name) + '" ' +
          'data-resource-format="' + escapeHtml(r.format) + '" ' +
          'style="padding:3px 10px;border-radius:3px;border:1px solid #6a040f;' +
          'background:transparent;color:#ffb3c1;font-size:11px;cursor:pointer;' +
          'transition:background 0.15s;"' +
          ' onmouseover="this.style.background=\'#6a040f\'"' +
          ' onmouseout="this.style.background=\'transparent\'"' +
          '>Connect API</button>';
      }

      html += '</div></div>';
    }

    html += '</div>';
    return html;
  }

  /**
   * Render the full search UI into a container element.
   *
   * Creates a search form with filters (format dropdown, organisation text input,
   * tag chips) and a results list. Suggested datasets shown as quick-access chips
   * above the search box.
   *
   * @param {string} containerId - The ID of the DOM element to render into.
   */
  function renderSearchUI(containerId) {
    var container = document.getElementById(containerId);
    if (!container) {
      throw new Error('Container element not found: ' + containerId);
    }

    // Build the search UI HTML
    var html = '<div class="datagov-search-ui" style="font-family:inherit;">' +

      // --- Suggested datasets chips ---
      '<div style="margin-bottom:12px;">' +
        '<div style="font-size:11px;color:var(--text-muted, #666);margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Suggested Datasets</div>' +
        '<div id="datagov-suggested" style="display:flex;flex-wrap:wrap;gap:6px;">';

    for (var s = 0; s < SUGGESTED.length; s++) {
      html += '<button class="datagov-suggestion" ' +
        'data-query="' + escapeHtml(SUGGESTED[s].query) + '" ' +
        'data-org="' + escapeHtml(SUGGESTED[s].org) + '" ' +
        'style="padding:4px 12px;border-radius:14px;border:1px solid var(--border-colour, #333);' +
        'background:var(--bg-tertiary, #252525);color:var(--text-secondary, #aaa);' +
        'font-size:12px;cursor:pointer;transition:border-color 0.15s,color 0.15s;"' +
        ' onmouseover="this.style.borderColor=\'var(--accent, #4fc3f7)\';this.style.color=\'var(--accent, #4fc3f7)\'"' +
        ' onmouseout="this.style.borderColor=\'var(--border-colour, #333)\';this.style.color=\'var(--text-secondary, #aaa)\'"' +
        '>' + escapeHtml(SUGGESTED[s].label) + '</button>';
    }

    html += '</div></div>' +

      // --- Search form ---
      '<div style="display:flex;gap:8px;margin-bottom:8px;">' +
        '<input id="datagov-query" type="text" placeholder="Search Australian government datasets\u2026" style="' +
          'flex:1;padding:8px 12px;border-radius:4px;border:1px solid var(--border-colour, #333);' +
          'background:var(--bg-secondary, #1e1e1e);color:var(--text-primary, #eee);font-size:14px;' +
          'outline:none;" />' +
        '<button id="datagov-search-btn" style="' +
          'padding:8px 16px;border-radius:4px;border:none;' +
          'background:var(--accent, #4fc3f7);color:#000;font-size:14px;font-weight:600;' +
          'cursor:pointer;white-space:nowrap;">Search</button>' +
      '</div>' +

      // --- Filters row ---
      '<div style="display:flex;gap:8px;margin-bottom:12px;align-items:center;">' +
        '<select id="datagov-format-filter" style="' +
          'padding:6px 10px;border-radius:4px;border:1px solid var(--border-colour, #333);' +
          'background:var(--bg-secondary, #1e1e1e);color:var(--text-primary, #eee);font-size:12px;">' +
          '<option value="">All formats</option>' +
          '<option value="CSV">CSV</option>' +
          '<option value="JSON">JSON</option>' +
          '<option value="API">API</option>' +
          '<option value="XML">XML</option>' +
          '<option value="XLSX">XLSX</option>' +
          '<option value="GeoJSON">GeoJSON</option>' +
        '</select>' +
        '<input id="datagov-org-filter" type="text" placeholder="Organisation\u2026" style="' +
          'padding:6px 10px;border-radius:4px;border:1px solid var(--border-colour, #333);' +
          'background:var(--bg-secondary, #1e1e1e);color:var(--text-primary, #eee);font-size:12px;' +
          'width:180px;outline:none;" />' +
      '</div>' +

      // --- Status bar ---
      '<div id="datagov-status" style="font-size:12px;color:var(--text-muted, #666);margin-bottom:8px;min-height:18px;"></div>' +

      // --- Results container ---
      '<div id="datagov-results"></div>' +

      // --- Pagination ---
      '<div id="datagov-pagination" style="display:flex;justify-content:center;gap:8px;margin-top:12px;"></div>' +

      // --- Detail panel (hidden by default) ---
      '<div id="datagov-detail" style="display:none;margin-top:12px;' +
        'border:1px solid var(--border-colour, #333);border-radius:6px;padding:16px;' +
        'background:var(--bg-secondary, #1e1e1e);"></div>' +

    '</div>';

    container.innerHTML = html;

    // --- Wire up event handlers ---
    var searchState = { start: 0, rows: 10, currentQuery: '', currentOpts: {} };

    var searchBtn = document.getElementById('datagov-search-btn');
    var queryInput = document.getElementById('datagov-query');
    var formatFilter = document.getElementById('datagov-format-filter');
    var orgFilter = document.getElementById('datagov-org-filter');

    /**
     * Execute a search and render results.
     */
    async function doSearch(resetPagination) {
      if (resetPagination) {
        searchState.start = 0;
      }

      var q = queryInput.value.trim();
      var format = formatFilter.value;
      var org = orgFilter.value.trim();

      searchState.currentQuery = q;
      searchState.currentOpts = { format: format, organisation: org };

      var statusEl = document.getElementById('datagov-status');
      var resultsEl = document.getElementById('datagov-results');
      var paginationEl = document.getElementById('datagov-pagination');
      var detailEl = document.getElementById('datagov-detail');

      // Hide detail panel
      detailEl.style.display = 'none';

      statusEl.textContent = 'Searching\u2026';
      resultsEl.innerHTML = '';
      paginationEl.innerHTML = '';

      try {
        var result = await search(q, {
          format: format || undefined,
          organisation: org || undefined,
          rows: searchState.rows,
          start: searchState.start
        });

        var totalCount = result.count;
        var pageStart = searchState.start + 1;
        var pageEnd = Math.min(searchState.start + searchState.rows, totalCount);
        statusEl.textContent = totalCount === 0
          ? 'No datasets found.'
          : 'Showing ' + pageStart + '\u2013' + pageEnd + ' of ' + totalCount + ' datasets';

        // Render dataset cards
        var cardsHtml = '';
        for (var i = 0; i < result.results.length; i++) {
          cardsHtml += renderDatasetCard(result.results[i]);
        }
        resultsEl.innerHTML = cardsHtml;

        // Attach click handlers on Load buttons
        var loadBtns = resultsEl.querySelectorAll('.datagov-load-btn');
        for (var b = 0; b < loadBtns.length; b++) {
          loadBtns[b].addEventListener('click', handleLoadClick);
        }

        // Pagination buttons
        var pagHtml = '';
        if (searchState.start > 0) {
          pagHtml += '<button id="datagov-prev" style="' +
            'padding:6px 14px;border-radius:4px;border:1px solid var(--border-colour, #333);' +
            'background:transparent;color:var(--text-secondary, #aaa);font-size:12px;cursor:pointer;"' +
            '>\u2190 Previous</button>';
        }
        if (searchState.start + searchState.rows < totalCount) {
          pagHtml += '<button id="datagov-next" style="' +
            'padding:6px 14px;border-radius:4px;border:1px solid var(--border-colour, #333);' +
            'background:transparent;color:var(--text-secondary, #aaa);font-size:12px;cursor:pointer;"' +
            '>\u2192 Next</button>';
        }
        paginationEl.innerHTML = pagHtml;

        var prevBtn = document.getElementById('datagov-prev');
        var nextBtn = document.getElementById('datagov-next');
        if (prevBtn) {
          prevBtn.addEventListener('click', function () {
            searchState.start = Math.max(0, searchState.start - searchState.rows);
            doSearch(false);
          });
        }
        if (nextBtn) {
          nextBtn.addEventListener('click', function () {
            searchState.start += searchState.rows;
            doSearch(false);
          });
        }
      } catch (err) {
        statusEl.textContent = 'Error: ' + err.message;
        resultsEl.innerHTML = '';
      }
    }

    /**
     * Handle click on a dataset's Load button — show resources panel.
     */
    async function handleLoadClick(e) {
      e.stopPropagation();
      var datasetId = e.target.getAttribute('data-dataset-id');
      if (!datasetId) return;

      var detailEl = document.getElementById('datagov-detail');
      detailEl.style.display = 'block';
      detailEl.innerHTML = '<div style="color:var(--text-muted, #666);font-size:13px;">Loading dataset details\u2026</div>';

      try {
        var dataset = await getDataset(datasetId);
        var resources = getResources(dataset);

        var detailHtml = '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">' +
          '<div style="font-weight:600;font-size:15px;color:var(--text-primary, #eee);">' +
            escapeHtml(dataset.title) +
          '</div>' +
          '<button id="datagov-close-detail" style="' +
            'border:none;background:transparent;color:var(--text-muted, #666);font-size:18px;cursor:pointer;' +
            'padding:0 4px;line-height:1;">\u00d7</button>' +
        '</div>';

        if (dataset.organisation) {
          detailHtml += '<div style="margin-bottom:6px;">' +
            '<span style="display:inline-block;padding:2px 8px;border-radius:3px;' +
            'font-size:11px;background:var(--bg-tertiary, #2d2d2d);color:var(--text-secondary, #aaa);">' +
            escapeHtml(dataset.organisation) + '</span></div>';
        }

        if (dataset.description) {
          var cleanDesc = dataset.description.replace(/<[^>]*>/g, '');
          detailHtml += '<div style="font-size:12px;color:var(--text-secondary, #aaa);line-height:1.5;margin-bottom:12px;max-height:120px;overflow-y:auto;">' +
            escapeHtml(truncate(cleanDesc, 500)) + '</div>';
        }

        detailHtml += '<div style="font-size:12px;color:var(--text-muted, #666);margin-bottom:8px;">' +
          resources.length + ' resource' + (resources.length !== 1 ? 's' : '') +
          ' available &middot; Last updated ' + formatDate(dataset.lastUpdated) + '</div>';

        detailHtml += renderResources(resources, dataset.title);
        detailEl.innerHTML = detailHtml;

        // Close button handler
        var closeBtn = document.getElementById('datagov-close-detail');
        if (closeBtn) {
          closeBtn.addEventListener('click', function () {
            detailEl.style.display = 'none';
          });
        }

        // Wire up CSV download buttons
        var csvBtns = detailEl.querySelectorAll('.datagov-download-csv');
        for (var c = 0; c < csvBtns.length; c++) {
          csvBtns[c].addEventListener('click', handleCSVDownload);
        }

        // Wire up API connect buttons
        var apiBtns = detailEl.querySelectorAll('.datagov-connect-api');
        for (var a = 0; a < apiBtns.length; a++) {
          apiBtns[a].addEventListener('click', handleAPIConnect);
        }
      } catch (err) {
        detailEl.innerHTML = '<div style="color:#e57373;font-size:13px;">Error loading dataset: ' +
          escapeHtml(err.message) + '</div>';
      }
    }

    /**
     * Handle click on Download CSV button.
     */
    async function handleCSVDownload(e) {
      e.stopPropagation();
      var btn = e.target;
      var resourceUrl = btn.getAttribute('data-resource-url');
      var resourceName = btn.getAttribute('data-resource-name');

      var originalText = btn.textContent;
      btn.textContent = 'Downloading\u2026';
      btn.disabled = true;

      try {
        var dataset = await downloadCSV(resourceUrl, resourceName);
        btn.textContent = 'Loaded (' + dataset.rows.length + ' rows)';
        btn.style.borderColor = '#2d6a4f';
        btn.style.color = '#b7e4c7';

        // Dispatch a custom event so moke can pick up the dataset
        var event = new CustomEvent('datagov:dataset-loaded', {
          detail: dataset,
          bubbles: true
        });
        btn.dispatchEvent(event);
      } catch (err) {
        btn.textContent = 'Error';
        btn.style.borderColor = '#e57373';
        btn.style.color = '#e57373';
        console.error('[MokeDataGov] CSV download error:', err);

        // Reset after delay
        setTimeout(function () {
          btn.textContent = originalText;
          btn.style.borderColor = '#2d6a4f';
          btn.style.color = '#b7e4c7';
          btn.disabled = false;
        }, 3000);
      }
    }

    /**
     * Handle click on Connect API button.
     */
    function handleAPIConnect(e) {
      e.stopPropagation();
      var btn = e.target;

      var resource = {
        id: btn.getAttribute('data-resource-id') || '',
        name: btn.getAttribute('data-resource-name') || '',
        url: btn.getAttribute('data-resource-url') || '',
        format: btn.getAttribute('data-resource-format') || 'API',
        description: '',
        lastModified: ''
      };

      var config = toConnectionConfig(resource);

      // Dispatch a custom event so moke can configure the connection
      var event = new CustomEvent('datagov:api-connected', {
        detail: config,
        bubbles: true
      });
      btn.dispatchEvent(event);

      btn.textContent = 'Configured';
      btn.style.borderColor = '#2d6a4f';
      btn.style.color = '#b7e4c7';
    }

    // Search button click
    searchBtn.addEventListener('click', function () {
      doSearch(true);
    });

    // Enter key in search input
    queryInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        doSearch(true);
      }
    });

    // Suggestion chip clicks
    var suggestionBtns = document.querySelectorAll('#datagov-suggested .datagov-suggestion');
    for (var i = 0; i < suggestionBtns.length; i++) {
      suggestionBtns[i].addEventListener('click', function (e) {
        var q = e.target.getAttribute('data-query');
        var org = e.target.getAttribute('data-org');
        queryInput.value = q || '';
        orgFilter.value = org || '';
        doSearch(true);
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  window.MokeDataGov = {
    BASE_URL: BASE_URL,
    SUGGESTED: SUGGESTED,
    search: search,
    getDataset: getDataset,
    getResources: getResources,
    downloadCSV: downloadCSV,
    parseCSV: parseCSV,
    toConnectionConfig: toConnectionConfig,
    renderSearchUI: renderSearchUI,
    renderDatasetCard: renderDatasetCard,
    renderResources: renderResources
  };

})();
