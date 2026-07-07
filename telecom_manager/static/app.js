document.addEventListener('DOMContentLoaded',function(){
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var EASE = function(t){ return 1 - Math.pow(1 - t, 3); };

  /* ---------- count-up ---------- */
  function tweenNumber(el, to, opts){
    opts = opts || {};
    var dur = opts.duration || (reduce ? 0 : 700);
    var from = parseFloat(el.getAttribute('data-current') || el.textContent || '0');
    if(isNaN(from)) from = 0;
    if(reduce || dur === 0){ el.textContent = formatNum(to, opts.decimals); el.setAttribute('data-current', to); return; }
    var start = performance.now();
    function step(now){
      var t = Math.min(1, (now - start) / dur);
      var v = from + (to - from) * EASE(t);
      el.textContent = formatNum(v, opts.decimals);
      if(t < 1) requestAnimationFrame(step);
      else { el.textContent = formatNum(to, opts.decimals); el.setAttribute('data-current', to); }
    }
    requestAnimationFrame(step);
  }
  function formatNum(v, d){
    if(d == null) d = (Math.abs(v) < 10 ? 1 : 0);
    return v.toFixed(d);
  }
  function runCounters(){
    document.querySelectorAll('.count[data-target]').forEach(function(el){
      tweenNumber(el, parseFloat(el.getAttribute('data-target')));
    });
  }

  /* ---------- gauges ---------- */
  function runGauges(){
    document.querySelectorAll('.stat-card').forEach(function(card){
      var arc = card.querySelector('.gauge-arc');
      if(!arc) return;
      var pct = parseFloat(card.getAttribute('data-pct') || '0');
      var C = 2 * Math.PI * 52;
      var off = C * (1 - Math.max(0, Math.min(100, pct)) / 100);
      card.style.setProperty('--gauge-off', off);
      if(reduce){ arc.style.strokeDashoffset = off; card.classList.add('is-drawn'); return; }
      arc.style.strokeDashoffset = C;
      requestAnimationFrame(function(){
        requestAnimationFrame(function(){ card.classList.add('is-drawn'); });
      });
    });
  }
  function updateGauge(card, pct){
    card.setAttribute('data-pct', pct);
    var arc = card.querySelector('.gauge-arc');
    if(!arc) return;
    var C = 2 * Math.PI * 52;
    var off = C * (1 - Math.max(0, Math.min(100, pct)) / 100);
    card.style.setProperty('--gauge-off', off);
    if(!reduce) card.classList.remove('is-drawn');
    requestAnimationFrame(function(){
      requestAnimationFrame(function(){ card.classList.add('is-drawn'); });
    });
    var tone = pct > 80 ? 'danger' : (pct > 50 ? 'warn' : 'ok');
    card.setAttribute('data-tone', tone);
  }

  /* ---------- sparkline draw-in + hover tooltip ---------- */
  function buildSpark(svg){
    var data = (svg.getAttribute('data-values') || '').split(',').map(parseFloat).filter(function(v){return !isNaN(v)});
    if(!data.length) return;
    var W = svg.viewBox.baseVal.width || 240;
    var H = svg.viewBox.baseVal.height || 60;
    var pad = 4;
    var max = Math.max.apply(null, data);
    var min = Math.min.apply(null, data);
    var range = max - min || 1;
    var stepX = (W - pad*2) / Math.max(1, data.length - 1);

    svg._data = data;
    svg._pts  = data.map(function(_,i){
      return [pad + i * stepX, H - pad - ((data[i] - min) / range) * (H - pad*2)];
    });

    var d = svg._pts.map(function(p,i){ return (i===0?'M':'L') + p[0].toFixed(2) + ' ' + p[1].toFixed(2); }).join(' ');
    var line = svg.querySelector('.spark-line');
    var area = svg.querySelector('.spark-area');
    if(line) line.setAttribute('d', d);
    if(area){
      var last = svg._pts[svg._pts.length-1], first = svg._pts[0];
      area.setAttribute('d', d + ' L ' + last[0].toFixed(2) + ' ' + (H - pad) + ' L ' + first[0].toFixed(2) + ' ' + (H - pad) + ' Z');
    }
    var dot = svg.querySelector('.spark-dot');
    if(dot && svg._pts.length){ var p = svg._pts[svg._pts.length-1]; dot.setAttribute('cx', p[0]); dot.setAttribute('cy', p[1]); }

    if(reduce){ svg.classList.add('is-drawn'); bindSparkHover(svg); return; }
    if(line){
      var len = line.getTotalLength();
      line.style.strokeDasharray = len;
      line.style.strokeDashoffset = len;
    }
    requestAnimationFrame(function(){
      requestAnimationFrame(function(){
        svg.classList.add('is-drawn');
        bindSparkHover(svg);
      });
    });
  }

  function bindSparkHover(svg){
    if(svg._hoverBound) return;
    svg._hoverBound = true;
    var guide = svg.querySelector('.spark-guide');
    var hov   = svg.querySelector('.spark-hover-dot');
    var tip   = svg.parentNode.querySelector('.spark-tip');
    if(!guide || !hov || !tip) return;
    var wrap = svg.parentNode;

    function onMove(e){
      var rect = svg.getBoundingClientRect();
      var x = ((e.clientX - rect.left) / rect.width) * (svg.viewBox.baseVal.width || 240);
      var pts = svg._pts || [];
      if(!pts.length) return;
      var stepX = pts[1] ? (pts[1][0] - pts[0][0]) : 0;
      var idx = stepX ? Math.round((x - pts[0][0]) / stepX) : 0;
      idx = Math.max(0, Math.min(pts.length-1, idx));
      var p = pts[idx];
      guide.setAttribute('x1', p[0]); guide.setAttribute('x2', p[0]);
      hov.setAttribute('cx', p[0]);   hov.setAttribute('cy', p[1]);
      tip.textContent = (svg._data[idx]).toFixed(1) + '%';
      // position tip in container space
      var wrapRect = wrap.getBoundingClientRect();
      var px = (p[0] / (svg.viewBox.baseVal.width || 240)) * rect.width + (rect.left - wrapRect.left);
      var py = (p[1] / (svg.viewBox.baseVal.height || 60)) * rect.height + (rect.top - wrapRect.top);
      tip.style.left = px + 'px';
      tip.style.top  = py + 'px';
      svg.classList.add('is-hovering');
    }
    function onLeave(){
      svg.classList.remove('is-hovering');
    }
    svg.addEventListener('mousemove', onMove);
    svg.addEventListener('mouseleave', onLeave);
    // touch support
    svg.addEventListener('touchmove', function(e){ if(e.touches[0]) onMove(e.touches[0]); }, {passive:true});
    svg.addEventListener('touchend', onLeave);
  }

  function runSparks(){
    document.querySelectorAll('svg.spark[data-values]').forEach(buildSpark);
  }
  function updateSpark(svg, data){
    svg.setAttribute('data-values', data.join(','));
    // preserve dasharray length style so draw-in plays
    svg.classList.remove('is-drawn');
    // rebuild path via buildSpark
    buildSpark(svg);
  }

  /* ---------- copy button ---------- */
  function fallbackCopy(text){var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta)}
  document.querySelectorAll('.copy-btn').forEach(function(btn){
    btn.addEventListener('click',function(e){
      var text = btn.getAttribute('data-copy') || '';
      var old = btn.getAttribute('data-old') || btn.textContent;
      btn.setAttribute('data-old', old);
      function done(){
        btn.textContent = '\u2713 Copied';
        btn.classList.add('copied');
        clearTimeout(btn._t);
        btn._t = setTimeout(function(){
          btn.textContent = old;
          btn.classList.remove('copied');
        }, 1400);
      }
      if(navigator.clipboard){ navigator.clipboard.writeText(text).then(done).catch(function(){ fallbackCopy(text); done(); }); }
      else { fallbackCopy(text); done(); }
      addRipple(btn, e);
    });
  });

  /* ---------- click ripple ---------- */
  function addRipple(el, e){
    if(reduce) return;
    var rect = el.getBoundingClientRect();
    var x = (e.clientX != null ? e.clientX - rect.left : rect.width/2);
    var y = (e.clientY != null ? e.clientY - rect.top : rect.height/2);
    var r = document.createElement('span');
    r.className = 'ripple';
    r.style.left = x + 'px';
    r.style.top  = y + 'px';
    r.style.width = '6px'; r.style.height = '6px';
    el.appendChild(r);
    setTimeout(function(){ if(r.parentNode) r.parentNode.removeChild(r); }, 700);
  }
  document.querySelectorAll('.btn, .btn-sm').forEach(function(btn){
    btn.addEventListener('click', function(e){ addRipple(btn, e); });
  });

  /* ---------- mobile sidebar ---------- */
  var toggle = document.querySelector('.mobile-menu-btn');
  var sidebar = document.querySelector('.sidebar');
  if(toggle && sidebar){
    toggle.addEventListener('click', function(){
      var open = sidebar.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape'){ sidebar.classList.remove('open'); toggle.setAttribute('aria-expanded','false'); }
    });
    document.querySelectorAll('.side-nav a').forEach(function(a){
      a.addEventListener('click', function(){
        sidebar.classList.remove('open');
        toggle.setAttribute('aria-expanded','false');
      });
    });
  }

  /* ---------- modal confirm/alert + toast ---------- */
  var modalRoot = document.getElementById('modal-root');
  var toastHost = null;
  function ensureToastHost(){
    if(toastHost && toastHost.isConnected) return toastHost;
    toastHost = document.createElement('div');
    toastHost.className = 'toast-stack';
    document.body.appendChild(toastHost);
    return toastHost;
  }

  function svgIcon(name){
    if(name === 'danger') return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    if(name === 'warn')   return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
    if(name === 'ok')     return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
  }

  function buildModal(opts){
    var kind = opts.kind || (opts.danger ? 'danger' : 'info');
    var tone = (kind === 'danger' || kind === 'warn') ? kind : (kind === 'ok' ? 'ok' : 'info');
    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.setAttribute('role', 'dialog');
    backdrop.setAttribute('aria-modal', 'true');
    backdrop.innerHTML =
      '<div class="modal-card">' +
        '<button type="button" class="modal-close-x" aria-label="Close" data-modal-close>\u00d7</button>' +
        '<div class="modal-head">' +
          '<div class="modal-icon ' + tone + '">' + svgIcon(tone === 'ok' ? 'ok' : tone) + '</div>' +
          '<div class="modal-title">' + escapeHtml(opts.title || '') + '</div>' +
        '</div>' +
        '<div class="modal-body">' + (opts.html || escapeHtml(opts.message || '')) + '</div>' +
        (opts.confirmText === false ? '' :
          '<div class="modal-foot">' +
            '<button type="button" class="btn btn-secondary" data-modal-cancel>' + escapeHtml(opts.cancelText || 'Cancel') + '</button>' +
            '<button type="button" class="btn ' + (opts.danger ? 'btn-danger' : 'btn-primary') + '" data-modal-confirm>' + escapeHtml(opts.confirmText || 'Confirm') + '</button>' +
          '</div>'
        ) +
      '</div>';
    return backdrop;
  }

  function openModal(opts){
    return new Promise(function(resolve){
      var backdrop = buildModal(opts);
      modalRoot.appendChild(backdrop);
      var confirmBtn = backdrop.querySelector('[data-modal-confirm]');
      var cancelBtn  = backdrop.querySelector('[data-modal-cancel]');
      var closeBtn   = backdrop.querySelector('[data-modal-close]');
      // focus confirm
      setTimeout(function(){ (confirmBtn || closeBtn).focus(); }, 30);

      function done(value){
        if(backdrop.classList.contains('is-leaving')) return;
        backdrop.classList.add('is-leaving');
        setTimeout(function(){ if(backdrop.parentNode) backdrop.parentNode.removeChild(backdrop); resolve(value); }, 200);
      }
      if(confirmBtn) confirmBtn.addEventListener('click', function(){ done(true); });
      if(cancelBtn)  cancelBtn.addEventListener('click',  function(){ done(false); });
      if(closeBtn)   closeBtn.addEventListener('click',   function(){ done(false); });
      backdrop.addEventListener('click', function(e){ if(e.target === backdrop) done(false); });
      document.addEventListener('keydown', function onKey(e){
        if(backdrop.classList.contains('is-leaving')){ document.removeEventListener('keydown', onKey); return; }
        if(e.key === 'Escape'){ done(false); }
        if(e.key === 'Enter' && confirmBtn && document.activeElement !== cancelBtn){ done(true); }
      });
    });
  }

  function escapeHtml(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  // public API
  window.modalConfirm = function(opts){
    opts = opts || {};
    if(typeof opts === 'string') opts = { message: opts };
    return openModal({
      title: opts.title || 'Are you sure?',
      message: opts.message,
      html: opts.html,
      confirmText: opts.confirmText || 'Confirm',
      cancelText:  opts.cancelText  || 'Cancel',
      danger: !!opts.danger,
    });
  };
  window.modalAlert = function(opts){
    opts = opts || {};
    if(typeof opts === 'string') opts = { message: opts };
    return openModal({
      title: opts.title || 'Notice',
      message: opts.message,
      kind: opts.kind || 'info',
      confirmText: 'OK',
      cancelText: false,
    });
  };
  window.toast = function(opts){
    opts = opts || {};
    if(typeof opts === 'string') opts = { message: opts };
    var host = ensureToastHost();
    var t = document.createElement('div');
    var kind = opts.kind || 'info';
    t.className = 'toast ' + kind;
    t.innerHTML =
      '<span class="toast-dot" aria-hidden="true"></span>' +
      '<div class="toast-body">' + escapeHtml(opts.message || '') + '</div>' +
      '<button type="button" class="toast-close" aria-label="Dismiss">\u00d7</button>';
    host.appendChild(t);
    function kill(){
      if(t.classList.contains('is-leaving')) return;
      t.classList.add('is-leaving');
      setTimeout(function(){ if(t.parentNode) t.parentNode.removeChild(t); }, 220);
    }
    t.querySelector('.toast-close').addEventListener('click', kill);
    var dur = opts.duration == null ? 4000 : opts.duration;
    if(dur > 0) setTimeout(kill, dur);
  };

  /* ---------- intercept data-confirm on form submit ---------- */
  document.addEventListener('submit', function(e){
    var form = e.target;
    if(form.tagName !== 'FORM') return;
    var btn = form.querySelector('[data-confirm]') || (form.dataset && form.dataset.confirm ? form : null);
    if(!btn) return;
    var msg, title, danger = false, confirmText, cancelText;
    if(btn === form){
      msg = form.dataset.confirm;
      danger = form.dataset.confirmDanger === 'true';
    } else {
      msg = btn.getAttribute('data-confirm');
      danger = btn.getAttribute('data-confirm-danger') === 'true';
    }
    if(!msg) return;
    e.preventDefault();
    modalConfirm({ title: title, message: msg, danger: danger, confirmText: confirmText, cancelText: cancelText })
      .then(function(ok){
        if(!ok) return;
        // disable to prevent double-submit, then submit
        if(btn && btn.tagName === 'BUTTON') btn.disabled = true;
        form.submit();
      });
  }, true);
  // also intercept plain button[data-confirm] outside forms (e.g., trigger a fetch)
  document.addEventListener('click', function(e){
    var btn = e.target.closest('[data-confirm]');
    if(!btn) return;
    if(btn.tagName === 'BUTTON' && btn.type === 'submit') return; // handled by submit listener
    if(btn.closest('form')) return;                                // form submit handler covers it
    var msg = btn.getAttribute('data-confirm');
    if(!msg) return;
    e.preventDefault();
    modalConfirm({
      message: msg,
      danger: btn.getAttribute('data-confirm-danger') === 'true',
      confirmText: btn.getAttribute('data-confirm-text'),
    }).then(function(ok){
      if(!ok) return;
      btn.disabled = true;
      // If it has data-href, navigate; if it's a link, follow it
      var href = btn.getAttribute('data-href') || btn.getAttribute('href');
      if(href) window.location.href = href;
    });
  }, true);

  /* ---------- login: show/hide password + submit spinner ---------- */
  document.querySelectorAll('.pw-toggle[data-target]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var el = document.getElementById(btn.getAttribute('data-target'));
      if(!el) return;
      var showing = el.type === 'text';
      el.type = showing ? 'password' : 'text';
      btn.setAttribute('aria-pressed', showing ? 'false' : 'true');
      btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    });
  });
  document.querySelectorAll('form.auth-form').forEach(function(form){
    form.addEventListener('submit', function(){
      form.classList.add('is-submitting');
    });
  });

  /* ---------- flash auto-dismiss + close ---------- */
  function dismissFlash(flash){
    if(flash.classList.contains('is-leaving')) return;
    flash.classList.add('is-leaving');
    setTimeout(function(){ if(flash.parentNode) flash.parentNode.removeChild(flash); }, 260);
  }
  document.querySelectorAll('.flash-stack .flash').forEach(function(flash){
    // wrap text + add close button
    var text = flash.textContent;
    flash.innerHTML = '';
    var span = document.createElement('span'); span.className = 'flash-text'; span.textContent = text;
    var btn = document.createElement('button'); btn.className = 'flash-close'; btn.type='button'; btn.setAttribute('aria-label','Dismiss'); btn.textContent = '\u00d7';
    btn.addEventListener('click', function(){ dismissFlash(flash); });
    flash.appendChild(span); flash.appendChild(btn);
    // success/info auto-dismiss; error stays
    if(!flash.classList.contains('flash-error')){
      setTimeout(function(){ dismissFlash(flash); }, 4500);
    }
  });

  /* ---------- live refresh (monitoring) ---------- */
  var liveRoot = document.querySelector('[data-live="monitoring"]');
  if(liveRoot){
    startLive(liveRoot, 30000);
    startLiveTick(liveRoot, 5000);
  }

  function startLive(root, interval){
    var lastSig = '';
    var timer = null;
    function sig(json){
      var s = json.samples || [];
      if(!s.length) return 'empty';
      var last = s[s.length-1];
      return s.length + ':' + (last.cpu_pct|0) + ':' + (last.mem_pct|0) + ':' + (last.disk_pct|0);
    }
    function tick(){
      fetch('/monitoring/data.json', {credentials:'same-origin', cache:'no-store'})
        .then(function(r){ return r.ok ? r.json() : null; })
        .then(function(json){
          if(!json) return;
          var s = sig(json);
          if(s === lastSig) return;
          lastSig = s;
          applyLiveData(root, json);
        })
        .catch(function(){});
    }
    function onVis(){ if(document.hidden) { stop(); } else { tick(); timer = setInterval(tick, interval); } }
    function stop(){ if(timer) { clearInterval(timer); timer = null; } }
    document.addEventListener('visibilitychange', onVis);
    timer = setInterval(tick, interval);
  }

  function applyLiveData(root, data){
    var byKey = {cpu_pct:[], mem_pct:[], disk_pct:[]};
    (data.samples || []).forEach(function(s){
      if(byKey.cpu_pct)  byKey.cpu_pct.push(s.cpu_pct);
      if(byKey.mem_pct)  byKey.mem_pct.push(s.mem_pct);
      if(byKey.disk_pct) byKey.disk_pct.push(s.disk_pct);
    });
    root.querySelectorAll('.stat-card').forEach(function(card){
      var key = card.getAttribute('data-key');
      var series = byKey[key] || [];
      if(!series.length) return;
      var last = series[series.length-1];
      var avg  = series.reduce(function(a,b){return a+b}, 0) / series.length;
      var mx   = series.reduce(function(a,b){return Math.max(a,b)}, -Infinity);
      // number
      var num = card.querySelector('.count');
      tweenNumber(num, last, {decimals: 0});
      // gauge
      updateGauge(card, last);
      // meta
      var avgEl = card.querySelector('.meta-avg');
      var maxEl = card.querySelector('.meta-max');
      var samEl = card.querySelector('.meta-samples');
      if(avgEl) tweenNumber(avgEl, Math.round(avg*10)/10, {decimals:1});
      if(maxEl) maxEl.textContent = Math.round(mx) + '%';
      if(samEl) samEl.textContent = series.length;
      // sparkline
      var spark = card.querySelector('svg.spark');
      if(spark) updateSpark(spark, series);
      // flash
      if(!reduce){
        card.classList.remove('is-updated');
        // force reflow so the animation restarts
        void card.offsetWidth;
        card.classList.add('is-updated');
      }
    });
  }

  /* ---------- real-time tick (reads /proc directly) ---------- */
  function startLiveTick(root, interval){
    var timer = null;
    var inflight = false;
    function tick(){
      if(inflight) return;
      inflight = true;
      fetch('/monitoring/live.json', {credentials:'same-origin', cache:'no-store'})
        .then(function(r){ return r.ok ? r.json() : null; })
        .then(function(d){ if(d) applyTick(root, d); })
        .catch(function(){})
        .then(function(){ inflight = false; });
    }
    function onVis(){
      if(document.hidden){ stop(); return; }
      tick();
      timer = setInterval(tick, interval);
    }
    function stop(){ if(timer){ clearInterval(timer); timer = null; } }
    document.addEventListener('visibilitychange', onVis);
    timer = setInterval(tick, interval);
  }

  function applyTick(root, d){
    root.querySelectorAll('.stat-card').forEach(function(card){
      var key = card.getAttribute('data-key');
      var v = d[key];
      if(v == null) return;
      var num = card.querySelector('.count');
      if(num){
        // short, no easing — feel instantaneous
        num.textContent = String(Math.round(v));
        num.setAttribute('data-current', v);
        num.setAttribute('data-target', v);
      }
      updateGauge(card, v);
    });
  }

  /* ---------- table enhance (search / filter / pagination) ---------- */
  function enhanceTables(){
    document.querySelectorAll('[data-enhance]').forEach(function(card){
      var cfg = readConfig(card);
      if(!cfg.table) return;
      initTable(card, cfg);
    });
  }

  function readConfig(card){
    var table = card.querySelector('table');
    if(!table) return {};
    return {
      card: card,
      table: table,
      tbody: table.tBodies[0],
      searchIn: card.getAttribute('data-search-in') || '',
      filterCol: card.getAttribute('data-filter-col'),
      pageSizes: (card.getAttribute('data-page-sizes') || '10,25,50,100').split(',').map(Number),
      defaultPage: parseInt(card.getAttribute('data-page-size') || '10', 10),
    };
  }

  function initTable(card, cfg){
    var rows = Array.prototype.slice.call(cfg.tbody.rows);
    rows.forEach(function(r){
      r._text = (r.textContent || '').toLowerCase();
      r._filterVal = cfg.filterCol != null
        ? (r.cells[cfg.filterCol] && r.cells[cfg.filterCol].textContent.trim().toLowerCase())
        : null;
    });
    var state = { q: '', filter: 'all', page: 1, size: cfg.defaultPage };
    var toolRow = document.createElement('div');
    toolRow.className = 'table-toolbar';
    toolRow.innerHTML =
      '<div class="table-search"><span class="search-icon" aria-hidden="true">' + searchSvg() + '</span>' +
      '<input type="search" placeholder="Search\u2026" aria-label="Search"></div>' +
      '<div class="filter-chips" role="tablist"></div>' +
      '<label class="page-size-select">Rows ' +
      '<select>' + cfg.pageSizes.map(function(n){ return '<option value="'+n+'"'+(n===state.size?' selected':'')+'>'+n+'</option>'; }).join('') +
      '</select></label>';

    // insert after the section-head (or at the top of the card)
    var head = card.querySelector(':scope > .section-head');
    if(head && head.nextSibling) card.insertBefore(toolRow, head.nextSibling);
    else if(head) card.appendChild(toolRow);
    else card.insertBefore(toolRow, card.firstChild);

    var pager = document.createElement('div');
    pager.className = 'table-pager';
    card.appendChild(pager);

    var search = toolRow.querySelector('input');
    var chips  = toolRow.querySelector('.filter-chips');
    var size   = toolRow.querySelector('select');

    // build filter chips from data-filter-values (comma-sep) or auto-derive from rows
    var filterValues = (card.getAttribute('data-filter-values') || '').trim();
    var values = filterValues ? filterValues.split('|').map(function(v){ return v.split(':'); })
                              : deriveFilters(rows, cfg.filterCol);
    buildChips(chips, values, state, function(){ apply(); });

    size.addEventListener('change', function(){
      state.size = parseInt(size.value, 10);
      state.page = 1;
      apply();
    });

    var t;
    search.addEventListener('input', function(){
      search.parentNode.classList.toggle('is-searching', !!search.value);
      clearTimeout(t);
      t = setTimeout(function(){
        state.q = (search.value || '').toLowerCase();
        state.page = 1;
        apply();
      }, 100);
    });

    function apply(){
      var matched = rows.filter(function(r){
        var ok = !state.q || (r._text || '').indexOf(state.q) !== -1;
        if(ok && state.filter !== 'all' && cfg.filterCol != null){
          ok = (r._filterVal || '').indexOf(state.filter) !== -1;
        }
        return ok;
      });
      var total = matched.length;
      var pages = Math.max(1, Math.ceil(total / state.size));
      if(state.page > pages) state.page = pages;
      var start = (state.page - 1) * state.size;
      var end   = start + state.size;

      rows.forEach(function(r){ r.classList.add('is-hidden'); });
      matched.slice(start, end).forEach(function(r){ r.classList.remove('is-hidden'); });

      // update chip counts
      updateChipCounts(chips, rows, state, cfg);

      // pager
      renderPager(pager, state, pages, total, function(p){ state.page = p; apply(); });

      // empty state if nothing matched
      var existingEmpty = card.querySelector('.table-empty');
      if(total === 0){
        if(!existingEmpty){
          var e = document.createElement('div');
          e.className = 'empty table-empty';
          e.textContent = 'No matching rows';
          cfg.tbody.parentNode.appendChild(e);
        }
      } else if(existingEmpty){ existingEmpty.parentNode.removeChild(existingEmpty); }
    }
    apply();
  }

  function deriveFilters(rows, col){
    if(col == null) return [['all','All']];
    var set = {};
    rows.forEach(function(r){
      var v = (r.cells[col] && r.cells[col].textContent.trim().toLowerCase()) || '';
      if(v) set[v] = (set[v] || 0) + 1;
    });
    var out = [['all', 'All', rows.length]];
    Object.keys(set).sort().forEach(function(k){
      var label = k.charAt(0).toUpperCase() + k.slice(1);
      out.push([k, label, set[k]]);
    });
    return out;
  }

  function buildChips(host, values, state, onChange){
    host.innerHTML = '';
    values.forEach(function(v){
      var key = v[0], label = v[1], count = v[2];
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip';
      b.setAttribute('aria-pressed', key === state.filter ? 'true' : 'false');
      b.dataset.filter = key;
      b.innerHTML = label + ' <span class="chip-count">' + (count != null ? count : '') + '</span>';
      b.addEventListener('click', function(){
        state.filter = key;
        host.querySelectorAll('.chip').forEach(function(c){ c.setAttribute('aria-pressed', c.dataset.filter === key ? 'true' : 'false'); });
        onChange();
      });
      host.appendChild(b);
    });
  }

  function updateChipCounts(host, rows, state, cfg){
    var counts = { all: rows.length };
    if(cfg.filterCol != null){
      rows.forEach(function(r){
        if(state.q && (r._text || '').indexOf(state.q) === -1) return;
        var k = r._filterVal || '';
        counts[k] = (counts[k] || 0) + 1;
      });
    } else {
      counts = { all: rows.filter(function(r){ return !state.q || (r._text || '').indexOf(state.q) !== -1; }).length };
    }
    host.querySelectorAll('.chip').forEach(function(c){
      var n = counts[c.dataset.filter] || 0;
      var span = c.querySelector('.chip-count');
      if(span) span.textContent = n;
    });
  }

  function renderPager(host, state, pages, total, onPick){
    host.innerHTML = '';
    if(total === 0){
      host.innerHTML = '<span class="pager-info">0 rows</span><div class="pager-controls"></div>';
      return;
    }
    var start = (state.page - 1) * state.size + 1;
    var end   = Math.min(start + state.size - 1, total);
    var info  = document.createElement('span');
    info.className = 'pager-info';
    info.textContent = start + '\u2013' + end + ' of ' + total;
    var ctrls = document.createElement('div');
    ctrls.className = 'pager-controls';
    function btn(label, page, opts){
      opts = opts || {};
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'pager-btn';
      b.textContent = label;
      if(opts.disabled){ b.disabled = true; return b; }
      if(opts.current){ b.setAttribute('aria-current', 'page'); }
      b.addEventListener('click', function(){ onPick(page); });
      return b;
    }
    ctrls.appendChild(btn('\u2039', state.page - 1, {disabled: state.page <= 1}));
    // page list with ellipsis
    var pageList = pagesList(state.page, pages);
    pageList.forEach(function(p){
      if(p === '\u2026'){
        var s = document.createElement('span'); s.className = 'pager-ellipsis'; s.textContent = '\u2026';
        ctrls.appendChild(s);
      } else {
        ctrls.appendChild(btn(String(p), p, {current: p === state.page}));
      }
    });
    ctrls.appendChild(btn('\u203a', state.page + 1, {disabled: state.page >= pages}));
    host.appendChild(info);
    host.appendChild(ctrls);
  }

  function pagesList(current, total){
    if(total <= 7) return Array.from({length: total}, function(_,i){ return i+1; });
    var out = [1];
    if(current > 4) out.push('\u2026');
    var from = Math.max(2, current - 1);
    var to   = Math.min(total - 1, current + 1);
    for(var i=from; i<=to; i++) out.push(i);
    if(current < total - 3) out.push('\u2026');
    out.push(total);
    return out;
  }

  function searchSvg(){
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>';
  }

  /* ---------- run ---------- */
  runGauges();
  runSparks();
  runCounters();
  enhanceTables();
});
