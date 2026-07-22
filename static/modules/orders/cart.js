/* Óptica Matiz Visión — cart.js (Fase 10) */
(function () {
  'use strict';
  var MV = window.MV;
  if (!MV || !MV.api) { console.error('cart.js: MV.api no disponible.'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape || function (s) { return s; };
  var container = document.getElementById('cart-container');
  var fmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
  function money(n) { return fmt.format(Number(n) || 0); }

  function render(items) {
    if (!items.length) {
      container.innerHTML = '<div class="mv-empty"><p>Tu carrito está vacío.</p><a class="btn btn-cta" href="/catalogo/">Ir al catálogo</a></div>';
      return;
    }
    var total = items.reduce(function (a, it) { return a + (Number(it.precio_unitario) * Number(it.cantidad)); }, 0);
    var rows = items.map(function (it) {
      return '<div class="mv-summary-item" data-id="' + it.id + '">' +
        '<div>' +
          '<div class="name">' + esc(it.producto_nombre) + '</div>' +
          '<div class="meta">' + money(it.precio_unitario) + ' c/u</div>' +
          '<div class="mv-qty mt-1">' +
            '<button type="button" data-act="dec">−</button>' +
            '<span>' + it.cantidad + '</span>' +
            '<button type="button" data-act="inc">+</button>' +
          '</div>' +
        '</div>' +
        '<div class="text-end">' +
          '<div class="price">' + money(it.precio_unitario * it.cantidad) + '</div>' +
          '<button type="button" class="mv-link-danger" data-act="del">Eliminar</button>' +
        '</div>' +
      '</div>';
    }).join('');

    container.innerHTML =
      '<div class="mv-summary-card p-4">' + rows +
        '<div class="mv-summary-total"><span>Total</span><span>' + money(total) + '</span></div>' +
      '</div>' +
      '<div class="d-flex justify-content-between mt-3">' +
        '<a href="/catalogo/" class="btn btn-outline-mv">← Seguir comprando</a>' +
        '<a href="/checkout/" class="btn btn-cta px-4">Ir a pagar →</a>' +
      '</div>';
  }

  function load() {
    api.get('/orders/carrito/').then(function (r) {
      if (!r.ok || !Array.isArray(r.data)) { container.innerHTML = '<div class="mv-empty">No se pudo cargar el carrito.</div>'; return; }
      render(r.data);
      if (MV.refreshCartBadge) MV.refreshCartBadge();
    });
  }

  container.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-act]');
    if (!btn) return;
    var row = e.target.closest('.mv-summary-item');
    var id = row.getAttribute('data-id');
    var act = btn.getAttribute('data-act');
    var qtySpan = row.querySelector('.mv-qty span');
    var qty = Number(qtySpan.textContent);

    if (act === 'inc') {
      api.patch('/orders/carrito/' + id + '/', { body: { cantidad: qty + 1 } }).then(function (r) { if (r.ok) load(); else toast('No se pudo actualizar.', 'error'); });
    } else if (act === 'dec') {
      if (qty <= 1) { api.delete('/orders/carrito/' + id + '/').then(function (r) { if (r.ok) load(); }); }
      else { api.patch('/orders/carrito/' + id + '/', { body: { cantidad: qty - 1 } }).then(function (r) { if (r.ok) load(); else toast('No se pudo actualizar.', 'error'); }); }
    } else if (act === 'del') {
      api.delete('/orders/carrito/' + id + '/').then(function (r) { if (r.ok) { toast('Producto eliminado.', 'success'); load(); } });
    }
  });

  if (!auth.isAuthenticated()) { window.location.href = '/login/?next=/carrito/'; return; }
  load();
})();