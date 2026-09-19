(function () {
'use strict';
var MV = window.MV; if (!MV || !MV.api) return;
var api = MV.api, toast = MV.toast;
var cache = null, cacheAt = 0;
function orders(){ var now = Date.now(); if (cache && now - cacheAt < 15000) return Promise.resolve(cache); return api.get('/orders/operaciones/').then(function (r){ if (r.ok && Array.isArray(r.data)) { cache = r.data; cacheAt = now; } return cache || []; }); }
function byId(id){ return orders().then(function (list){ return list.filter(function (o){ return String(o.id) === String(id); })[0] || null; }); }
function normWa(tel){ var d = String(tel || '').replace(/\D/g, ''); if (d.length === 9) return '56' + d; if (d.length === 11 && d.slice(0, 2) === '56') return d; if (d.length === 10 && d[0] === '0') return '56' + d.slice(1); return ''; }
function itemsTxt(o){ return (o.items || []).map(function (it){ return (it.producto_nombre || '') + ' x' + (it.cantidad || 1); }).join(', '); }
function openWa(o, extra){ var d = normWa(o.cliente_telefono); if (!d) { toast('El cliente no tiene telefono registrado; avisale por correo.', 'error'); return; } var msg = extra || ('Hola! Te escribimos de Optica Matiz Vision respecto a tu pedido ' + (o.codigo || '') + '. ' + (itemsTxt(o) ? ('Productos: ' + itemsTxt(o) + '. ') : '')); window.open('https://wa.me/' + d + '?text=' + encodeURIComponent(msg), '_blank', 'noopener'); }
function confirmDlg(msg){ return new Promise(function (res){ var ov = document.createElement('div'); ov.style.cssText = 'position:fixed;inset:0;z-index:3000;display:flex;align-items:center;justify-content:center;background:rgba(17,24,39,.55);padding:1rem;'; ov.innerHTML = '<div style="max-width:430px;width:100%;background:#fff;border-radius:16px;padding:1.5rem;box-shadow:0 30px 70px rgba(17,24,39,.4);"><h3 style="margin:0 0 .6rem;font-weight:800;">Confirmar accion</h3><p style="color:#6B7280;margin:0 0 1.1rem;">' + msg + '</p><div style="display:flex;justify-content:flex-end;gap:.6rem;"><button type="button" class="btn btn-outline-mv btn-sm" data-cq-no>Cancelar</button><button type="button" class="btn btn-sm" data-cq-yes style="background:#dc2626;color:#fff;">Si, continuar</button></div></div>'; document.body.appendChild(ov); function done(v){ if (ov.parentNode) ov.parentNode.removeChild(ov); res(v); } ov.querySelector('[data-cq-no]').addEventListener('click', function (){ done(false); }); ov.querySelector('[data-cq-yes]').addEventListener('click', function (){ done(true); }); ov.addEventListener('click', function (e){ if (e.target === ov) done(false); }); }); }
function cancelQuiebre(o){ confirmDlg('¿Cancelar el pedido ' + (o.codigo || '') + ' por QUIEBRE DE STOCK? Se marcara CANCELADA (no repone stock) y deberas reembolsar por Webpay. Al confirmar se abrira WhatsApp para avisar al cliente.').then(function (ok){ if (!ok) return; api.post('/orders/operaciones/' + o.id + '/cancelar-quiebre/', { body: { motivo: 'Quiebre de stock: unidades no disponibles fisicamente.' } }).then(function (r){ if (r.ok) { toast('Pedido cancelado. Abriendo WhatsApp…', 'success'); openWa(o, 'Hola! Te escribimos de Optica Matiz Vision: debimos CANCELAR tu pedido ' + (o.codigo || '') + ' por quiebre de stock de: ' + itemsTxt(o) + '. El reembolso de $' + (o.total || 0) + ' se procesara por Webpay en 3-5 dias habiles. Lamentamos las molestias; puedes responder por este canal.'); setTimeout(function (){ location.reload(); }, 1500); } else { toast((r.data && (r.data.error || r.data.detail)) || 'No se pudo cancelar.', 'error'); } }); }); }
document.addEventListener('click', function (e){
  var el = (e.target && e.target.closest) ? e.target.closest('button[data-wa], button[data-cancela]') : null;
  if (!el) return;
  e.stopPropagation(); e.preventDefault();
  var id = el.getAttribute('data-wa') || el.getAttribute('data-cancela');
  byId(id).then(function (o){
    if (!o) { toast('No se encontro el pedido en la lista.', 'error'); return; }
    if (el.hasAttribute('data-wa')) openWa(o); else cancelQuiebre(o);
  });
}, true);
})();