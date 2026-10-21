(function () {
  function mount() {
    if (document.getElementById('s34-credit')) return;
    var d = document.createElement('div'); d.id = 's34-credit'; d.textContent = 'Theme by Sarthak34';
    document.body.appendChild(d);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
