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

  /* ---------- run ---------- */
  runGauges();
  runSparks();
  runCounters();
});
