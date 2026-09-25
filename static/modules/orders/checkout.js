/* Óptica Matiz Visión — checkout.js (modalidad: pago completo o abono 50%) */
(function () {
'use strict';
var MV = window.MV;
if (!MV || !MV.api) { console.error('checkout.js: MV.api no disponible.'); return; }
var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape || function (s) { return s; };
var container = document.getElementById('checkout-container');
var fmt = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
function money(n) { return fmt.format(Number(n) || 0); }
var modoPago = 'COMPLETO';
var TOTAL = 0;

function redirectToWebpay(url, token) {
  var form = document.createElement('form');
  form.method = 'POST'; form.action = url;
  var input = document.createElement('input');
  input.type = 'hidden'; input.name = 'token_ws'; input.value = token;
  form.appendChild(input); document.body.appendChild(form); form.submit();
}
function abono() { return Math.round(TOTAL / 2); }
function breakdownHtml() {
  if (modoPago === 'ABONO') {
    return '<div class="mv-summary-item"><div><div class="name">Abono hoy (Webpay)</div><div class="meta">50% del total</div></div><div class="price">' + money(abono()) + '</div></div>' +
           '<div class="mv-summary-item"><div><div class="name">Saldo al retirar en tienda</div><div class="meta">Se cancela al recibir tu compra</div></div><div class="price">' + money(TOTAL - abono()) + '</div></div>';
  }
  return '<div class="mv-summary-item"><div><div class="name">Pagarás ahora con Webpay</div><div class="meta">Pago completo</div></div><div class="price">' + money(TOTAL) + '</div></div>';
}
function payLabel() {
  return modoPago === 'ABONO' ? ('Abonar ' + money(abono()) + ' con Webpay Plus') : ('Pagar ' + money(TOTAL) + ' con Webpay Plus');
}
function render(items, userConsents) {
  userConsents = userConsents || {};
  if (!items.length) {
    container.innerHTML = '<div class="mv-empty"><p>No hay productos para pagar.</p><a class="btn btn-cta" href="/catalogo/">Ir al catálogo</a></div>';
    return;
  }
  TOTAL = items.reduce(function (a, it) { return a + (Number(it.precio_unitario) * Number(it.cantidad)); }, 0);
  var rows = items.map(function (it) {
    return '<div class="mv-summary-item">' +
      '<div><div class="name">' + esc(it.producto_nombre) + '</div><div class="meta">Cantidad: ' + it.cantidad + (it.tipo_lente ? ' · <i class="bi bi-bullseye"></i> ' + esc(it.tipo_lente_display || '') + ' / ' + esc(it.uso_lente_display || '') : '') + '</div></div>' +
      '<div class="price">' + money(it.precio_unitario * it.cantidad) + '</div></div>';
  }).join('');
  var tieneLentes = items.some(function (it) { return !!it.tipo_lente; });

  // Solo solicitamos consentimientos que NO hayan sido otorgados previamente
  var needsTerminos = !userConsents.acepta_terminos;
  var needsSalud = tieneLentes && !userConsents.consiente_salud;

  var consentHtml = '';
  if (needsTerminos || needsSalud) {
    consentHtml =
      '<div class="mv-summary-card p-4 mt-3">' +
        '<div class="mv-summary-eyebrow mb-2"><i class="bi bi-shield-check"></i> Autorizaciones y Privacidad (Ley 21.719)</div>' +
        (needsTerminos ? (
          '<div class="form-check mb-2" style="font-size:.9rem;">' +
            '<input class="form-check-input" type="checkbox" id="chk-terminos" style="cursor:pointer;" />' +
            '<label class="form-check-label text-secondary" for="chk-terminos" style="cursor:pointer;">' +
              'He leído y acepto los <a href="/terminos/" target="_blank" rel="noopener" class="text-decoration-underline text-dark fw-bold">Términos y Condiciones</a> y la <a href="/privacidad/" target="_blank" rel="noopener" class="text-decoration-underline text-dark fw-bold">Política de Privacidad</a>.*' +
            '</label>' +
          '</div>'
        ) : '') +
        (needsSalud ? (
          '<div class="form-check mb-1" style="font-size:.9rem;">' +
            '<input class="form-check-input" type="checkbox" id="chk-salud" style="cursor:pointer;" />' +
            '<label class="form-check-label text-secondary" for="chk-salud" style="cursor:pointer;">' +
              'Autorizo expresamente el tratamiento de mis <strong>datos de salud visual</strong> para la confección personalizada y adaptación óptica de mis lentes (Ley 21.719 y Ley 20.584).*' +
            '</label>' +
          '</div>'
        ) : '') +
      '</div>';
  }

  container.innerHTML =
    '<div class="mv-summary-card p-4">' + rows +
      '<div class="mv-summary-total"><span>Total compra</span><span>' + money(TOTAL) + '</span></div></div>' +
    '<div class="mv-summary-card p-4 mt-3">' +
      '<div class="mv-summary-eyebrow"><i class="bi bi-credit-card"></i> Modalidad de pago</div>' +
      '<label class="mv-pay-opt"><input type="radio" name="modo_pago" value="COMPLETO" checked /><span><strong>Pago completo</strong><small>Pagas todo ahora con Webpay.</small></span></label>' +
      '<label class="mv-pay-opt"><input type="radio" name="modo_pago" value="ABONO" /><span><strong>Abono 50% ahora</strong><small>Pagas la mitad hoy y el saldo al retirar en tienda.</small></span></label>' +
      '<div id="pay-breakdown" class="mt-3">' + breakdownHtml() + '</div></div>' +
    consentHtml +
    '<div class="mv-secure-note my-3"><i class="bi bi-lock-fill"></i> Serás redirigido de forma segura a la pasarela Webpay Plus de Transbank.</div>' +
    '<div id="checkout-error" class="mv-result error" style="display:none;margin:0 0 1rem;padding:1rem;"></div>' +
    '<button id="pay-btn" class="btn btn-cta w-100 btn-lg">' + payLabel() + ' <i class="bi bi-credit-card-2-front-fill"></i></button>' +
    '<div class="text-center mt-2"><a href="/carrito/" class="text-secondary">← Volver al carrito</a></div>';
  Array.prototype.slice.call(container.querySelectorAll('input[name="modo_pago"]')).forEach(function (r) {
    r.addEventListener('change', function () {
      modoPago = r.value;
      document.getElementById('pay-breakdown').innerHTML = breakdownHtml();
      document.getElementById('pay-btn').innerHTML = payLabel() + ' <i class="bi bi-credit-card-2-front-fill"></i>';
    });
  });
  document.getElementById('pay-btn').addEventListener('click', pay);
}
function showError(msg) {
  var el = document.getElementById('checkout-error');
  if (el) { el.style.display = 'block'; el.innerHTML = '<div>' + esc(msg) + '</div>'; }
  toast(msg, 'error');
}
function pay() {
  var chkTerminos = document.getElementById('chk-terminos');
  if (chkTerminos && !chkTerminos.checked) {
    showError('Debes aceptar los Términos y Condiciones y la Política de Privacidad para continuar.');
    return;
  }
  var chkSalud = document.getElementById('chk-salud');
  if (chkSalud && !chkSalud.checked) {
    showError('Debes autorizar el tratamiento de tus datos de salud visual para adquirir lentes personalizados.');
    return;
  }

  var btn = document.getElementById('pay-btn');
  btn.disabled = true; btn.textContent = 'Procesando…';

  var sealPromises = [];
  if (chkTerminos && chkTerminos.checked) {
    sealPromises.push(api.patch('/accounts/consentimientos/', { body: { acepta_terminos: true } }));
  }
  if (chkSalud && chkSalud.checked) {
    sealPromises.push(api.patch('/accounts/consentimientos/', { body: { consiente_salud: true } }));
  }

  Promise.all(sealPromises).then(function () {
    return api.post('/orders/ordenes/', { body: { modo_pago: modoPago } });
  }).then(function (rOrden) {
    if (!rOrden.ok) {
      var m = (rOrden.data && (rOrden.data.error || rOrden.data.detail)) || 'No se pudo crear la orden.';
      showError(m); btn.disabled = false; btn.textContent = payLabel(); return;
    }
    var ordenId = rOrden.data.id;
    btn.textContent = 'Conectando con Transbank…';
    return api.post('/payments/webpay/create/', { body: { orden_id: ordenId } }).then(function (rPago) {
      if (!rPago.ok || !rPago.data || !rPago.data.url || !rPago.data.token) {
        var m = (rPago.data && (rPago.data.error || rPago.data.detail)) || 'No se pudo iniciar el pago en Transbank.';
        showError(m); btn.disabled = false; btn.textContent = payLabel(); return;
      }
      btn.textContent = 'Redirigiendo a Webpay…';
      redirectToWebpay(rPago.data.url, rPago.data.token);
    });
  });
}
function load() {
  Promise.all([
    api.get('/orders/carrito/'),
    api.get('/accounts/consentimientos/')
  ]).then(function (results) {
    var rCart = results[0];
    var rConsent = results[1];
    if (!rCart.ok || !Array.isArray(rCart.data)) {
      container.innerHTML = '<div class="mv-empty">No se pudo cargar el resumen.</div>';
      return;
    }
    var userConsents = (rConsent && rConsent.ok && rConsent.data) ? rConsent.data : {};
    render(rCart.data, userConsents);
  }).catch(function () {
    container.innerHTML = '<div class="mv-empty">Error al cargar el resumen de compra.</div>';
  });
}
if (!auth.isAuthenticated()) { window.location.href = '/login/?next=/checkout/'; return; }
load();
})();