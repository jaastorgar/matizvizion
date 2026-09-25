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
var WA_META = document.querySelector('meta[name=whatsapp-asesor]');
var WHATSAPP_NUM = (WA_META && WA_META.content) ? WA_META.content.trim() : '56964126663'; // <- PON AQUI TU NUMERO REAL con codigo de pais, ej: 569xxxxxxxx
function waLink(msg){ return 'https://wa.me/' + WHATSAPP_NUM + '?text=' + encodeURIComponent(msg); }
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
function addBtnHtml(id, agotado, configurable) {
  var inner = agotado
    ? '<button class="btn btn-secondary w-100" disabled>Agotado</button>'
    : (configurable
        ? '<button class="btn btn-cta w-100 btn-add-config" data-id="' + id + '"><i class="bi bi-bullseye"></i> Elegir lentes</button>'
        : '<button class="btn btn-cta w-100 btn-add" data-id="' + id + '">+ Agregar</button>');
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
function mediaHtml(p) {
  return p.imagen_url
    ? '<div class="mv-product-emoji"><img src="' + p.imagen_url + '" alt="' + esc(p.nombre) + '" loading="lazy" /></div>'
    : '<div class="mv-product-emoji">' + emojiFor(p.categoria_nombre) + '</div>';
}
function swatchesHtml(p, members) {
  if (!members || members.length < 2) return '';
  return '<div class="mv-swatches">' + members.map(function (m) {
    var bg = m.imagen_url ? ' style="background-image:url(\'' + m.imagen_url + '\')"' : '';
    return '<button type="button" class="mv-swatch' + (String(m.id) === String(p.id) ? ' active' : '') + '" data-pid="' + m.id + '"' + bg + ' title="' + esc(m.color || m.nombre) + '"></button>';
  }).join('') + '<span class="mv-swatch-label">' + esc(p.color || '') + '</span></div>';
}
function cardHtml(p, members) {
  var stock = Number(p.stock) || 0;
  var agotado = stock <= 0;
  var inCart = cartMap[p.id];
  var slot = (!agotado && inCart && inCart.cantidad > 0) ? qtySlotHtml(p.id, inCart.item_id, inCart.cantidad, stock) : addBtnHtml(p.id, agotado, p.configurable_lente);
  var cfgBadge = (inCart && inCart.tipo_lente) ? '<div class="mv-lente-cfg"><i class="bi bi-bullseye"></i> ' + esc(inCart.tipo_lente_display || inCart.tipo_lente) + ' · ' + esc(inCart.uso_lente_display || inCart.uso_lente) + '</div>' : '';
  var desc = p.descripcion ? esc(p.descripcion) : 'Producto de óptica de alta calidad.';
  var stockBadge = agotado ? '<span class="stock-badge text-danger fw-bold">Agotado</span>' : '<span class="stock-badge">Stock: ' + stock + '</span>';
  var catName = (p.categoria_nombre || '').toLowerCase();
  var isArmazon = catName.indexOf('armaz') !== -1 || catName.indexOf('sol') !== -1 || !!p.imagen_tryon_url || !!p.configurable_lente;
  var tryonBtn = isArmazon
    ? '<button type="button" class="mv-btn-tryon" data-tryon="' + p.id + '"><i class="bi bi-camera-video-fill"></i> Probar en mi rostro</button>'
    : '';
  return '<div class="col-sm-6 col-lg-4"><div class="mv-product-card">' +
    mediaHtml(p) +
    '<div class="mv-product-body">' +
    '<span class="mv-product-cat">' + esc(p.categoria_nombre || '') + '</span>' +
    '<h3 class="mv-product-name">' + esc(p.nombre) + '</h3>' + cfgBadge +
    swatchesHtml(p, members) +
    '<p class="mv-product-desc">' + desc + '</p>' +
    '<div class="mv-product-foot"><span class="mv-product-price">' + formatPrice(p.precio) + '</span>' + stockBadge + '<button type="button" class="mv-wa-card-btn" data-wa="' + p.id + '" title="Consultar por WhatsApp"><i class="bi bi-whatsapp"></i></button></div>' +
    tryonBtn +
    slot +
    '</div></div></div>';
}
function render(list) {
  var seen = {};
  var html = [];
  list.forEach(function (p) {
    if (p.grupo) {
      if (seen[p.grupo]) return;
      seen[p.grupo] = true;
      var members = list.filter(function (x) { return x.grupo === p.grupo; });
      html.push(cardHtml(members[0], members));
    } else {
      html.push(cardHtml(p, null));
    }
  });
  grid.innerHTML = html.length ? html.join('') : '<div class="col-12 mv-empty">No hay productos que coincidan con los filtros.</div>';
  countInfo.textContent = 'Mostrando ' + html.length + ' de ' + ALL.length + ' productos';
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
      var hay = (p.nombre || '').toLowerCase().indexOf(q) !== -1 || (p.descripcion || '').toLowerCase().indexOf(q) !== -1 || (p.categoria_nombre || '').toLowerCase().indexOf(q) !== -1 || (p.color || '').toLowerCase().indexOf(q) !== -1;
      if (!hay) return false;
    }
    return true;
  }));
}
function doAdd(btn, cfg) {
  if (!MV.auth.isAuthenticated()) { MV.ensureGuest().then(function (ok) { if (ok) { doAdd(btn); } }); return; }
  var id = btn.getAttribute('data-id');
  btn.disabled = true; btn.textContent = '…';
  api.post('/orders/carrito/', { body: { producto: Number(id), cantidad: 1, tipo_lente: (cfg && cfg.tipo) || '', uso_lente: (cfg && cfg.uso) || '' } }).then(function (r) {
    if (r.ok) {
      cartMap[id] = { item_id: r.data.id, cantidad: r.data.cantidad, tipo_lente: r.data.tipo_lente, tipo_lente_display: r.data.tipo_lente_display, uso_lente_display: r.data.uso_lente_display };
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
  var sw = e.target.closest('.mv-swatch');
  if (sw) {
    var pid = sw.getAttribute('data-pid');
    var prod = ALL.find(function (x) { return String(x.id) === String(pid); });
    if (!prod) return;
    var members = prod.grupo ? ALL.filter(function (x) { return x.grupo === prod.grupo; }) : null;
    var col = sw.closest('.col-sm-6');
    if (col) col.outerHTML = cardHtml(prod, members);
    return;
  }
  var wa = e.target.closest('.mv-wa-card-btn');
  if (wa) {
    var wpid = wa.getAttribute('data-wa');
    var wprod = ALL.find(function (x){ return String(x.id) === String(wpid); });
    if (wprod) {
      var wmsg = 'Hola Matiz Visión! Me interesa "' + wprod.nombre + '"' +
        (wprod.sku ? ' (SKU ' + wprod.sku + ')' : '') +
        (wprod.color ? ' en color ' + wprod.color : '') +
        ' a ' + formatPrice(wprod.precio) + '. ¿Me pueden asesorar?';
      window.open(waLink(wmsg), '_blank', 'noopener');
    }
    return;
  }
  var tb = e.target.closest('.mv-btn-tryon');
  if (tb) {
    var tpid = tb.getAttribute('data-tryon');
    var tprod = ALL.find(function (x) { return String(x.id) === String(tpid); });
    if (tprod && window.MV && window.MV.openTryon) {
      window.MV.openTryon(tprod, ALL);
    }
    return;
  }
  var ac = e.target.closest('.btn-add-config'); if (ac && !ac.disabled) { openLenteModal(ac); return; }
  var a = e.target.closest('.btn-add'); if (a && !a.disabled) { doAdd(a); return; }
  var i = e.target.closest('.mv-q-inc'); if (i && !i.disabled) { doInc(i); return; }
  var d = e.target.closest('.mv-q-dec'); if (d && !d.disabled) { doDec(d); return; }
});
searchInput.addEventListener('input', applyFilters);
priceRange.addEventListener('input', applyFilters);
catSelect.addEventListener('change', applyFilters);
resetBtn.addEventListener('click', function () { searchInput.value = ''; catSelect.value = ''; priceRange.value = String(MAX_PRICE); applyFilters(); });
var btnHero = document.getElementById('btn-hero-tryon');
if (btnHero) {
  btnHero.addEventListener('click', function () {
    if (!ALL || !ALL.length) return;
    var armazon = ALL.find(function (p) {
      var cat = (p.categoria_nombre || '').toLowerCase();
      return cat.indexOf('armaz') !== -1 || cat.indexOf('sol') !== -1 || !!p.imagen_tryon_url || !!p.configurable_lente;
    }) || ALL[0];
    if (window.MV && window.MV.openTryon) {
      window.MV.openTryon(armazon, ALL);
    }
  });
}
function loadCartMap() {
  if (!auth.isAuthenticated()) return Promise.resolve({});
  return api.get('/orders/carrito/').then(function (r) {
    var m = {};
    if (r.ok && Array.isArray(r.data)) r.data.forEach(function (it) { m[it.producto] = { item_id: it.id, cantidad: it.cantidad, tipo_lente: it.tipo_lente, tipo_lente_display: it.tipo_lente_display, uso_lente_display: it.uso_lente_display }; });
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


// ---- Asesor WhatsApp: boton flotante + estilos ----
(function () {
  if (document.getElementById('mv-wa-css')) return;
  var s = document.createElement('style'); s.id = 'mv-wa-css';
  s.textContent = '.mv-wa-float{position:fixed;right:18px;bottom:18px;z-index:1050;width:56px;height:56px;border-radius:50%;background:#25D366;color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.7rem;box-shadow:0 10px 26px rgba(0,0,0,.25);border:none;cursor:pointer;transition:transform .15s ease;}' +
    '.mv-wa-float:hover{transform:scale(1.08);}' +
    '.mv-wa-card-btn{border:none;background:#25D366;color:#fff;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.05rem;cursor:pointer;flex:0 0 auto;margin-left:.4rem;transition:transform .12s ease;}' +
    '.mv-wa-card-btn:hover{transform:scale(1.12);}';
  document.head.appendChild(s);
  if (document.getElementById('mv-wa-float')) return;
  var b = document.createElement('button');
  b.id = 'mv-wa-float'; b.type = 'button'; b.className = 'mv-wa-float';
  b.title = 'Chatear con un asesor por WhatsApp';
  b.setAttribute('aria-label', 'Chatear con un asesor por WhatsApp');
  b.innerHTML = '<i class="bi bi-whatsapp"></i>';
  b.addEventListener('click', function () {
    window.open(waLink('Hola Matiz Visión! Quiero asesoría óptica personalizada.'), '_blank', 'noopener');
  });
  document.body.appendChild(b);
})();

// ---- Configurador optico: tipo de lente + distancia de uso (Guia Tecnica 2026) ----
var LENTE_TIPOS = [
  { v: 'MONOFOCAL', t: 'Monofocal (foco único)', d: 'Un solo poder en todo el lente. Miopía, astigmatismo, hipermetropía o lectura exclusiva.', usos: ['LEJOS','CERCA'], def: 'LEJOS' },
  { v: 'BIFOCAL', t: 'Bifocal (doble foco)', d: 'Zona superior para lejos y segmento inferior para cerca, con línea visible.', usos: ['LEJOS_CERCA'], def: 'LEJOS_CERCA' },
  { v: 'PROGRESIVO', t: 'Progresivo / multifocal', d: 'Visión continua lejos-intermedia-cerca sin cortes estéticos visibles.', usos: ['LEJOS_CERCA'], def: 'LEJOS_CERCA' },
  { v: 'OCUPACIONAL', t: 'Ocupacional / degresivo', d: 'Optimiza intermedia (40 cm–2 m) y cerca; pasillos hasta 60% más amplios. Ideal pantallas.', usos: ['INTERMEDIA','CERCA'], def: 'INTERMEDIA' }
];
var LENTE_USOS = [
  { v: 'LEJOS', t: 'Visión lejos' },
  { v: 'CERCA', t: 'Visión cerca (lectura)' },
  { v: 'LEJOS_CERCA', t: 'Lejos y cerca' },
  { v: 'INTERMEDIA', t: 'Intermedia (pantallas 40 cm–2 m)' }
];
function openLenteModal(btn) {
  if (document.getElementById('mv-lente-ov')) return;
  var ov = document.createElement('div'); ov.id = 'mv-lente-ov'; ov.className = 'mv-lente-ov';
  ov.innerHTML =
    '<div class="mv-lente-card" role="dialog" aria-modal="true">' +
    '<button type="button" class="mv-lente-x" aria-label="Cerrar"><i class="bi bi-x-lg"></i></button>' +
    '<span class="mv-lente-eyebrow"><i class="bi bi-bullseye"></i> Configurador óptico</span>' +
    '<h3>Elige el diseño de tus lentes</h3>' +
    '<div class="mv-lente-label">1 · Diseño focal</div>' +
    '<div class="mv-lente-opts" id="mv-lente-tipos">' + LENTE_TIPOS.map(function (t, i) {
      return '<label class="mv-lente-opt"><input type="radio" name="mv-tipo" value="' + t.v + '"' + (i === 0 ? ' checked' : '') + ' /><span><strong>' + t.t + '</strong><small>' + t.d + '</small></span></label>';
    }).join('') + '</div>' +
    '<div class="mv-lente-label">2 · Distancia de uso</div>' +
    '<div class="mv-lente-opts" id="mv-lente-usos">' + LENTE_USOS.map(function (u) {
      return '<label class="mv-lente-opt compact"><input type="radio" name="mv-uso" value="' + u.v + '" /><span>' + u.t + '</span></label>';
    }).join('') + '</div>' +
    '<div class="mv-lente-hint" id="mv-lente-hint"></div>' +
    '<div class="mv-lente-foot"><button type="button" class="btn btn-outline-mv btn-sm" id="mv-lente-cancel">Cancelar</button>' +
    '<button type="button" class="btn btn-cta" id="mv-lente-ok"><i class="bi bi-cart-plus"></i> Agregar al carrito</button></div></div>';
  document.body.appendChild(ov);
  function tipoSel() { return LENTE_TIPOS.filter(function (x) { return x.v === ov.querySelector('input[name=mv-tipo]:checked').value; })[0]; }
  function syncUsos() {
    var t = tipoSel();
    ov.querySelectorAll('input[name=mv-uso]').forEach(function (r) {
      var ok = t.usos.indexOf(r.value) !== -1;
      r.disabled = !ok;
      r.closest('.mv-lente-opt').style.opacity = ok ? '1' : '.45';
      if (ok && r.value === t.def) r.checked = true;
      if (!ok && r.checked) r.checked = false;
    });
    if (!ov.querySelector('input[name=mv-uso]:checked')) {
      var d = ov.querySelector('input[name=mv-uso][value="' + t.def + '"]'); if (d) d.checked = true;
    }
    ov.querySelector('#mv-lente-hint').innerHTML = '<i class="bi bi-info-circle"></i> ' + t.d;
  }
  ov.querySelectorAll('input[name=mv-tipo]').forEach(function (r) { r.addEventListener('change', syncUsos); });
  syncUsos();
  function close() { if (ov.parentNode) ov.parentNode.removeChild(ov); }
  ov.querySelector('.mv-lente-x').addEventListener('click', close);
  ov.querySelector('#mv-lente-cancel').addEventListener('click', close);
  ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
  ov.querySelector('#mv-lente-ok').addEventListener('click', function () {
    var uso = ov.querySelector('input[name=mv-uso]:checked');
    if (!uso) { toast('Elige la distancia de uso.', 'error'); return; }
    close();
    doAdd(btn, { tipo: tipoSel().v, uso: uso.value });
  });
}
(function () {
  if (document.getElementById('mv-lente-css')) return;
  var s = document.createElement('style'); s.id = 'mv-lente-css';
  s.textContent = '.mv-lente-cfg{font-size:.75rem;color:var(--green-dark);background:rgba(16,185,129,.1);border-radius:8px;padding:.15rem .5rem;display:inline-flex;align-items:center;gap:.3rem;margin:.1rem 0 .4rem;}' +
    '.mv-lente-ov{position:fixed;inset:0;z-index:2100;display:flex;align-items:center;justify-content:center;background:rgba(17,24,39,.55);backdrop-filter:blur(3px);padding:1rem;}' +
    '.mv-lente-card{width:100%;max-width:560px;max-height:90vh;overflow:auto;background:var(--white);border-radius:16px;padding:1.6rem;box-shadow:0 30px 70px rgba(17,24,39,.4);position:relative;}' +
    '.mv-lente-x{position:absolute;top:.8rem;right:.8rem;border:none;background:transparent;font-size:1.1rem;cursor:pointer;color:var(--lead-muted,#6B7280);}' +
    '.mv-lente-eyebrow{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--green-dark);display:flex;gap:.4rem;align-items:center;}' +
    '.mv-lente-card h3{font-family:var(--font-head);font-weight:800;margin:.3rem 0 1rem;}' +
    '.mv-lente-label{font-size:.78rem;font-weight:700;color:var(--lead-muted,#6B7280);margin:.6rem 0 .4rem;}' +
    '.mv-lente-opts{display:flex;flex-direction:column;gap:.5rem;}' +
    '.mv-lente-opt{display:flex;gap:.6rem;border:1px solid var(--border-color);border-radius:12px;padding:.6rem .8rem;cursor:pointer;}' +
    '.mv-lente-opt:has(input:checked){border-color:var(--green-primary);box-shadow:0 0 0 3px rgba(16,185,129,.15);}' +
    '.mv-lente-opt input{margin-top:.2rem;accent-color:var(--green-primary);}' +
    '.mv-lente-opt span{display:flex;flex-direction:column;}' +
    '.mv-lente-opt.compact span{flex-direction:row;}' +
    '.mv-lente-opt small{color:var(--lead-muted,#6B7280);}' +
    '.mv-lente-hint{font-size:.8rem;color:var(--lead-muted,#6B7280);background:var(--lead-light);border-radius:10px;padding:.5rem .7rem;margin:.8rem 0;}' +
    '.mv-lente-foot{display:flex;justify-content:flex-end;gap:.6rem;}';
  document.head.appendChild(s);
})();

// ---- Botón sticky "Ir al carrito" con total en vivo ----
(function () {
  var stickyEl = document.getElementById('mv-cart-sticky');
  var countEl  = document.getElementById('mv-cart-sticky-count');
  var totalEl  = document.getElementById('mv-cart-sticky-total');
  if (!stickyEl || !countEl || !totalEl) return;

  function updateCartSticky() {
    var items = 0, total = 0;
    for (var pid in cartMap) {
      if (!cartMap.hasOwnProperty(pid)) continue;
      var it = cartMap[pid];
      var p  = ALL.find(function (x) { return String(x.id) === String(pid); });
      if (!p || !it || !it.cantidad) continue;
      items += Number(it.cantidad);
      total += Number(it.cantidad) * (Number(p.precio) || 0);
    }
    countEl.textContent = items;
    totalEl.textContent = formatPrice(total);
    if (items > 0) {
      stickyEl.removeAttribute('hidden');
      stickyEl.classList.add('visible');
    } else {
      stickyEl.setAttribute('hidden', '');
      stickyEl.classList.remove('visible');
    }
  }
  window.MV_updateCartSticky = updateCartSticky;

  // Wrap de badge() existente para sincronizar el sticky también
  var _origBadge = window.badge || function () { if (MV.refreshCartBadge) MV.refreshCartBadge(); };
  window.badge = function () {
    _origBadge();
    updateCartSticky();
  };
})();
})();


// ---- v2: pill sticky "Ir al carrito" + total (autocontenida, fetch propio, EOF) ----
(function () {
  if (document.getElementById('mv-cart-pill')) return;
  var MVv2 = window.MV; if (!MVv2 || !MVv2.api) { console.error('[mv-cart-pill] MV.api no disponible'); return; }
  var st = document.createElement('style'); st.id = 'mv-cart-pill-css';
  st.textContent = '.mv-cart-pill{position:fixed;left:50%;transform:translateX(-50%) translateY(160%);bottom:calc(14px + env(safe-area-inset-bottom,0px));z-index:1045;display:flex;align-items:center;gap:.75rem;background:#065F46;color:#fff;padding:.65rem 1.15rem;border-radius:999px;box-shadow:0 14px 34px rgba(6,95,70,.45);text-decoration:none;font-weight:700;transition:transform .35s cubic-bezier(.2,.8,.2,1),opacity .3s ease;opacity:0;pointer-events:none;max-width:min(480px,calc(100vw - 24px));}' +
    '.mv-cart-pill.visible{transform:translateX(-50%) translateY(0);opacity:1;pointer-events:auto;}' +
    '.mv-cart-pill:hover{color:#fff;}' +
    '.mv-cart-pill .mcp-count{display:inline-flex;align-items:center;justify-content:center;gap:.3rem;min-width:28px;height:28px;padding:0 .5rem;background:#fff;color:#065F46;border-radius:999px;font-size:.9rem;font-weight:800;flex:0 0 auto;}' +
    '.mv-cart-pill .mcp-text{display:flex;flex-direction:column;line-height:1.15;}' +
    '.mv-cart-pill .mcp-label{font-size:.72rem;font-weight:600;opacity:.85;}' +
    '.mv-cart-pill .mcp-total{font-size:1.05rem;font-weight:800;}' +
    '.mv-cart-pill .bi-arrow-right{font-size:1.05rem;flex:0 0 auto;}' +
    '.mv-wa-float{transition:bottom .3s ease;}' +
    'body.mv-cart-pill-on .mv-wa-float{bottom:calc(88px + env(safe-area-inset-bottom,0px));}';
  document.head.appendChild(st);
  var a = document.createElement('a');
  a.id = 'mv-cart-pill'; a.className = 'mv-cart-pill'; a.href = '/carrito/';
  a.setAttribute('aria-label', 'Ir al carrito');
  a.innerHTML = '<span class="mcp-count"><i class="bi bi-cart3"></i><span id="mcp-count">0</span></span>' +
    '<span class="mcp-text"><span class="mcp-label">Ir al carrito</span><span class="mcp-total" id="mcp-total">$0</span></span>' +
    '<i class="bi bi-arrow-right"></i>';
  document.body.appendChild(a);
  var cEl = document.getElementById('mcp-count');
  var tEl = document.getElementById('mcp-total');
  var fmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
  function paint(items, total) {
    cEl.textContent = items;
    tEl.textContent = fmt.format(total);
    var on = items > 0;
    a.classList.toggle('visible', on);
    document.body.classList.toggle('mv-cart-pill-on', on);
    console.log('[mv-cart-pill] items=' + items + ' total=' + total + ' visible=' + on);
  }
  function compute() {
    if (!MVv2.auth || !MVv2.auth.isAuthenticated()) { paint(0, 0); return; }
    MVv2.api.get('/orders/carrito/').then(function (r) {
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      var items = 0, total = 0;
      list.forEach(function (it) {
        items += Number(it.cantidad) || 0;
        total += Number(it.subtotal != null ? it.subtotal : ((Number(it.precio_unitario) || 0) * (Number(it.cantidad) || 0)));
      });
      paint(items, total);
    });
  }
  var orig = MVv2.refreshCartBadge;
  MVv2.refreshCartBadge = function () { if (orig) orig(); compute(); };
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('.mv-q-inc,.mv-q-dec,.btn-add,.btn-add-config')) setTimeout(compute, 350);
  }, true);
  compute();
})();

