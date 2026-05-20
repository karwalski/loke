/**
 * MK9.4: OpenAPI/Swagger Discovery for Moke
 *
 * Standalone utility for fetching, parsing, and extracting endpoint
 * information from OpenAPI 3.x and Swagger 2.0 specifications.
 * No external dependencies.
 *
 * Usage:
 *   const result = await window.MokeOpenAPI.fetch('https://petstore.swagger.io/v2/swagger.json');
 *   // result = { info, servers, endpoints: [...] }
 *   const config = window.MokeOpenAPI.toConnectionConfig(result.endpoints[0], result.servers[0]);
 */

(function () {
  'use strict';

  var LOKE_URL_FALLBACK = 'http://127.0.0.1:11430';

  /** Return the current loke proxy base URL. */
  function lokeUrl() {
    return (typeof window !== 'undefined' && window.LOKE_URL != null)
      ? window.LOKE_URL
      : LOKE_URL_FALLBACK;
  }

  // --------------------------------------------------------------------------
  // Simple YAML parser
  // --------------------------------------------------------------------------

  /**
   * Parse a basic YAML string into a JavaScript object.
   * Handles maps, sequences (block and flow), scalars (strings, numbers,
   * booleans, null), quoted strings, and multi-line folded/literal blocks.
   * Does NOT handle anchors/aliases, tags, or complex keys.
   */
  function parseYAML(yamlStr) {
    if (typeof yamlStr !== 'string') {
      throw new Error('parseYAML: input must be a string');
    }

    // Normalise line endings and split into lines.
    var lines = yamlStr.replace(/\r\n?/g, '\n').split('\n');

    // Strip leading BOM if present.
    if (lines.length > 0 && lines[0].charCodeAt(0) === 0xFEFF) {
      lines[0] = lines[0].slice(1);
    }

    var pos = { index: 0 };

    /** Skip blank lines and comment-only lines from current position. */
    function skipEmpty() {
      while (pos.index < lines.length) {
        var trimmed = lines[pos.index].replace(/\s+$/, '');
        if (trimmed === '' || trimmed.charAt(0) === '#') {
          pos.index++;
        } else {
          break;
        }
      }
    }

    /** Return leading whitespace count of a line. */
    function indentOf(line) {
      var m = line.match(/^( *)/);
      return m ? m[1].length : 0;
    }

    /** Parse a scalar value string (after the colon or as a sequence item). */
    function parseScalar(val) {
      if (val === '' || val === '~' || val === 'null' || val === 'Null' || val === 'NULL') {
        return null;
      }
      if (val === 'true' || val === 'True' || val === 'TRUE') return true;
      if (val === 'false' || val === 'False' || val === 'FALSE') return false;

      // Quoted strings — strip outer quotes.
      if ((val.charAt(0) === '"' && val.charAt(val.length - 1) === '"') ||
          (val.charAt(0) === "'" && val.charAt(val.length - 1) === "'")) {
        return val.slice(1, -1);
      }

      // Numbers.
      if (/^-?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(val)) {
        var n = Number(val);
        if (!isNaN(n)) return n;
      }

      return val;
    }

    /** Parse an inline (flow) value — handles flow sequences and flow maps. */
    function parseFlow(val) {
      val = val.trim();
      if (val.charAt(0) === '[') {
        return parseFlowSequence(val);
      }
      if (val.charAt(0) === '{') {
        return parseFlowMap(val);
      }
      return parseScalar(val);
    }

    /** Parse a flow sequence like [a, b, c]. */
    function parseFlowSequence(str) {
      str = str.trim();
      if (str.charAt(0) !== '[') return parseScalar(str);
      var inner = str.slice(1, str.length - 1).trim();
      if (inner === '') return [];
      // Simple comma-split (does not handle nested structures deeply).
      var parts = splitFlowItems(inner);
      var result = [];
      for (var i = 0; i < parts.length; i++) {
        result.push(parseFlow(parts[i]));
      }
      return result;
    }

    /** Parse a flow map like {a: 1, b: 2}. */
    function parseFlowMap(str) {
      str = str.trim();
      if (str.charAt(0) !== '{') return parseScalar(str);
      var inner = str.slice(1, str.length - 1).trim();
      if (inner === '') return {};
      var parts = splitFlowItems(inner);
      var result = {};
      for (var i = 0; i < parts.length; i++) {
        var colonIdx = parts[i].indexOf(':');
        if (colonIdx === -1) continue;
        var k = parts[i].slice(0, colonIdx).trim();
        var v = parts[i].slice(colonIdx + 1).trim();
        result[k] = parseFlow(v);
      }
      return result;
    }

    /** Split flow items by commas, respecting bracket/brace nesting. */
    function splitFlowItems(str) {
      var items = [];
      var depth = 0;
      var start = 0;
      for (var i = 0; i < str.length; i++) {
        var ch = str.charAt(i);
        if (ch === '[' || ch === '{') depth++;
        else if (ch === ']' || ch === '}') depth--;
        else if (ch === ',' && depth === 0) {
          items.push(str.slice(start, i).trim());
          start = i + 1;
        }
      }
      items.push(str.slice(start).trim());
      return items;
    }

    /** Strip an inline comment from a value string. */
    function stripComment(val) {
      // Walk through the string to find a # that is not inside quotes.
      var inSingle = false;
      var inDouble = false;
      for (var i = 0; i < val.length; i++) {
        var ch = val.charAt(i);
        if (ch === "'" && !inDouble) inSingle = !inSingle;
        else if (ch === '"' && !inSingle) inDouble = !inDouble;
        else if (ch === '#' && !inSingle && !inDouble) {
          // Must be preceded by whitespace to be a comment.
          if (i === 0 || val.charAt(i - 1) === ' ' || val.charAt(i - 1) === '\t') {
            return val.slice(0, i).replace(/\s+$/, '');
          }
        }
      }
      return val;
    }

    /**
     * Parse a block at the given minimum indent level.
     * Returns a JS value (object, array, or scalar).
     */
    function parseBlock(minIndent) {
      skipEmpty();
      if (pos.index >= lines.length) return null;

      var line = lines[pos.index];
      var indent = indentOf(line);
      if (indent < minIndent) return null;

      var trimmed = line.trim();

      // Detect whether this block is a sequence or a mapping.
      if (trimmed.charAt(0) === '-' && (trimmed.length === 1 || trimmed.charAt(1) === ' ')) {
        return parseSequenceBlock(indent);
      }
      // Check for mapping (key: value).
      if (trimmed.indexOf(':') !== -1) {
        return parseMappingBlock(indent);
      }

      // Bare scalar — consume the line.
      pos.index++;
      return parseScalar(stripComment(trimmed));
    }

    /** Parse a block sequence starting at the given indent. */
    function parseSequenceBlock(baseIndent) {
      var result = [];
      while (pos.index < lines.length) {
        skipEmpty();
        if (pos.index >= lines.length) break;
        var line = lines[pos.index];
        var indent = indentOf(line);
        if (indent < baseIndent) break;
        if (indent > baseIndent) break; // sub-block handled by recursion
        var trimmed = line.trim();
        if (!(trimmed.charAt(0) === '-' && (trimmed.length === 1 || trimmed.charAt(1) === ' '))) {
          break;
        }

        // Consume the '- ' prefix.
        var rest = trimmed.slice(1).trim();
        pos.index++;

        if (rest === '' || rest.charAt(0) === '#') {
          // Value is a nested block on subsequent indented lines.
          result.push(parseBlock(baseIndent + 1));
        } else if (rest.indexOf(':') !== -1 && rest.charAt(0) !== '{' && rest.charAt(0) !== '[' &&
                   rest.charAt(0) !== '"' && rest.charAt(0) !== "'") {
          // Inline mapping after dash, e.g. "- name: foo"
          // We need to parse this as a mapping, but the first key:value is on
          // this line. We'll handle it by constructing a temporary object.
          var obj = {};
          var colonIdx = rest.indexOf(':');
          var key = rest.slice(0, colonIdx).trim();
          var val = stripComment(rest.slice(colonIdx + 1).trim());

          if (val === '' || val.charAt(0) === '#') {
            obj[key] = parseBlock(indent + 2);
          } else {
            obj[key] = parseFlow(val);
          }
          // Collect remaining keys at deeper indent.
          while (pos.index < lines.length) {
            skipEmpty();
            if (pos.index >= lines.length) break;
            var nextLine = lines[pos.index];
            var nextIndent = indentOf(nextLine);
            if (nextIndent <= baseIndent) break;
            var nextTrimmed = nextLine.trim();
            if (nextTrimmed.charAt(0) === '-') break; // new sequence item
            var ci = nextTrimmed.indexOf(':');
            if (ci === -1) break;
            var nk = nextTrimmed.slice(0, ci).trim();
            var nv = stripComment(nextTrimmed.slice(ci + 1).trim());
            pos.index++;
            if (nv === '' || nv.charAt(0) === '#') {
              obj[nk] = parseBlock(nextIndent + 1);
            } else {
              obj[nk] = parseFlow(nv);
            }
          }
          result.push(obj);
        } else {
          result.push(parseFlow(rest));
        }
      }
      return result;
    }

    /** Parse a block mapping starting at the given indent. */
    function parseMappingBlock(baseIndent) {
      var result = {};
      while (pos.index < lines.length) {
        skipEmpty();
        if (pos.index >= lines.length) break;
        var line = lines[pos.index];
        var indent = indentOf(line);
        if (indent !== baseIndent) break;

        var trimmed = line.trim();
        var colonIdx = trimmed.indexOf(':');
        if (colonIdx === -1) break;

        var key = trimmed.slice(0, colonIdx).trim();
        var val = stripComment(trimmed.slice(colonIdx + 1).trim());
        pos.index++;

        if (val === '' || val.charAt(0) === '#') {
          // Check for literal/folded block scalars.
          skipEmpty();
          if (pos.index < lines.length) {
            var peekTrimmed = lines[pos.index].trim();
            if (peekTrimmed === '|' || peekTrimmed === '>' ||
                val === '|' || val === '>' || val === '|-' || val === '>-') {
              result[key] = parseBlockScalar(val || peekTrimmed, baseIndent);
              continue;
            }
          }
          result[key] = parseBlock(baseIndent + 1);
        } else if (val === '|' || val === '>' || val === '|-' || val === '>-') {
          result[key] = parseBlockScalar(val, baseIndent);
        } else {
          result[key] = parseFlow(val);
        }
      }
      return result;
    }

    /** Parse a literal (|) or folded (>) block scalar. */
    function parseBlockScalar(indicator, parentIndent) {
      var chomp = indicator.indexOf('-') !== -1; // strip trailing newline
      var fold = indicator.charAt(0) === '>';
      var contentLines = [];
      var blockIndent = -1;

      while (pos.index < lines.length) {
        var line = lines[pos.index];
        // Blank lines within block scalars are preserved.
        if (line.trim() === '') {
          contentLines.push('');
          pos.index++;
          continue;
        }
        var ind = indentOf(line);
        if (blockIndent === -1) {
          if (ind <= parentIndent) break;
          blockIndent = ind;
        }
        if (ind < blockIndent) break;
        contentLines.push(line.slice(blockIndent));
        pos.index++;
      }

      // Trim trailing blank lines if chomping.
      if (chomp) {
        while (contentLines.length > 0 && contentLines[contentLines.length - 1] === '') {
          contentLines.pop();
        }
      }

      if (fold) {
        return contentLines.join(' ').replace(/ {2,}/g, '\n').trim();
      }
      return contentLines.join('\n');
    }

    // Start parsing.
    // Skip document markers (---).
    skipEmpty();
    if (pos.index < lines.length && lines[pos.index].trim() === '---') {
      pos.index++;
    }

    return parseBlock(0) || {};
  }

  // --------------------------------------------------------------------------
  // $ref resolution
  // --------------------------------------------------------------------------

  /**
   * Resolve a JSON Pointer $ref (e.g. '#/components/schemas/Pet') within spec.
   * Returns the referenced object or undefined if not found.
   */
  function resolveRef(spec, ref) {
    if (typeof ref !== 'string' || ref.charAt(0) !== '#') return undefined;
    var parts = ref.slice(2).split('/'); // strip '#/'
    var current = spec;
    for (var i = 0; i < parts.length; i++) {
      var segment = decodeURIComponent(parts[i].replace(/~1/g, '/').replace(/~0/g, '~'));
      if (current == null || typeof current !== 'object') return undefined;
      current = current[segment];
    }
    return current;
  }

  /**
   * If obj has a $ref property, resolve it against spec.
   * Returns the resolved object (or the original if no $ref).
   */
  function maybeResolve(spec, obj) {
    if (obj && typeof obj === 'object' && obj['$ref']) {
      return resolveRef(spec, obj['$ref']) || obj;
    }
    return obj;
  }

  // --------------------------------------------------------------------------
  // Example generation from JSON Schema
  // --------------------------------------------------------------------------

  /**
   * Generate an example value from a JSON Schema definition.
   * Recursively builds objects, arrays, and scalars.
   * Uses 'example' fields when present, otherwise synthesises defaults.
   */
  function generateExample(schema, spec, _depth) {
    if (!schema || typeof schema !== 'object') return null;
    var depth = _depth || 0;
    if (depth > 10) return null; // prevent infinite recursion

    // Resolve $ref if needed.
    schema = maybeResolve(spec, schema);
    if (!schema) return null;

    // Use explicit example if provided.
    if (schema.example !== undefined) return schema.example;
    if (schema['default'] !== undefined) return schema['default'];

    // Handle enum.
    if (schema['enum'] && schema['enum'].length > 0) return schema['enum'][0];

    // Handle allOf by merging.
    if (schema.allOf && Array.isArray(schema.allOf)) {
      var merged = {};
      for (var a = 0; a < schema.allOf.length; a++) {
        var sub = generateExample(schema.allOf[a], spec, depth + 1);
        if (sub && typeof sub === 'object' && !Array.isArray(sub)) {
          for (var mk in sub) {
            if (sub.hasOwnProperty(mk)) merged[mk] = sub[mk];
          }
        }
      }
      return merged;
    }

    // Handle oneOf / anyOf — pick the first option.
    if (schema.oneOf && schema.oneOf.length > 0) {
      return generateExample(schema.oneOf[0], spec, depth + 1);
    }
    if (schema.anyOf && schema.anyOf.length > 0) {
      return generateExample(schema.anyOf[0], spec, depth + 1);
    }

    var type = schema.type;

    if (type === 'object' || schema.properties) {
      var obj = {};
      var props = schema.properties || {};
      for (var key in props) {
        if (props.hasOwnProperty(key)) {
          obj[key] = generateExample(props[key], spec, depth + 1);
        }
      }
      return obj;
    }

    if (type === 'array') {
      var itemSchema = schema.items ? maybeResolve(spec, schema.items) : null;
      if (itemSchema) {
        var item = generateExample(itemSchema, spec, depth + 1);
        return [item];
      }
      return [];
    }

    if (type === 'string') {
      if (schema.format === 'date-time') return '2024-01-01T00:00:00Z';
      if (schema.format === 'date') return '2024-01-01';
      if (schema.format === 'email') return 'user@example.com';
      if (schema.format === 'uri' || schema.format === 'url') return 'https://example.com';
      if (schema.format === 'uuid') return '550e8400-e29b-41d4-a716-446655440000';
      return 'string';
    }
    if (type === 'integer') return 0;
    if (type === 'number') return 0.0;
    if (type === 'boolean') return false;

    return null;
  }

  // --------------------------------------------------------------------------
  // Version detection
  // --------------------------------------------------------------------------

  /**
   * Detect the specification version.
   * Returns 'swagger2', 'openapi3.0', 'openapi3.1', or 'unknown'.
   */
  function detectVersion(spec) {
    if (!spec || typeof spec !== 'object') return 'unknown';
    if (spec.swagger && String(spec.swagger).indexOf('2') === 0) return 'swagger2';
    if (spec.openapi) {
      var v = String(spec.openapi);
      if (v.indexOf('3.1') === 0) return 'openapi3.1';
      if (v.indexOf('3.') === 0) return 'openapi3.0';
    }
    return 'unknown';
  }

  // --------------------------------------------------------------------------
  // Parameter extraction helpers
  // --------------------------------------------------------------------------

  /**
   * Normalise a parameter object into a consistent shape.
   */
  function normaliseParam(param, spec) {
    param = maybeResolve(spec, param);
    if (!param) return null;
    return {
      name: param.name || '',
      'in': param['in'] || '',
      description: param.description || '',
      required: !!param.required,
      type: param.type || (param.schema ? (param.schema.type || '') : ''),
      schema: param.schema ? maybeResolve(spec, param.schema) : null,
      example: param.example !== undefined ? param.example : (param.schema ? param.schema.example : undefined)
    };
  }

  // --------------------------------------------------------------------------
  // Swagger 2.0 parser
  // --------------------------------------------------------------------------

  function parseSwagger2(spec) {
    var info = spec.info || {};
    var basePath = spec.basePath || '';
    var host = spec.host || '';
    var schemes = spec.schemes || ['https'];

    // Build server URL from host + basePath.
    var servers = [];
    if (host) {
      for (var s = 0; s < schemes.length; s++) {
        servers.push({ url: schemes[s] + '://' + host + basePath, description: '' });
      }
    }
    if (servers.length === 0) {
      servers.push({ url: basePath || '/', description: '' });
    }

    var endpoints = [];
    var paths = spec.paths || {};

    for (var path in paths) {
      if (!paths.hasOwnProperty(path)) continue;
      var pathItem = paths[path];
      // Collect path-level parameters.
      var pathParams = pathItem.parameters || [];

      var methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head'];
      for (var m = 0; m < methods.length; m++) {
        var method = methods[m];
        if (!pathItem[method]) continue;
        var op = pathItem[method];

        // Merge path-level and operation-level parameters.
        var allParams = pathParams.concat(op.parameters || []);
        var params = [];
        for (var p = 0; p < allParams.length; p++) {
          var np = normaliseParam(allParams[p], spec);
          if (np) params.push(np);
        }

        // Extract response schema from 200 or default.
        var responseSchema = null;
        if (op.responses) {
          var resp = op.responses['200'] || op.responses['201'] || op.responses['default'];
          if (resp && resp.schema) {
            responseSchema = maybeResolve(spec, resp.schema);
          }
        }

        // Extract request body from body parameter.
        var requestBodySchema = null;
        for (var b = 0; b < params.length; b++) {
          if (params[b]['in'] === 'body' && params[b].schema) {
            requestBodySchema = maybeResolve(spec, params[b].schema);
            break;
          }
        }

        endpoints.push({
          path: path,
          method: method.toUpperCase(),
          operationId: op.operationId || '',
          summary: op.summary || '',
          description: op.description || '',
          tags: op.tags || [],
          parameters: params,
          requestBodySchema: requestBodySchema,
          responseSchema: responseSchema,
          deprecated: !!op.deprecated,
          security: op.security || spec.security || []
        });
      }
    }

    return {
      version: 'swagger2',
      info: {
        title: info.title || '',
        description: info.description || '',
        version: info.version || ''
      },
      servers: servers,
      endpoints: endpoints
    };
  }

  // --------------------------------------------------------------------------
  // OpenAPI 3.x parser
  // --------------------------------------------------------------------------

  function parseOpenAPI3(spec) {
    var info = spec.info || {};

    // Servers.
    var servers = [];
    var specServers = spec.servers || [];
    for (var s = 0; s < specServers.length; s++) {
      var srv = specServers[s];
      var url = srv.url || '/';
      // Substitute server variables with defaults.
      if (srv.variables) {
        for (var vk in srv.variables) {
          if (srv.variables.hasOwnProperty(vk)) {
            var dflt = srv.variables[vk]['default'] || '';
            url = url.replace('{' + vk + '}', dflt);
          }
        }
      }
      servers.push({ url: url, description: srv.description || '' });
    }
    if (servers.length === 0) {
      servers.push({ url: '/', description: '' });
    }

    var endpoints = [];
    var paths = spec.paths || {};

    for (var path in paths) {
      if (!paths.hasOwnProperty(path)) continue;
      var pathItem = maybeResolve(spec, paths[path]);
      if (!pathItem) continue;
      var pathParams = pathItem.parameters || [];

      var methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace'];
      for (var m = 0; m < methods.length; m++) {
        var method = methods[m];
        if (!pathItem[method]) continue;
        var op = pathItem[method];

        // Parameters.
        var allParams = pathParams.concat(op.parameters || []);
        var params = [];
        for (var p = 0; p < allParams.length; p++) {
          var np = normaliseParam(allParams[p], spec);
          if (np) params.push(np);
        }

        // Request body.
        var requestBodySchema = null;
        if (op.requestBody) {
          var rb = maybeResolve(spec, op.requestBody);
          if (rb && rb.content) {
            // Prefer application/json, fall back to first available.
            var contentType = rb.content['application/json'] ||
                              rb.content[Object.keys(rb.content)[0]];
            if (contentType && contentType.schema) {
              requestBodySchema = maybeResolve(spec, contentType.schema);
            }
          }
        }

        // Response schema — look at 200, 201, default.
        var responseSchema = null;
        if (op.responses) {
          var resp = op.responses['200'] || op.responses['201'] || op.responses['default'];
          if (resp) {
            resp = maybeResolve(spec, resp);
            if (resp && resp.content) {
              var rc = resp.content['application/json'] ||
                       resp.content[Object.keys(resp.content)[0]];
              if (rc && rc.schema) {
                responseSchema = maybeResolve(spec, rc.schema);
              }
            }
          }
        }

        endpoints.push({
          path: path,
          method: method.toUpperCase(),
          operationId: op.operationId || '',
          summary: op.summary || '',
          description: op.description || '',
          tags: op.tags || [],
          parameters: params,
          requestBodySchema: requestBodySchema,
          responseSchema: responseSchema,
          deprecated: !!op.deprecated,
          security: op.security || spec.security || []
        });
      }
    }

    return {
      version: detectVersion(spec),
      info: {
        title: info.title || '',
        description: info.description || '',
        version: info.version || ''
      },
      servers: servers,
      endpoints: endpoints
    };
  }

  // --------------------------------------------------------------------------
  // Unified parse
  // --------------------------------------------------------------------------

  /**
   * Parse a spec object (already decoded from JSON/YAML) into a normalised
   * structure: { version, info, servers, endpoints }.
   */
  function parse(spec) {
    var version = detectVersion(spec);
    if (version === 'swagger2') return parseSwagger2(spec);
    if (version === 'openapi3.0' || version === 'openapi3.1') return parseOpenAPI3(spec);
    throw new Error('Unsupported or unrecognised spec format. Expected Swagger 2.0 or OpenAPI 3.x.');
  }

  // --------------------------------------------------------------------------
  // Connection config generation
  // --------------------------------------------------------------------------

  /**
   * Convert a parsed endpoint into a connection configuration object suitable
   * for auto-filling the moke API connection form.
   *
   * @param {object} endpoint — one item from the endpoints array
   * @param {object} server — { url, description } from the servers array
   * @param {object} [spec] — original spec, needed for example generation
   * @returns {object} { url, method, headers, queryParams, body, description }
   */
  function toConnectionConfig(endpoint, server, spec) {
    var baseUrl = (server && server.url) ? server.url.replace(/\/+$/, '') : '';
    var fullUrl = baseUrl + endpoint.path;

    // Separate parameters by location.
    var headers = {};
    var queryParams = {};
    var pathParams = {};
    var params = endpoint.parameters || [];

    for (var i = 0; i < params.length; i++) {
      var param = params[i];
      var exampleVal = param.example !== undefined ? param.example : '';
      if (param['in'] === 'header') {
        headers[param.name] = exampleVal;
      } else if (param['in'] === 'query') {
        queryParams[param.name] = exampleVal;
      } else if (param['in'] === 'path') {
        pathParams[param.name] = exampleVal;
      }
    }

    // Substitute path parameters into URL.
    for (var pk in pathParams) {
      if (pathParams.hasOwnProperty(pk)) {
        var placeholder = '{' + pk + '}';
        var replacement = pathParams[pk] !== '' ? String(pathParams[pk]) : placeholder;
        fullUrl = fullUrl.replace(placeholder, replacement);
      }
    }

    // Build query string.
    var qsParts = [];
    for (var qk in queryParams) {
      if (queryParams.hasOwnProperty(qk)) {
        qsParts.push(encodeURIComponent(qk) + '=' + encodeURIComponent(queryParams[qk]));
      }
    }
    if (qsParts.length > 0) {
      fullUrl += '?' + qsParts.join('&');
    }

    // Generate request body example if present.
    var body = null;
    if (endpoint.requestBodySchema && spec) {
      body = generateExample(endpoint.requestBodySchema, spec);
    }

    // Description for display.
    var desc = endpoint.summary || endpoint.description || (endpoint.method + ' ' + endpoint.path);

    return {
      url: fullUrl,
      method: endpoint.method,
      headers: headers,
      queryParams: queryParams,
      body: body,
      description: desc,
      operationId: endpoint.operationId || '',
      tags: endpoint.tags || []
    };
  }

  // --------------------------------------------------------------------------
  // Fetch
  // --------------------------------------------------------------------------

  /**
   * Fetch an OpenAPI/Swagger spec from a URL via the loke proxy.
   * Auto-detects JSON vs YAML content.
   *
   * @param {string} specUrl — the URL of the spec document
   * @returns {Promise<object>} parsed result from parse()
   */
  async function fetchSpec(specUrl) {
    if (!specUrl || typeof specUrl !== 'string') {
      throw new Error('fetchSpec: specUrl is required');
    }

    var proxyUrl = lokeUrl() + '/api/proxy';
    var response = await fetch(proxyUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: specUrl, method: 'GET' })
    });

    if (!response.ok) {
      throw new Error('Failed to fetch spec: HTTP ' + response.status + ' ' + response.statusText);
    }

    var text = await response.text();
    text = text.trim();

    // Try to parse as JSON first.
    var spec;
    try {
      spec = JSON.parse(text);
    } catch (e) {
      // Fall back to YAML parsing.
      try {
        spec = parseYAML(text);
      } catch (yamlErr) {
        throw new Error('Failed to parse spec as JSON or YAML: ' + yamlErr.message);
      }
    }

    // Parse and return structured result. Attach raw spec for reference.
    var result = parse(spec);
    result._raw = spec;
    return result;
  }

  // --------------------------------------------------------------------------
  // Public API
  // --------------------------------------------------------------------------

  window.MokeOpenAPI = {
    fetch: fetchSpec,
    parse: parse,
    detectVersion: detectVersion,
    parseSwagger2: parseSwagger2,
    parseOpenAPI3: parseOpenAPI3,
    toConnectionConfig: toConnectionConfig,
    resolveRef: resolveRef,
    generateExample: generateExample,
    parseYAML: parseYAML
  };

})();
