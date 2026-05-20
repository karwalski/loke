/**
 * MokeGraphQL - GraphQL data source utility for moke
 *
 * Provides query execution (via loke proxy), schema introspection,
 * response-to-tabular conversion, and localStorage-based query management.
 *
 * No external dependencies.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  var STORAGE_KEY = 'moke_graphql_queries';

  /**
   * Standard introspection query that discovers types, queries, and mutations.
   */
  var INTROSPECTION_QUERY = [
    'query IntrospectionQuery {',
    '  __schema {',
    '    queryType { name }',
    '    mutationType { name }',
    '    types {',
    '      kind',
    '      name',
    '      description',
    '      fields(includeDeprecated: false) {',
    '        name',
    '        description',
    '        type {',
    '          kind',
    '          name',
    '          ofType {',
    '            kind',
    '            name',
    '            ofType {',
    '              kind',
    '              name',
    '              ofType {',
    '                kind',
    '                name',
    '              }',
    '            }',
    '          }',
    '        }',
    '        args {',
    '          name',
    '          description',
    '          type {',
    '            kind',
    '            name',
    '            ofType {',
    '              kind',
    '              name',
    '            }',
    '          }',
    '        }',
    '      }',
    '    }',
    '  }',
    '}'
  ].join('\n');

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /**
   * Resolve the loke proxy URL. Falls back to current origin if LOKE_URL is
   * not set on the window.
   */
  function proxyUrl() {
    var base = (window.LOKE_URL || '') || '';
    // Strip trailing slash so we don't double up
    return base.replace(/\/+$/, '') + '/api/proxy';
  }

  /**
   * Merge default and user-supplied headers. Always sets Content-Type and
   * Accept for GraphQL.
   */
  function buildHeaders(userHeaders) {
    var merged = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    if (userHeaders && typeof userHeaders === 'object') {
      var keys = Object.keys(userHeaders);
      for (var i = 0; i < keys.length; i++) {
        if (userHeaders[keys[i]] != null && userHeaders[keys[i]] !== '') {
          merged[keys[i]] = userHeaders[keys[i]];
        }
      }
    }
    return merged;
  }

  /**
   * Flatten a nested object into dot-notated keys.
   * e.g. { a: { b: 1 } } -> { 'a.b': 1 }
   */
  function flattenObject(obj, prefix) {
    var result = {};
    prefix = prefix || '';
    if (obj == null || typeof obj !== 'object' || Array.isArray(obj)) {
      return result;
    }
    var keys = Object.keys(obj);
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      var fullKey = prefix ? prefix + '.' + key : key;
      var val = obj[key];
      if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
        var nested = flattenObject(val, fullKey);
        var nk = Object.keys(nested);
        for (var j = 0; j < nk.length; j++) {
          result[nk[j]] = nested[nk[j]];
        }
      } else {
        result[fullKey] = val;
      }
    }
    return result;
  }

  // ---------------------------------------------------------------------------
  // Core API
  // ---------------------------------------------------------------------------

  /**
   * Execute a GraphQL query via the loke proxy.
   *
   * @param {string}  endpoint  - The target GraphQL endpoint URL.
   * @param {string}  query     - The GraphQL query/mutation string.
   * @param {object}  [variables] - Optional variables object.
   * @param {object}  [headers]   - Optional extra headers.
   * @returns {Promise<object>}  The parsed JSON response from the server.
   */
  async function execute(endpoint, query, variables, headers) {
    if (!endpoint) {
      throw new Error('GraphQL endpoint URL is required');
    }
    if (!query) {
      throw new Error('GraphQL query string is required');
    }

    var body = { query: query };
    if (variables && typeof variables === 'object' && Object.keys(variables).length > 0) {
      body.variables = variables;
    }

    var fetchHeaders = buildHeaders(headers);
    // Tell the loke proxy which upstream endpoint to hit
    fetchHeaders['X-Loke-Target'] = endpoint;

    var response = await fetch(proxyUrl(), {
      method: 'POST',
      headers: fetchHeaders,
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      var errText = await response.text();
      throw new Error('GraphQL request failed (' + response.status + '): ' + errText);
    }

    var json = await response.json();

    // Surface GraphQL-level errors even though HTTP was 200
    if (json.errors && json.errors.length > 0) {
      var messages = json.errors.map(function (e) { return e.message; });
      var err = new Error('GraphQL errors: ' + messages.join('; '));
      err.graphqlErrors = json.errors;
      err.data = json.data || null;
      throw err;
    }

    return json;
  }

  // ---------------------------------------------------------------------------
  // Introspection
  // ---------------------------------------------------------------------------

  /**
   * Run the standard introspection query and return the parsed schema.
   *
   * @param {string} endpoint - The GraphQL endpoint to introspect.
   * @param {object} [headers] - Optional extra headers.
   * @returns {Promise<object>} Parsed schema with {types, queries, mutations}.
   */
  async function introspect(endpoint, headers) {
    var result = await execute(endpoint, INTROSPECTION_QUERY, null, headers);
    return parseSchema(result);
  }

  /**
   * Parse an introspection result into a friendlier structure.
   *
   * @param {object} introspectionResult - Full response from introspection query.
   * @returns {object} { types, queries, mutations }
   */
  function parseSchema(introspectionResult) {
    var schema = introspectionResult &&
                 introspectionResult.data &&
                 introspectionResult.data.__schema;
    if (!schema) {
      throw new Error('Invalid introspection result: missing __schema');
    }

    var queryTypeName = schema.queryType ? schema.queryType.name : null;
    var mutationTypeName = schema.mutationType ? schema.mutationType.name : null;

    // Filter out built-in types (those starting with __)
    var userTypes = (schema.types || []).filter(function (t) {
      return t.name && t.name.indexOf('__') !== 0;
    });

    // Build a simple map: name -> { kind, name, description, fields[] }
    var types = userTypes.map(function (t) {
      return {
        kind: t.kind,
        name: t.name,
        description: t.description || '',
        fields: (t.fields || []).map(function (f) {
          return {
            name: f.name,
            description: f.description || '',
            type: resolveTypeName(f.type),
            args: (f.args || []).map(function (a) {
              return {
                name: a.name,
                description: a.description || '',
                type: resolveTypeName(a.type)
              };
            })
          };
        })
      };
    });

    // Extract top-level query and mutation fields
    var queries = [];
    var mutations = [];
    for (var i = 0; i < types.length; i++) {
      if (types[i].name === queryTypeName) {
        queries = types[i].fields;
      }
      if (types[i].name === mutationTypeName) {
        mutations = types[i].fields;
      }
    }

    return {
      types: types,
      queries: queries,
      mutations: mutations
    };
  }

  /**
   * Recursively resolve a GraphQL type reference to a human-readable string.
   * Handles NON_NULL, LIST, and named types.
   */
  function resolveTypeName(typeRef) {
    if (!typeRef) return 'Unknown';
    if (typeRef.kind === 'NON_NULL') {
      return resolveTypeName(typeRef.ofType) + '!';
    }
    if (typeRef.kind === 'LIST') {
      return '[' + resolveTypeName(typeRef.ofType) + ']';
    }
    return typeRef.name || 'Unknown';
  }

  // ---------------------------------------------------------------------------
  // Response -> tabular conversion
  // ---------------------------------------------------------------------------

  /**
   * Find the first array field within a data object (depth-first).
   * Useful for automatically locating the result list in a GraphQL response.
   *
   * @param {object} data - The response data object.
   * @returns {object|null} { key, value } where value is the array, or null.
   */
  function findArrayField(data) {
    if (data == null || typeof data !== 'object') return null;
    var keys = Object.keys(data);
    for (var i = 0; i < keys.length; i++) {
      var val = data[keys[i]];
      if (Array.isArray(val)) {
        return { key: keys[i], value: val };
      }
    }
    // If no direct array child, recurse into object children
    for (var j = 0; j < keys.length; j++) {
      var child = data[keys[j]];
      if (child && typeof child === 'object' && !Array.isArray(child)) {
        var found = findArrayField(child);
        if (found) return found;
      }
    }
    return null;
  }

  /**
   * Convert a GraphQL response `data` field into moke's tabular format.
   *
   * Returns { headers: string[], rows: any[][], meta: object }.
   *
   * @param {object} responseData - The `data` property from a GraphQL response.
   * @param {string} [queryName]  - Optional label for the dataset.
   * @returns {object} { headers, rows, meta }
   */
  function toDataset(responseData, queryName) {
    if (!responseData || typeof responseData !== 'object') {
      return { headers: [], rows: [], meta: { queryName: queryName || '', empty: true } };
    }

    var arrayResult = findArrayField(responseData);

    // If no array found, treat the whole data object as a single-row result
    if (!arrayResult) {
      var flat = flattenObject(responseData);
      var hdr = Object.keys(flat);
      var row = hdr.map(function (k) { return flat[k]; });
      return {
        headers: hdr,
        rows: [row],
        meta: {
          queryName: queryName || '',
          source: 'graphql',
          rowCount: 1,
          arrayField: null
        }
      };
    }

    var items = arrayResult.value;
    if (items.length === 0) {
      return {
        headers: [],
        rows: [],
        meta: {
          queryName: queryName || '',
          source: 'graphql',
          rowCount: 0,
          arrayField: arrayResult.key
        }
      };
    }

    // Derive headers from all items (flattened), preserving insertion order
    var headerSet = {};
    var headers = [];
    for (var i = 0; i < items.length; i++) {
      var flatItem = (items[i] && typeof items[i] === 'object' && !Array.isArray(items[i]))
        ? flattenObject(items[i])
        : { value: items[i] };
      var ks = Object.keys(flatItem);
      for (var j = 0; j < ks.length; j++) {
        if (!headerSet[ks[j]]) {
          headerSet[ks[j]] = true;
          headers.push(ks[j]);
        }
      }
    }

    // Build rows aligned to headers
    var rows = [];
    for (var r = 0; r < items.length; r++) {
      var fi = (items[r] && typeof items[r] === 'object' && !Array.isArray(items[r]))
        ? flattenObject(items[r])
        : { value: items[r] };
      var row = [];
      for (var c = 0; c < headers.length; c++) {
        var v = fi[headers[c]];
        row.push(v !== undefined ? v : null);
      }
      rows.push(row);
    }

    return {
      headers: headers,
      rows: rows,
      meta: {
        queryName: queryName || '',
        source: 'graphql',
        rowCount: rows.length,
        arrayField: arrayResult.key
      }
    };
  }

  // ---------------------------------------------------------------------------
  // Query builder
  // ---------------------------------------------------------------------------

  /**
   * Build a basic GraphQL query string from a type name and list of field names.
   *
   * @param {string}   typeName - The root query field name (e.g. "users").
   * @param {string[]} fields   - Array of field names to select.
   * @returns {string} A GraphQL query string.
   */
  function buildQuery(typeName, fields) {
    if (!typeName) {
      throw new Error('typeName is required');
    }
    if (!fields || fields.length === 0) {
      return '{\n  ' + typeName + '\n}';
    }
    var fieldList = fields.map(function (f) { return '    ' + f; }).join('\n');
    return '{\n  ' + typeName + ' {\n' + fieldList + '\n  }\n}';
  }

  // ---------------------------------------------------------------------------
  // localStorage persistence
  // ---------------------------------------------------------------------------

  /**
   * Save a named query to localStorage.
   *
   * @param {string} name      - Unique name for this saved query.
   * @param {string} endpoint  - The GraphQL endpoint URL.
   * @param {string} query     - The query string.
   * @param {object} [variables] - Variables object (will be JSON-stringified).
   * @param {object} [headers]   - Extra headers object.
   */
  function saveQuery(name, endpoint, query, variables, headers) {
    if (!name) throw new Error('Query name is required');
    var queries = loadQueries();
    queries[name] = {
      name: name,
      endpoint: endpoint || '',
      query: query || '',
      variables: variables || {},
      headers: headers || {},
      savedAt: new Date().toISOString()
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));
    } catch (e) {
      throw new Error('Failed to save query to localStorage: ' + e.message);
    }
  }

  /**
   * Load all saved queries from localStorage.
   *
   * @returns {object} Map of name -> saved query objects.
   */
  function loadQueries() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return {};
      return JSON.parse(raw);
    } catch (e) {
      return {};
    }
  }

  /**
   * Delete a saved query by name.
   *
   * @param {string} name - The name of the query to delete.
   */
  function deleteQuery(name) {
    var queries = loadQueries();
    delete queries[name];
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));
    } catch (e) {
      throw new Error('Failed to update localStorage: ' + e.message);
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  window.MokeGraphQL = {
    execute: execute,
    introspect: introspect,
    toDataset: toDataset,
    findArrayField: findArrayField,
    INTROSPECTION_QUERY: INTROSPECTION_QUERY,
    parseSchema: parseSchema,
    buildQuery: buildQuery,
    saveQuery: saveQuery,
    loadQueries: loadQueries,
    deleteQuery: deleteQuery
  };

})();
