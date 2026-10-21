(function () {
  var TEXT = 'Welcome to Sarthak34 hosting. Need help? Open a ticket on our Discord.'; // edit me
  var KEY = 's34-bar-dismissed';
  function mount() {
    if (document.getElementById('s34-bar')) return;
    try { if (sessionStorage.getItem(KEY)) return; } catch (e) {}
    var bar = document.createElement('div');
    bar.id = 's34-bar';
    var msg = document.createElement('span'); msg.textContent = TEXT;
    var x = document.createElement('button'); x.type = 'button'; x.setAttribute('aria-label', 'Dismiss'); x.textContent = '\u00d7';
    x.onclick = function () { bar.remove(); try { sessionStorage.setItem(KEY, '1'); } catch (e) {} };
    bar.appendChild(msg); bar.appendChild(x);
    document.body.prepend(bar);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
