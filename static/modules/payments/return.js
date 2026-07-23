/* Óptica Matiz Visión — return.js (Fase 10) */
(function () {
  'use strict';
  var MV = window.MV;
  if (!MV || !MV.api) { console.error('return.js: MV.api no disponible.'); return; }
  var api = MV.api, esc = MV.escape || function (s) { return s; };
  var container = document.getElementById('return-container');
  var dataEl = document.getElementById('return-data');
  var token = dataEl ? (dataEl.getAttribute('data-token') || '') : '';

  function paint(kind, title, msg, links) {
    var icon = kind === 'success' ? '<i class="bi bi-check-circle-fill"></i>' : (kind === 'error' ? '<i class="bi bi-x-circle-fill"></i>' : '<i class="bi bi-exclamation-triangle-fill"></i>');
    var cls = kind === 'success' ? 'success' : 'error';
    var btns = (links || []).map(function (l) { return '<a class="btn ' + (l.primary ? 'btn-cta' : 'btn-outline-mv') + ' mx-1" href="' + l.href + '">' + esc(l.text) + '</a>'; }).join('');
    container.innerHTML = '<div class="mv-result ' + cls + '"><div class="icon">' + icon + '</div><h1>' + esc(title) + '</h1><p class="text-secondary">' + esc(msg) + '</p><div class="mt-3">' + btns + '</div></div>';
  }

  if (!token) {
    paint('error', 'Pago anulado', 'No se recibió el token de la transacción. Es probable que el pago se haya anulado o cerrado la ventana.', [
      { href: '/catalogo/', text: 'Volver al catálogo', primary: true }
    ]);
    return;
  }

  // Confirmar el pago en el backend (idempotente)
  api.post('/payments/webpay/return/', { body: { token_ws: token } }).then(function (r) {
    var st = (r.data && r.data.status) ? String(r.data.status) : '';
    var ordenId = r.data && r.data.orden_id;
    var links = [
      { href: '/catalogo/', text: 'Ir al catálogo', primary: false }
    ];
    if (ordenId) links.unshift({ href: '/carrito/', text: 'Ver mis pedidos', primary: true });

    if (r.ok && st === 'AUTHORIZED') {
      paint('success', '¡Pago exitoso!', 'Tu compra fue confirmada. Gracias por preferir Óptica Matiz Visión.', links);
    } else {
      var msg = (r.data && (r.data.message || r.data.error)) || 'El pago fue rechazado o no pudo completarse.';
      paint('error', 'Pago rechazado', msg, [{ href: '/catalogo/', text: 'Volver al catálogo', primary: true }]);
    }
  }).catch(function () {
    paint('error', 'Error de conexión', 'No pudimos confirmar tu pago. Si el descuento apareció en tu banco, contacta a soporte indicando tu orden.', [
      { href: '/catalogo/', text: 'Volver al catálogo', primary: true }
    ]);
  });
})();