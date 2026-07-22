/* =========================================================
   Óptica Matiz Visión — catalogo.js (Fase 09)
   Carga productos/categorias, filtra en cliente, agrega al carrito
   y mantiene el badge del navbar sincronizado.
   ========================================================= */
(function () {
  'use strict';

  var MV = window.MV;
  if (!MV || !MV.api) { console.error('catalogo.js: MV.api no disponible (revisa utils.js).'); return; }

  var api    = MV.api;
  var auth   = MV.auth;
  var toast  = MV.toast;
  var esc    = MV.escape || function (s) { return s; };

  var grid        = document.getElementById('catalogo-grid');
  var catSelect   = document.getElementById('cat-filter');
  var priceRange  = document.getElementById('price-range');
  var priceValue  = document.getElementById('price-value');
  var searchInput = document.getElementById('search-input');
  var resetBtn    = document.getElementById('reset-filters');
  var countInfo   = document.getElementById('count-info');

  var ALL = [];          // productos completos
  var MAX_PRICE = 150000;

  var priceFmt = new Intl.NumberFormat('es-CL', {
    style: 'currency', currency: 'CLP', maximumFractionDigits: 0
  });
  function formatPrice(n) { return priceFmt.format(Number(n) || 0); }

  function emojiFor(catName) {
    var c = (catName || '').toLowerCase();
    if (c.indexOf('sol') !== -1)      return '🕶️';
    if (c.indexOf('contacto') !== -1) return '👁️';
    if (c.indexOf('armaz') !== -1)    return '👓';
    return '🛍️';
  }

  /* ---------- Badge del carrito ---------- */
  function refreshCartBadge() {
    var badge = document.getElementById('cart-badge');
    if (!badge) return;
    if (!auth || !auth.isAuthenticated()) { badge.hidden = true; badge.textContent = '0'; return; }
    api.get('/orders/carrito/').then(function (r) {
      if (!r.ok || !Array.isArray(r.data)) { badge.hidden = true; badge.textContent = '0'; return; }
      var total = r.data.reduce(function (acc, it) { return acc + (Number(it.cantidad) || 0); }, 0);
      badge.textContent = String(total);
      badge.hidden = total <= 0;
    });
  }
  // Lo expongo para reutilizarlo desde otros módulos (cart.js, checkout, etc.)
  MV.refreshCartBadge = refreshCartBadge;

  /* ---------- Render de tarjetas ---------- */
  function cardHtml(p) {
    var stock = Number(p.stock) || 0;
    var agotado = stock <= 0;
    var desc = p.descripcion ? esc(p.descripcion) : 'Producto de óptica de alta calidad.';
    var stockBadge = agotado
      ? '<span class="stock-badge text-danger fw-bold">Agotado</span>'
      : '<span class="stock-badge">Stock: ' + stock + '</span>';
    var btn = agotado
      ? '<button class="btn btn-secondary w-100 btn-add" disabled>Agotado</button>'
      : '<button class="btn btn-cta w-100 btn-add" data-id="' + p.id + '">+ Agregar</button>';

    return '' +
      '<div class="col-sm-6 col-lg-4">' +
        '<div class="mv-product-card">' +
          '<div class="mv-product-emoji">' + emojiFor(p.categoria_nombre) + '</div>' +
          '<div class="mv-product-body">' +
            '<span class="mv-product-cat">' + esc(p.categoria_nombre || '') + '</span>' +
            '<h3 class="mv-product-name">' + esc(p.nombre) + '</h3>' +
            '<p class="mv-product-desc">' + desc + '</p>' +
            '<div class="mv-product-foot">' +
              '<span class="mv-product-price">' + formatPrice(p.precio) + '</span>' +
              stockBadge +
            '</div>' +
            btn +
          '</div>' +
        '</div>' +
      '</div>';
  }

  function render(list) {
    if (!list.length) {
      grid.innerHTML = '<div class="col-12 mv-empty">No hay productos que coincidan con los filtros.</div>';
    } else {
      grid.innerHTML = list.map(cardHtml).join('');
    }
    countInfo.textContent = 'Mostrando ' + list.length + ' de ' + ALL.length + ' productos';
  }

  /* ---------- Filtros en cliente ---------- */
  function applyFilters() {
    var q    = (searchInput.value || '').trim().toLowerCase();
    var cat  = catSelect.value;
    var maxP = Number(priceRange.value);
    priceValue.textContent = formatPrice(maxP);

    var filtered = ALL.filter(function (p) {
      if (cat && String(p.categoria) !== cat) return false;
      if ((Number(p.precio) || 0) > maxP) return false;
      if (q) {
        var hay = (p.nombre || '').toLowerCase().indexOf(q) !== -1 ||
                  (p.descripcion || '').toLowerCase().indexOf(q) !== -1 ||
                  (p.categoria_nombre || '').toLowerCase().indexOf(q) !== -1;
        if (!hay) return false;
      }
      return true;
    });
    render(filtered);
  }

  /* ---------- Agregar al carrito ---------- */
  function addToCart(id, btn) {
    if (!auth || !auth.isAuthenticated()) {
      toast('Inicia sesión para agregar al carrito.', 'error');
      window.location.href = '/login/?next=/catalogo/';
      return;
    }
    if (btn) { btn.disabled = true; btn.textContent = 'Agregando…'; }
    api.post('/orders/carrito/', { body: { producto: Number(id), cantidad: 1 } })
      .then(function (r) {
        if (r.ok) {
          toast('Producto agregado al carrito.', 'success');
          refreshCartBadge();
        } else {
          var msg = 'No se pudo agregar al carrito.';
          if (r.data && r.data.cantidad) msg = Array.isArray(r.data.cantidad) ? r.data.cantidad[0] : r.data.cantidad;
          else if (r.data && r.data.detail) msg = r.data.detail;
          toast(msg, 'error');
        }
      })
      .finally(function () {
        if (btn && !btn.disabled === false) { /* noop */ }
        if (btn) { btn.disabled = false; btn.textContent = '+ Agregar'; }
      });
  }

  // Delegación de clics sobre la grilla
  grid.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-add');
    if (!btn || btn.disabled) return;
    addToCart(btn.getAttribute('data-id'), btn);
  });

  /* ---------- Listeners de filtros ---------- */
  searchInput.addEventListener('input', applyFilters);
  priceRange.addEventListener('input', applyFilters);
  catSelect.addEventListener('change', applyFilters);
  resetBtn.addEventListener('click', function () {
    searchInput.value = '';
    catSelect.value = '';
    priceRange.value = String(MAX_PRICE);
    applyFilters();
  });

  /* ---------- Carga inicial ---------- */
  function init() {
    Promise.all([
      api.get('/store/productos/'),
      api.get('/store/categorias/')
    ]).then(function (res) {
      var rp = res[0], rc = res[1];

      if (!rp.ok || !Array.isArray(rp.data)) {
        grid.innerHTML = '<div class="col-12 mv-empty">No se pudo cargar el catálogo. Revisa la conexión con la API.</div>';
        countInfo.textContent = '';
        return;
      }
      ALL = rp.data;

      // Rango de precio según el producto más caro
      if (ALL.length) {
        MAX_PRICE = Math.max.apply(null, ALL.map(function (p) { return Number(p.precio) || 0; }));
        MAX_PRICE = Math.ceil(MAX_PRICE / 1000) * 1000 || 150000;
      }
      priceRange.max = String(MAX_PRICE);
      priceRange.value = String(MAX_PRICE);

      // Select de categorías
      if (rc.ok && Array.isArray(rc.data)) {
        rc.data.forEach(function (c) {
          var opt = document.createElement('option');
          opt.value = String(c.id);
          opt.textContent = c.nombre;
          catSelect.appendChild(opt);
        });
      }

      applyFilters();   // render inicial con todos los productos
      refreshCartBadge();
    });
  }

  init();
})();