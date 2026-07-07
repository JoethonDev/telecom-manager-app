document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.copy-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      var text=btn.getAttribute('data-copy')||'';
      function done(){var old=btn.textContent;btn.textContent='Copied';btn.classList.add('copied');setTimeout(function(){btn.textContent=old;btn.classList.remove('copied')},1400)}
      if(navigator.clipboard){navigator.clipboard.writeText(text).then(done).catch(function(){fallbackCopy(text);done()})}
      else{fallbackCopy(text);done()}
    });
  });
  function fallbackCopy(text){var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta)}
  var toggle=document.querySelector('.mobile-menu-btn');
  var sidebar=document.querySelector('.sidebar');
  if(toggle&&sidebar){
    toggle.addEventListener('click',function(){var open=sidebar.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});
    document.addEventListener('keydown',function(e){if(e.key==='Escape'){sidebar.classList.remove('open');toggle.setAttribute('aria-expanded','false')}});
    document.querySelectorAll('.side-nav a').forEach(function(a){a.addEventListener('click',function(){sidebar.classList.remove('open');toggle.setAttribute('aria-expanded','false')})});
  }
});
