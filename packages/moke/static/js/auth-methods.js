/**
 * MK9.5 — Authentication methods for moke API connections.
 *
 * Provides auth configuration for: API Key, Bearer Token, Basic Auth,
 * OAuth 2.0 (client credentials), and Certificate (mTLS).
 *
 * Credentials are stored server-side via loke /api/settings — never in
 * localStorage.  Sensitive values are masked for display.
 *
 * No external dependencies.  Uses CSS custom properties from base.tkt
 * (--bg, --surface, --border, --teal, --text, --muted).
 */

(function () {
  'use strict';

  var LOKE_URL = window.LOKE_URL || 'http://127.0.0.1:11430';

  // ── Auth type definitions ─────────────────────────────────────────────

  var AUTH_TYPES = {
    none:        { label: 'None',                fields: [] },
    api_key:     { label: 'API Key',             fields: ['key_name', 'key_value', 'key_location'] },
    bearer:      { label: 'Bearer Token',        fields: ['token'] },
    basic:       { label: 'Basic Auth',          fields: ['username', 'password'] },
    oauth2:      { label: 'OAuth 2.0',           fields: ['token_url', 'client_id', 'client_secret', 'scopes'] },
    certificate: { label: 'Certificate (mTLS)',  fields: ['client_cert', 'client_key', 'ca_cert'] }
  };

  // ── Field metadata (label, type, placeholder, help text) ──────────────

  var FIELD_META = {
    key_name:      { label: 'Header / Param Name', type: 'text',     placeholder: 'X-API-Key',                help: 'Header name or query parameter name' },
    key_value:     { label: 'Key Value',            type: 'password', placeholder: 'your-api-key',             help: 'The API key value' },
    key_location:  { label: 'Send In',              type: 'select',   options: [{ v: 'header', l: 'Header' }, { v: 'query', l: 'Query Parameter' }], help: 'Where to attach the key' },
    token:         { label: 'Token',                type: 'password', placeholder: 'eyJhbGciOiJIUzI1NiIs...', help: 'Static bearer token' },
    username:      { label: 'Username',             type: 'text',     placeholder: 'user',                     help: '' },
    password:      { label: 'Password',             type: 'password', placeholder: '',                         help: '' },
    token_url:     { label: 'Token URL',            type: 'text',     placeholder: 'https://auth.example.com/oauth/token', help: 'OAuth 2.0 token endpoint' },
    client_id:     { label: 'Client ID',            type: 'text',     placeholder: '',                         help: '' },
    client_secret: { label: 'Client Secret',        type: 'password', placeholder: '',                         help: '' },
    scopes:        { label: 'Scopes',               type: 'text',     placeholder: 'read write',               help: 'Space-separated scopes' },
    client_cert:   { label: 'Client Certificate (PEM)', type: 'textarea', placeholder: '-----BEGIN CERTIFICATE-----', help: 'Paste PEM-encoded client certificate' },
    client_key:    { label: 'Client Key (PEM)',         type: 'textarea', placeholder: '-----BEGIN PRIVATE KEY-----',  help: 'Paste PEM-encoded private key' },
    ca_cert:       { label: 'CA Certificate (PEM)',     type: 'textarea', placeholder: '-----BEGIN CERTIFICATE-----',  help: 'Optional CA cert for server verification' }
  };

  // ── Helpers ────────────────────────────────────────────────────────────

  /** Base64-encode a string (UTF-8 safe). */
  function b64(str) {
    try {
      return btoa(unescape(encodeURIComponent(str)));
    } catch (_) {
      return btoa(str);
    }
  }

  /** Escape HTML to prevent injection in rendered forms. */
  function esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }

  // ── applyAuth ─────────────────────────────────────────────────────────
  /**
   * Modify a request config object in-place to include authentication.
   *
   * @param {Object} requestConfig  — { url, headers, params, body, ... }
   * @param {Object} authConfig     — { type, ...field values }
   * @returns {Object} the mutated requestConfig
   */
  function applyAuth(requestConfig, authConfig) {
    if (!authConfig || !authConfig.type || authConfig.type === 'none') {
      return requestConfig;
    }

    requestConfig.headers = requestConfig.headers || {};
    requestConfig.params  = requestConfig.params  || {};

    switch (authConfig.type) {
      case 'api_key':
        if (authConfig.key_location === 'query') {
          requestConfig.params[authConfig.key_name] = authConfig.key_value;
        } else {
          // Default to header
          requestConfig.headers[authConfig.key_name] = authConfig.key_value;
        }
        break;

      case 'bearer':
        requestConfig.headers['Authorization'] = 'Bearer ' + authConfig.token;
        break;

      case 'basic':
        requestConfig.headers['Authorization'] =
          'Basic ' + b64(authConfig.username + ':' + authConfig.password);
        break;

      case 'oauth2':
        // Expects authConfig._access_token to have been populated by
        // ensureValidToken() before this call.
        if (authConfig._access_token) {
          requestConfig.headers['Authorization'] = 'Bearer ' + authConfig._access_token;
        }
        break;

      case 'certificate':
        // Certificate data is attached for the backend to use when making
        // the upstream request.  The browser cannot do mTLS directly.
        requestConfig._mtls = {
          client_cert: authConfig.client_cert,
          client_key:  authConfig.client_key,
          ca_cert:     authConfig.ca_cert || null
        };
        break;
    }

    return requestConfig;
  }

  // ── renderAuthForm ────────────────────────────────────────────────────
  /**
   * Inject auth-type-specific form fields into a container element.
   *
   * @param {string} authType       — key from AUTH_TYPES
   * @param {string} containerId    — DOM id of the container element
   * @param {Object} [existingConfig] — pre-populate fields
   */
  function renderAuthForm(authType, containerId, existingConfig) {
    var container = document.getElementById(containerId);
    if (!container) return;

    var typeDef = AUTH_TYPES[authType];
    if (!typeDef) {
      container.innerHTML = '<p style="color:var(--muted);">Unknown auth type.</p>';
      return;
    }

    if (typeDef.fields.length === 0) {
      container.innerHTML = '<p style="color:var(--muted);">No authentication required.</p>';
      return;
    }

    var html = '';
    existingConfig = existingConfig || {};

    typeDef.fields.forEach(function (fieldName) {
      var meta  = FIELD_META[fieldName] || { label: fieldName, type: 'text', placeholder: '', help: '' };
      var val   = existingConfig[fieldName] || '';
      var id    = 'moke-auth-' + fieldName;

      html += '<div style="margin-bottom:12px;">';
      html += '  <label for="' + id + '" style="display:block;margin-bottom:4px;color:var(--text);font-size:13px;font-weight:500;">';
      html += esc(meta.label);
      html += '  </label>';

      if (meta.type === 'select' && meta.options) {
        html += '  <select id="' + id + '" data-auth-field="' + fieldName + '"';
        html += '    style="width:100%;padding:8px 10px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px;">';
        meta.options.forEach(function (opt) {
          var sel = val === opt.v ? ' selected' : '';
          html += '    <option value="' + esc(opt.v) + '"' + sel + '>' + esc(opt.l) + '</option>';
        });
        html += '  </select>';
      } else if (meta.type === 'textarea') {
        html += '  <textarea id="' + id + '" data-auth-field="' + fieldName + '" rows="4"';
        html += '    placeholder="' + esc(meta.placeholder) + '"';
        html += '    style="width:100%;padding:8px 10px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px;font-family:monospace;resize:vertical;">';
        html += esc(val);
        html += '</textarea>';
      } else {
        html += '  <input id="' + id + '" data-auth-field="' + fieldName + '"';
        html += '    type="' + meta.type + '"';
        html += '    value="' + esc(val) + '"';
        html += '    placeholder="' + esc(meta.placeholder) + '"';
        html += '    autocomplete="off"';
        html += '    style="width:100%;padding:8px 10px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px;">';
      }

      if (meta.help) {
        html += '  <small style="display:block;margin-top:3px;color:var(--muted);font-size:11px;">' + esc(meta.help) + '</small>';
      }

      html += '</div>';
    });

    container.innerHTML = html;
  }

  // ── readAuthForm ──────────────────────────────────────────────────────
  /**
   * Read current values from the rendered auth form.
   *
   * @param {string} authType    — key from AUTH_TYPES
   * @param {string} containerId — DOM id of the container
   * @returns {Object} authConfig with type + field values
   */
  function readAuthForm(authType, containerId) {
    var container = document.getElementById(containerId);
    var config = { type: authType };

    if (!container) return config;

    var typeDef = AUTH_TYPES[authType];
    if (!typeDef) return config;

    typeDef.fields.forEach(function (fieldName) {
      var el = container.querySelector('[data-auth-field="' + fieldName + '"]');
      config[fieldName] = el ? el.value : '';
    });

    return config;
  }

  // ── fetchOAuth2Token ──────────────────────────────────────────────────
  /**
   * Fetch an OAuth 2.0 access token using the client credentials grant.
   * The request is routed through the loke proxy so the browser does not
   * need direct access to the token endpoint.
   *
   * @param {string} tokenUrl
   * @param {string} clientId
   * @param {string} clientSecret
   * @param {string} scopes        — space-separated scope string
   * @returns {Promise<Object>}    — { access_token, token_type, expires_in, ... }
   */
  async function fetchOAuth2Token(tokenUrl, clientId, clientSecret, scopes) {
    var body = 'grant_type=client_credentials'
      + '&client_id='     + encodeURIComponent(clientId)
      + '&client_secret=' + encodeURIComponent(clientSecret);

    if (scopes && scopes.trim()) {
      body += '&scope=' + encodeURIComponent(scopes.trim());
    }

    var resp = await fetch(LOKE_URL + '/api/proxy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url:     tokenUrl,
        method:  'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body:    body
      })
    });

    if (!resp.ok) {
      var errText = await resp.text();
      throw new Error('OAuth token request failed (' + resp.status + '): ' + errText);
    }

    var data = await resp.json();

    // Attach a local timestamp so we can check expiry later
    data._fetched_at = Date.now();
    return data;
  }

  // ── ensureValidToken ──────────────────────────────────────────────────
  /**
   * Check whether the cached OAuth token is still valid.  If it has
   * expired (or is within 60 s of expiring), fetch a fresh one.
   *
   * Mutates authConfig in-place (_access_token, _token_data).
   *
   * @param {Object} authConfig — must have type === 'oauth2'
   * @returns {Promise<Object>} the (possibly refreshed) authConfig
   */
  async function ensureValidToken(authConfig) {
    if (authConfig.type !== 'oauth2') return authConfig;

    var tokenData = authConfig._token_data;
    var needsRefresh = false;

    if (!tokenData || !tokenData.access_token) {
      needsRefresh = true;
    } else {
      // Check expiry with a 60-second buffer
      var expiresIn = tokenData.expires_in || 3600;
      var fetchedAt = tokenData._fetched_at || 0;
      var expiresAt = fetchedAt + (expiresIn * 1000);
      if (Date.now() >= expiresAt - 60000) {
        needsRefresh = true;
      }
    }

    if (needsRefresh) {
      tokenData = await fetchOAuth2Token(
        authConfig.token_url,
        authConfig.client_id,
        authConfig.client_secret,
        authConfig.scopes
      );
      authConfig._token_data    = tokenData;
      authConfig._access_token  = tokenData.access_token;
    }

    return authConfig;
  }

  // ── Credential persistence (via loke /api/settings) ───────────────────

  /** Settings key for a connection's auth config. */
  function credKey(connectionName) {
    return 'connection_auth_' + connectionName;
  }

  /**
   * Save auth credentials for a named connection.
   * Stored server-side in ~/.loke/connections.json via loke keychain.
   *
   * @param {string} connectionName
   * @param {Object} authConfig
   * @returns {Promise<Object>} server response
   */
  async function saveCredentials(connectionName, authConfig) {
    // Strip transient runtime fields before persisting
    var toSave = {};
    Object.keys(authConfig).forEach(function (k) {
      if (k.charAt(0) !== '_') toSave[k] = authConfig[k];
    });

    var resp = await fetch(LOKE_URL + '/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: credKey(connectionName), value: toSave })
    });

    if (!resp.ok) {
      var errText = await resp.text();
      throw new Error('Failed to save credentials (' + resp.status + '): ' + errText);
    }

    return resp.json();
  }

  /**
   * Load auth credentials for a named connection from the loke backend.
   *
   * @param {string} connectionName
   * @returns {Promise<Object|null>} authConfig or null if not found
   */
  async function loadCredentials(connectionName) {
    var resp = await fetch(LOKE_URL + '/api/settings', { cache: 'no-store' });

    if (!resp.ok) {
      throw new Error('Failed to load settings (' + resp.status + ')');
    }

    var data = await resp.json();
    var key  = credKey(connectionName);

    if (data && data[key] !== undefined) {
      return data[key];
    }
    return null;
  }

  /**
   * Delete stored credentials for a named connection.
   *
   * @param {string} connectionName
   * @returns {Promise<Object>} server response
   */
  async function deleteCredentials(connectionName) {
    var resp = await fetch(LOKE_URL + '/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: credKey(connectionName), value: null })
    });

    if (!resp.ok) {
      var errText = await resp.text();
      throw new Error('Failed to delete credentials (' + resp.status + '): ' + errText);
    }

    return resp.json();
  }

  // ── maskValue ─────────────────────────────────────────────────────────
  /**
   * Mask a sensitive string for safe display.
   * Shows first 4 characters followed by '****'.
   * Short values (<=4 chars) are fully masked.
   *
   * @param {string} value
   * @returns {string}
   */
  function maskValue(value) {
    if (!value || typeof value !== 'string') return '****';
    if (value.length <= 4) return '****';
    return value.substring(0, 4) + '****';
  }

  // ── Public API ────────────────────────────────────────────────────────

  window.MokeAuth = {
    AUTH_TYPES:        AUTH_TYPES,
    applyAuth:         applyAuth,
    renderAuthForm:    renderAuthForm,
    readAuthForm:      readAuthForm,
    fetchOAuth2Token:  fetchOAuth2Token,
    ensureValidToken:  ensureValidToken,
    saveCredentials:   saveCredentials,
    loadCredentials:   loadCredentials,
    deleteCredentials: deleteCredentials,
    maskValue:         maskValue
  };

})();
