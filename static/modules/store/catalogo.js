(function () {
  'use strict';
  var MV = window.MV;
  if (!MV || !MV.api) { console.error('catalogo.js: MV.api no disponible.'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape || function (s) { return s; };
  var grid = document.getElementById('catalogo-grid');
  var catSelect = document.getElementById('cat-filter');
  var priceRange = document.getElementById('price-range');
  var priceValue = document.getElementById('price-value');
  var searchInput = document.getElementById('search-input');
  var resetBtn = document.getElementById('reset-filters');
  var countInfo = document.getElementById('count-info');
  var ALL = [], cartMap = {}, MAX_PRICE = 150000;

  var priceFmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
  function formatPrice(n) { return priceFmt.format(Number(n) || 0); }
  function emojiFor(c) { c = (c || '').toLowerCase(); if (c.indexOf('sol') !== -1) return '🕶️'; if (c.indexOf('contacto') !== -1) return '👁️'; if (c.indexOf('armaz') !== -1) return '👓'; return '🛍️'; }
  function stockOf(id) { var p = ALL.find(function (x) { return String(x.id) === String(id); }); return p ? (Number(p.stock) || 0) : 0; }
  function badge() { if (MV.refreshCartBadge) MV.refreshCartBadge(); }
  function errMsg(r) {
    if (r.data && r.data.cantidad) return Array.isArray(r.data.cantidad) ? r.data.cantidad[0] : r.data.cantidad;
    if (r.data && r.data.stock) return Array.isArray(r.data.stock) ? r.data.stock[0] : r.data.stock;
    if (r.data && r.data.detail) return r.data.detail;
    return 'No se pudo actualizar el carrito.';
  }

  function addBtnHtml(id, agotado) {
    var inner = agotado
      ? '<button class="btn btn-secondary w-100" disabled>Agotado</button>'
      : '<button class="btn btn-cta w-100 btn-add" data-id="' + id + '">+ Agregar</button>';
    return '<div class="mv-add-slot" data-id="' + id + '">' + inner + '</div>';
  }
  function qtySlotHtml(id, itemId, qty, stock) {
    var disInc = (Number(qty) >= Number(stock)) ? ' disabled' : '';
    return '<div class="mv-add-slot" data-id="' + id + '">' +
      '<div class="mv-qty-card">' +
        '<button type="button" class="mv-q-dec" data-id="' + id + '" data-item="' + itemId + '">−</button>' +
        '<span class="mv-q-num">' + qty + '</span>' +
        '<button type="button" class="mv-q-inc" data-id="' + id + '" data-item="' + itemId + '" data-stock="' + stock + '"' + disInc + '>+</button>' +
      '</div></div>';
  }
  function cardHtml(p) {
    var stock = Number(p.stock) || 0;
    var agotado = stock <= 0;
    var inCart = cartMap[p.id];
    var slot = (!agotado && inCart && inCart.cantidad > 0) ? qtySlotHtml(p.id, inCart.item_id, inCart.cantidad, stock) : addBtnHtml(p.id, agotado);
    var desc = p.descripcion ? esc(p.descripcion) : 'Producto de óptica de alta calidad.';
    var stockBadge = agotado ? '<span class="stock-badge text-danger fw-bold">Agotado</span>' : '<span class="stock-badge">Stock: ' + stock + '</span>';
    return '<div class="col-sm-6 col-lg-4"><div class="mv-product-card">' +
      '<div class="mv-product-emoji">' + emojiFor(p.categoria_nombre) + '</div>' +
      '<div class="mv-product-body">' +
        '<span class="mv-product-cat">' + esc(p.categoria_nombre || '') + '</span>' +
        '<h3 class="mv-product-name">' + esc(p.nombre) + '</h3>' +
        '<p class="mv-product-desc">' + desc + '</p>' +
        '<div class="mv-product-foot"><span class="mv-product-price">' + formatPrice(p.precio) + '</span>' + stockBadge + '</div>' +
        slot +
      '</div></div></div>';
  }
  function render(list) {
    grid.innerHTML = list.length ? list.map(cardHtml).join('') : '<div class="col-12 mv-empty">No hay productos que coincidan con los filtros.</div>';
    countInfo.textContent = 'Mostrando ' + list.length + ' de ' + ALL.length + ' productos';
  }
  function applyFilters() {
    var q = (searchInput.value || '').trim().toLowerCase();
    var cat = catSelect.value;
    var maxP = Number(priceRange.value);
    priceValue.textContent = formatPrice(maxP);
    render(ALL.filter(function (p) {
      if (cat && String(p.categoria) !== cat) return false;
      if ((Number(p.precio) || 0) > maxP) return false;
      if (q) {
        var hay = (p.nombre || '').toLowerCase().indexOf(q) !== -1 || (p.descripcion || '').toLowerCase().indexOf(q) !== -1 || (p.categoria_nombre || '').toLowerCase().indexOf(q) !== -1;
        if (!hay) return false;
      }
      return true;
    }));
  }

  function doAdd(btn) {
    if (!MV.auth.isAuthenticated()) { MV.ensureGuest().then(function (ok) { if (ok) { doAdd(btn); } }); return; }
    var id = btn.getAttribute('data-id');
    btn.disabled = true; btn.textContent = '…';
    api.post('/orders/carrito/', { body: { producto: Number(id), cantidad: 1 } }).then(function (r) {
      if (r.ok) {
        cartMap[id] = { item_id: r.data.id, cantidad: r.data.cantidad };
        var slot = btn.closest('.mv-add-slot');
        slot.outerHTML = qtySlotHtml(id, r.data.id, r.data.cantidad, stockOf(id));
        toast('Producto agregado al carrito.', 'success'); badge();
      } else { toast(errMsg(r), 'error'); btn.disabled = false; btn.textContent = '+ Agregar'; }
    });
  }
  function doInc(btn) {
    var id = btn.getAttribute('data-id'), item = btn.getAttribute('data-item'), stock = Number(btn.getAttribute('data-stock'));
    var cur = cartMap[id] ? cartMap[id].cantidad : 0, nueva = cur + 1;
    if (nueva > stock) { toast('Stock máximo alcanzado.', 'error'); return; }
    var slot = btn.closest('.mv-add-slot'), decBtn = slot.querySelector('.mv-q-dec');
    btn.disabled = true; decBtn.disabled = true;
    api.patch('/orders/carrito/' + item + '/', { body: { cantidad: nueva } }).then(function (r) {
      if (r.ok) {
        cartMap[id] = { item_id: item, cantidad: r.data.cantidad };
        slot.querySelector('.mv-q-num').textContent = r.data.cantidad;
        slot.querySelector('.mv-q-inc').disabled = (Number(r.data.cantidad) >= stock);
        decBtn.disabled = false; badge();
      } else { toast(errMsg(r), 'error'); btn.disabled = false; decBtn.disabled = false; }
    });
  }
  function doDec(btn) {
    var id = btn.getAttribute('data-id'), item = btn.getAttribute('data-item');
    var cur = cartMap[id] ? cartMap[id].cantidad : 1, nueva = cur - 1;
    var slot = btn.closest('.mv-add-slot'), incBtn = slot.querySelector('.mv-q-inc');
    btn.disabled = true; incBtn.disabled = true;
    if (nueva <= 0) {
      api.delete('/orders/carrito/' + item + '/').then(function (r) {
        if (r.ok) { delete cartMap[id]; slot.outerHTML = addBtnHtml(id, false); toast('Producto quitado del carrito.', 'success'); badge(); }
        else { toast(errMsg(r), 'error'); btn.disabled = false; incBtn.disabled = false; }
      });
    } else {
      api.patch('/orders/carrito/' + item + '/', { body: { cantidad: nueva } }).then(function (r) {
        if (r.ok) { cartMap[id] = { item_id: item, cantidad: r.data.cantidad }; slot.querySelector('.mv-q-num').textContent = r.data.cantidad; btn.disabled = false; incBtn.disabled = false; badge(); }
        else { toast(errMsg(r), 'error'); btn.disabled = false; incBtn.disabled = false; }
      });
    }
  }

  grid.addEventListener('click', function (e) {
    var a = e.target.closest('.btn-add'); if (a && !a.disabled) { doAdd(a); return; }
    var i = e.target.closest('.mv-q-inc'); if (i && !i.disabled) { doInc(i); return; }
    var d = e.target.closest('.mv-q-dec'); if (d && !d.disabled) { doDec(d); return; }
  });
  searchInput.addEventListener('input', applyFilters);
  priceRange.addEventListener('input', applyFilters);
  catSelect.addEventListener('change', applyFilters);
  resetBtn.addEventListener('click', function () { searchInput.value = ''; catSelect.value = ''; priceRange.value = String(MAX_PRICE); applyFilters(); });

  function loadCartMap() {
    if (!auth.isAuthenticated()) return Promise.resolve({});
    return api.get('/orders/carrito/').then(function (r) {
      var m = {};
      if (r.ok && Array.isArray(r.data)) r.data.forEach(function (it) { m[it.producto] = { item_id: it.id, cantidad: it.cantidad }; });
      return m;
    });
  }
  Promise.all([api.get('/store/productos/'), api.get('/store/categorias/'), loadCartMap()]).then(function (res) {
    var rp = res[0], rc = res[1]; cartMap = res[2] || {};
    if (!rp.ok || !Array.isArray(rp.data)) { grid.innerHTML = '<div class="col-12 mv-empty">No se pudo cargar el catálogo.</div>'; countInfo.textContent = ''; return; }
    ALL = rp.data;
    if (ALL.length) { MAX_PRICE = Math.max.apply(null, ALL.map(function (p) { return Number(p.precio) || 0; })); MAX_PRICE = Math.ceil(MAX_PRICE / 1000) * 1000 || 150000; }
    priceRange.max = String(MAX_PRICE); priceRange.value = String(MAX_PRICE);
    if (rc.ok && Array.isArray(rc.data)) rc.data.forEach(function (c) { var o = document.createElement('option'); o.value = String(c.id); o.textContent = c.nombre; catSelect.appendChild(o); });
    applyFilters(); badge();
  });
})();