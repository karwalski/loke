/**
 * MK16 (Routing & Companion Demo) + MK17 (Streaming & Real-Time)
 * Client-side logic for moke chat interface.
 */
(function() {
  'use strict';

  // ── MK16.1: Routing explainer card builder ──
  // Builds an expandable card showing routing decision details per request.
  window.mokeRouting = {
    // Classify intent client-side (mirrors core/router/intent.tk keyword path)
    classifyIntent: function(text) {
      var lower = (text || '').toLowerCase();
      var patterns = [
        { re: /\bembed|vector|similarity\b/, task: 'embedding', conf: 0.90 },
        { re: /\bsummarise|summarize|tldr|summary|brief\b/, task: 'summarisation', conf: 0.85 },
        { re: /\bcategorise|categorize|classify|label\b/, task: 'classification', conf: 0.82 },
        { re: /\breview.*code|check my code\b/, task: 'code_review', conf: 0.78 },
        { re: /\bcode|function|class|implement|refactor|debug\b/, task: 'code_generation', conf: 0.80 },
        { re: /\banalyse|analyze|data|csv|chart|trend|distribution\b/, task: 'data_analysis', conf: 0.78 },
        { re: /\bwho is|what is|find the name|identify\b/, task: 'ner', conf: 0.70 }
      ];
      for (var i = 0; i < patterns.length; i++) {
        if (patterns[i].re.test(lower)) {
          return { task: patterns[i].task, confidence: patterns[i].conf, method: 'keyword' };
        }
      }
      return { task: 'chat', confidence: 0.60, method: 'keyword' };
    },

    // Estimate cloud cost for model/tokens
    estimateCloudCost: function(modelId, tokensIn, tokensOut) {
      var m = (modelId || '').toLowerCase();
      var cin = 0.001, cout = 0.003;
      if (m.indexOf('claude-3-5-sonnet') !== -1) { cin = 0.003; cout = 0.015; }
      else if (m.indexOf('claude-3-5-haiku') !== -1) { cin = 0.001; cout = 0.005; }
      else if (m.indexOf('gpt-4o-mini') !== -1) { cin = 0.00015; cout = 0.0006; }
      else if (m.indexOf('gpt-4o') !== -1) { cin = 0.005; cout = 0.015; }
      else if (m.indexOf('llama') !== -1 || m.indexOf('qwen') !== -1) { cin = 0.0002; cout = 0.0002; }
      return (tokensIn / 1000) * cin + (tokensOut / 1000) * cout;
    },

    // Determine sensitivity routing hint
    sensitivityRouting: function(level) {
      var l = (level || '').toUpperCase();
      if (l === 'PUBLIC') return 'any';
      if (l === 'INTERNAL') return 'prefer-local';
      if (l === 'CONFIDENTIAL') return 'local-only';
      return 'local-only-no-log';
    },

    // Build the routing card HTML for a response
    buildRoutingCard: function(opts) {
      var cardId = 'routing-' + opts.msgNum;
      var bodyId = 'routing-body-' + opts.msgNum;
      var intent = opts.intent || { task: 'chat', confidence: 0.60, method: 'keyword' };
      var sensitivity = opts.sensitivity || 'PUBLIC';
      var modelId = opts.modelId || 'unknown';
      var isLocal = opts.isLocal !== undefined ? opts.isLocal : true;
      var tier = opts.tier || 'interactive';
      var costUsd = opts.costUsd || 0;
      var tokensIn = opts.tokensIn || 0;
      var tokensOut = opts.tokensOut || 0;
      var cloudCost = this.estimateCloudCost(modelId, tokensIn, tokensOut);

      var sensBadgeCls = 'rc-badge-green';
      if (sensitivity === 'INTERNAL') sensBadgeCls = 'rc-badge-amber';
      else if (sensitivity === 'CONFIDENTIAL' || sensitivity === 'RESTRICTED') sensBadgeCls = 'rc-badge-red';

      var html = '<div class="routing-card" id="' + cardId + '">' +
        '<div class="routing-card-header" onclick="mokeRouting.toggleCard(\'' + bodyId + '\', this)">' +
          '<span class="rc-icon">&#9654;</span>' +
          '<span class="rc-title">Routing Decision</span>' +
          '<span class="rc-model">' + modelId + '</span>' +
        '</div>' +
        '<div class="routing-card-body" id="' + bodyId + '">' +
          '<div class="rc-row"><span class="rc-label">Intent</span><span class="rc-value">' + intent.task + ' <span class="rc-badge rc-badge-teal">' + (intent.confidence * 100).toFixed(0) + '% ' + intent.method + '</span></span></div>' +
          '<div class="rc-row"><span class="rc-label">Sensitivity</span><span class="rc-value"><span class="rc-badge ' + sensBadgeCls + '">' + sensitivity + '</span> ' + this.sensitivityRouting(sensitivity) + '</span></div>' +
          '<div class="rc-row"><span class="rc-label">Latency Tolerance</span><span class="rc-value">instant</span></div>' +
          '<div class="rc-row"><span class="rc-label">Selected Tier</span><span class="rc-value">' + tier + '</span></div>' +
          '<div class="rc-row"><span class="rc-label">Model</span><span class="rc-value">' + modelId + (isLocal ? ' (local)' : ' (cloud)') + '</span></div>' +
          '<div class="rc-row"><span class="rc-label">Cost Estimate</span><span class="rc-value">$' + costUsd.toFixed(6) + '</span></div>' +
          '<div class="rc-row"><span class="rc-label">Reason</span><span class="rc-value">' + (isLocal ? 'local-only' : 'cloud-eligible') + ' (sensitivity: ' + sensitivity + ', tier: ' + tier + ') =&gt; ' + modelId + '</span></div>' +
        '</div>' +
      '</div>';
      return html;
    },

    toggleCard: function(bodyId, headerEl) {
      var body = document.getElementById(bodyId);
      if (!body) return;
      body.classList.toggle('open');
      headerEl.classList.toggle('open');
    }
  };

  // ── MK16.4: Cost comparison widget builder ──
  window.mokeCost = {
    sessionSavings: { totalCloud: 0, totalLocal: 0, totalSaved: 0, count: 0, localCount: 0 },

    init: function() {
      try {
        var saved = JSON.parse(sessionStorage.getItem('moke_mk16_cost'));
        if (saved) this.sessionSavings = saved;
      } catch(e) {}
    },

    buildWidget: function(modelId, tokensIn, tokensOut, isLocal) {
      var cloudCost = window.mokeRouting.estimateCloudCost(modelId, tokensIn, tokensOut);
      var localCost = 0;
      var savedCost = isLocal ? cloudCost : 0;

      this.sessionSavings.totalCloud += cloudCost;
      this.sessionSavings.totalLocal += localCost;
      this.sessionSavings.totalSaved += savedCost;
      this.sessionSavings.count++;
      if (isLocal) this.sessionSavings.localCount++;
      sessionStorage.setItem('moke_mk16_cost', JSON.stringify(this.sessionSavings));

      return '<div class="cost-widget">' +
        '<div class="cost-item"><span class="cost-label">Cloud:</span> <span class="cost-value cost-cloud">$' + cloudCost.toFixed(4) + '</span></div>' +
        '<span class="cost-sep">|</span>' +
        '<div class="cost-item"><span class="cost-label">Local:</span> <span class="cost-value cost-local">$0.0000</span></div>' +
        '<span class="cost-sep">|</span>' +
        '<div class="cost-item"><span class="cost-label">Saved:</span> <span class="cost-value cost-saved">$' + savedCost.toFixed(4) + '</span></div>' +
        '<span class="cost-sep">|</span>' +
        '<div class="cost-item"><span class="cost-label">Session total saved:</span> <span class="cost-value cost-saved">$' + this.sessionSavings.totalSaved.toFixed(4) + '</span></div>' +
      '</div>';
    }
  };
  window.mokeCost.init();

  // ── MK16.2: Tier visualiser updates ──
  window.mokeTiers = {
    setActive: function(tierName) {
      var tiers = ['interactive', 'considered', 'background'];
      tiers.forEach(function(t) {
        var dot = document.getElementById('tier-dot-' + t);
        if (dot) {
          if (t === tierName) {
            dot.classList.add('active');
          } else {
            dot.classList.remove('active');
          }
        }
      });
    }
  };

  // ── MK16.3: Companion device simulator ──
  window.mokeCompanion = {
    state: 'idle',
    events: ['Session created -- idle'],

    addEvent: function(text) {
      this.events.push(text);
      var el = document.getElementById('companion-events');
      if (el) {
        var div = document.createElement('div');
        div.textContent = text;
        el.appendChild(div);
        el.scrollTop = el.scrollHeight;
      }
    },

    setState: function(state, label, dotClass) {
      this.state = state;
      var statusEl = document.getElementById('companion-status');
      var dotEl = document.getElementById('companion-dot');
      if (statusEl) statusEl.textContent = label;
      if (dotEl) {
        dotEl.className = 'companion-dot';
        if (dotClass) dotEl.classList.add(dotClass);
      }
    },

    scan: function() {
      var self = this;
      var btn = document.getElementById('companion-scan-btn');
      if (btn) btn.disabled = true;

      self.setState('scanning', 'Scanning...', 'scanning');
      self.addEvent('Scanning local network via mDNS...');

      setTimeout(function() {
        self.setState('discovered', 'Device Found', '');
        self.addEvent('Discovered: Mac Studio (Office) -- Apple M2 Ultra, 76-core GPU, 192GB');
        var countEl = document.getElementById('companion-count');
        if (countEl) countEl.textContent = '1 found';

        setTimeout(function() {
          self.setState('pairing', 'Pairing...', 'scanning');
          self.addEvent('Pairing via TLS mutual auth...');

          setTimeout(function() {
            self.setState('paired', 'Paired', 'paired');
            self.addEvent('Paired successfully -- encrypted channel established');
            if (countEl) countEl.textContent = '1 paired';
            if (btn) { btn.textContent = 'Offload Request'; btn.disabled = false; btn.onclick = function() { self.offload(); }; }
          }, 1200);
        }, 800);
      }, 1500);
    },

    offload: function() {
      var self = this;
      var btn = document.getElementById('companion-scan-btn');
      if (btn) btn.disabled = true;

      self.setState('offloading', 'Offloading...', 'offloading');
      self.addEvent('Offloading inference: llama3.1:70b to Mac Studio (Office)');

      setTimeout(function() {
        self.setState('paired', 'Complete', 'paired');
        self.addEvent('Offload complete: 847 tokens in 3200ms (~265 tok/s)');
        if (btn) { btn.textContent = 'Offload Request'; btn.disabled = false; }
      }, 3200);
    }
  };

  window.companionScan = function() {
    window.mokeCompanion.scan();
  };

  // ── MK17.1: Streaming response display ──
  window.mokeStream = {
    activeEl: null,
    tokenCount: 0,
    counterEl: null,
    startTime: 0,

    // Create a streaming bubble and return the element
    startStreaming: function(historyEl) {
      this.tokenCount = 0;
      this.startTime = Date.now();

      var msg = document.createElement('div');
      msg.className = 'msg msg-assistant';
      msg.id = 'streaming-msg';

      var bubble = document.createElement('div');
      bubble.className = 'bubble bubble-assistant';
      bubble.id = 'streaming-bubble';
      bubble.innerHTML = '<span class="typing-indicator" id="stream-typing">' +
        '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>' +
        '</span>';

      var counter = document.createElement('div');
      counter.className = 'stream-counter';
      counter.id = 'stream-counter';
      counter.innerHTML = '<span class="count">0</span> tokens';

      msg.appendChild(bubble);
      msg.appendChild(counter);
      historyEl.appendChild(msg);
      historyEl.scrollTop = historyEl.scrollHeight;

      this.activeEl = bubble;
      this.counterEl = counter;
      return msg;
    },

    // Append a token to the streaming bubble
    addToken: function(token) {
      if (!this.activeEl) return;
      // Remove typing indicator on first real token
      var typing = document.getElementById('stream-typing');
      if (typing) typing.remove();

      this.tokenCount++;
      this.activeEl.textContent += token;
      if (this.counterEl) {
        var elapsed = ((Date.now() - this.startTime) / 1000) || 0.001;
        var tokPerSec = (this.tokenCount / elapsed).toFixed(1);
        this.counterEl.innerHTML = '<span class="count">' + this.tokenCount + '</span> tokens (' + tokPerSec + ' tok/s)';
      }
      // Auto-scroll
      var history = document.getElementById('message-history');
      if (history) history.scrollTop = history.scrollHeight;
    },

    // Complete streaming and convert to a regular message
    completeStreaming: function() {
      var typing = document.getElementById('stream-typing');
      if (typing) typing.remove();
      this.activeEl = null;
      this.counterEl = null;
    }
  };

  // ── MK17.2: Live pipeline animation ──
  // Adds pulse/glow class to the current active stage in the console
  window.mokePipelineAnim = {
    activeStageClass: null,

    setActiveStage: function(stageCls) {
      // Remove previous active state
      if (this.activeStageClass) {
        var prevEntries = document.querySelectorAll('.log-entry.stage-active');
        prevEntries.forEach(function(el) { el.classList.remove('stage-active'); });
      }
      this.activeStageClass = stageCls;
      // Add active to the most recent log entry matching this stage
      if (stageCls) {
        var allEntries = document.querySelectorAll('.log-entry');
        for (var i = allEntries.length - 1; i >= 0; i--) {
          var stageEl = allEntries[i].querySelector('.log-stage.' + stageCls);
          if (stageEl) {
            allEntries[i].classList.add('stage-active');
            break;
          }
        }
      }
    },

    clearActive: function() {
      var entries = document.querySelectorAll('.log-entry.stage-active');
      entries.forEach(function(el) { el.classList.remove('stage-active'); });
      this.activeStageClass = null;
    }
  };

  // ── MK17.3: Live console log ──
  // Enhanced console logging with streaming-aware auto-scroll and stage highlighting
  window.mokeConsoleLog = {
    logWithAnim: function(stage, msg, cls) {
      // Call the existing consoleLog if available
      if (typeof window._mokeConsoleLog === 'function') {
        window._mokeConsoleLog(stage, msg, cls);
      }
      // Activate pipeline animation for the current stage
      window.mokePipelineAnim.setActiveStage(cls);
    }
  };

  // ── Detect hardware summary ──
  (function() {
    var hwEl = document.getElementById('tier-hw-summary');
    if (hwEl) {
      fetch('http://127.0.0.1:11430/api/health', { mode: 'cors', cache: 'no-store' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d && d.hardware) {
            hwEl.textContent = d.hardware;
          } else {
            hwEl.textContent = 'Apple M-series';
          }
        })
        .catch(function() { hwEl.textContent = 'Apple M-series (estimated)'; });
    }
  })();

})();
