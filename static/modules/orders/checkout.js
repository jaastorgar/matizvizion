/* Óptica Matiz Visión — checkout.js (Fase 10) */
(function () {
  'use strict';
  var MV = window.MV;
  if (!MV || !MV.api) { console.error('checkout.js: MV.api no disponible.'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape || function (s) { return s; };
  var container = document.getElementById('checkout-container');
  var fmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
  function money(n) { return fmt.format(Number(n) || 0); }

  function redirectToWebpay(url, token) {
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    var input = document.createElement('input');
    input.type = 'hidden'; input.name = 'token_ws'; input.value = token;
    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
  }

  function render(items) {
    if (!items.length) {
      container.innerHTML = '<div class="mv-empty"><p>No hay productos para pagar.</p><a class="btn btn-cta" href="/catalogo/">Ir al catálogo</a></div>';
      return;
    }
    var total = items.reduce(function (a, it) { return a + (Number(it.precio_unitario) * Number(it.cantidad)); }, 0);
    var rows = items.map(function (it) {
      return '<div class="mv-summary-item">' +
        '<div><div class="name">' + esc(it.producto_nombre) + '</div><div class="meta">Cantidad: ' + it.cantidad + '</div></div>' +
        '<div class="price">' + money(it.precio_unitario * it.cantidad) + '</div>' +
      '</div>';
    }).join('');

    container.innerHTML =
      '<div class="mv-summary-card p-4">' + rows +
        '<div class="mv-summary-total"><span>Total a pagar</span><span>' + money(total) + '</span></div>' +
      '</div>' +
      '<div class="mv-secure-note my-3">🔒 Serás redirigido de forma segura a la pasarela Webpay Plus de Transbank para completar la transacción.</div>' +
      '<div id="checkout-error" class="mv-result error" style="display:none;margin:0 0 1rem;padding:1rem;"></div>' +
      '<button id="pay-btn" class="btn btn-cta w-100 btn-lg">Pagar con Webpay Plus 💳</button>' +
      '<div class="text-center mt-2"><a href="/carrito/" class="text-secondary">← Volver al carrito</a></div>';

    document.getElementById('pay-btn').addEventListener('click', pay);
  }

  function showError(msg) {
    var el = document.getElementById('checkout-error');
    if (el) { el.style.display = 'block'; el.innerHTML = '<div>' + esc(msg) + '</div>'; }
    toast(msg, 'error');
  }

  function pay() {
    var btn = document.getElementById('pay-btn');
    btn.disabled = true; btn.textContent = 'Creando orden…';

    // 1) Crear la orden desde el carrito
    api.post('/orders/ordenes/', { body: {} }).then(function (rOrden) {
      if (!rOrden.ok) {
        var m = (rOrden.data && (rOrden.data.error || rOrden.data.detail)) || 'No se pudo crear la orden.';
        showError(m); btn.disabled = false; btn.textContent = 'Pagar con Webpay Plus 💳';
        return;
      }
      var ordenId = rOrden.data.id;
      btn.textContent = 'Conectando con Transbank…';

      // 2) Crear la transacción Webpay
      return api.post('/payments/webpay/create/', { body: { orden_id: ordenId } }).then(function (rPago) {
        if (!rPago.ok || !rPago.data || !rPago.data.url || !rPago.data.token) {
          var m = (rPago.data && (rPago.data.error || rPago.data.detail)) || 'No se pudo iniciar el pago en Transbank.';
          showError(m); btn.disabled = false; btn.textContent = 'Pagar con Webpay Plus 💳';
          return;
        }
        // 3) POST automático a la pasarela (formulario oculto)
        btn.textContent = 'Redirigiendo a Webpay…';
        redirectToWebpay(rPago.data.url, rPago.data.token);
      });
    });
  }

  function load() {
    api.get('/orders/carrito/').then(function (r) {
      if (!r.ok || !Array.isArray(r.data)) { container.innerHTML = '<div class="mv-empty">No se pudo cargar el resumen.</div>'; return; }
      render(r.data);
    });
  }

  if (!auth.isAuthenticated()) { window.location.href = '/login/?next=/checkout/'; return; }
  load();
})();