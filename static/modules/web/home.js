(function () {
  'use strict';
  var MV = window.MV;
  document.body.classList.add('js-reveal');
  var api = MV ? MV.api : null;
  var esc = (MV && MV.escape) || function (s) { return s == null ? '' : String(s); };
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  function emojiFor(c) {
    c = (c || '').toLowerCase();
    if (c.indexOf('sol') !== -1) return '<i class="bi bi-sunglasses"></i>';
    if (c.indexOf('contacto') !== -1) return '<i class="bi bi-eye"></i>';
    if (c.indexOf('armaz') !== -1) return '<i class="bi bi-eyeglasses"></i>';
    return '<i class="bi bi-bag"></i>';
  }
  function initReveal() {
    var els = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
    if (!els.length) return;
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
      }, { threshold: 0.12 });
      els.forEach(function (el) { io.observe(el); });
    } else {
      els.forEach(function (el) { el.classList.add('in'); });
    }
    setTimeout(function () { els.forEach(function (el) { el.classList.add('in'); }); }, 1500);
  }
  function initHeroCTA() {
    if (!MV || !MV.me) return;
    MV.me().then(function (u) {
      if (!u) return;
      if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/panel/'); return; }
      var a1 = document.getElementById('home-cta-1'), a2 = document.getElementById('home-cta-2');
      if (a1) { a1.href = '/catalogo/'; a1.textContent = 'Ir al catálogo'; }
      if (a2) { a2.href = '/citas/'; a2.textContent = 'Agendar cita'; }
    });
  }
  function renderFeatured(list) {
    var grid = document.getElementById('feat-grid');
    if (!grid) return;
    if (!list.length) { grid.innerHTML = '<div class="col-12 text-center text-secondary py-4">Pronto tendremos destacados aquí.</div>'; return; }
    grid.innerHTML = list.map(function (p) {
      var stock = Number(p.stock) || 0;
      var stockTxt = stock <= 0 ? '<span class="mv-feat-stock text-danger">Agotado</span>' : '<span class="mv-feat-stock">Stock: ' + stock + '</span>';
      return '<div class="col-sm-6 col-lg-3"><div class="mv-feat-card">' +
        '<div class="mv-feat-emoji">' + emojiFor(p.categoria_nombre) + '</div>' +
        '<div class="mv-feat-body">' +
          '<span class="mv-feat-cat">' + esc(p.categoria_nombre || '') + '</span>' +
          '<h3 class="mv-feat-name">' + esc(p.nombre) + '</h3>' +
          '<div class="mv-feat-foot"><span class="mv-feat-price">' + money(p.precio) + '</span>' + stockTxt + '</div>' +
          '<a href="/catalogo/" class="btn btn-cta w-100">Ver en catálogo</a>' +
        '</div></div></div>';
    }).join('');
  }
  function loadFeatured() {
    var grid = document.getElementById('feat-grid');
    if (!api || !grid) return;
    api.get('/store/productos/').then(function (r) {
      if (!r.ok || !Array.isArray(r.data)) { grid.innerHTML = '<div class="col-12 text-center text-secondary py-4">No se pudieron cargar los destacados.</div>'; return; }
      var all = r.data;
      var dest = all.filter(function (p) { return p.destacado === true; });
      if (!dest.length) dest = all.slice(0, 4);
      dest = dest.slice(0, 4);
      renderFeatured(dest);
    });
  }
  initReveal();
  initHeroCTA();
  loadFeatured();
})();