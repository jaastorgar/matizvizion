(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, esc = MV.escape;
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  function fecha(iso){ try { return new Date(iso).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' }); } catch (e) { return iso || '—'; } }
  var TXT = { PAGADA:'Pagada', EN_PREPARACION:'En preparación', LISTO_PARA_RETIRO:'Listo para retiro', ENVIADA:'Enviada', ENTREGADA:'Entregada' };
  function card(o){
    var lines = (o.items || []).map(function (it){
      return '<div class="mv-track-line"><span>' + esc(it.producto_nombre) + ' <span class="mv-track-sku">' + esc(it.producto_sku || '') + '</span> × ' + it.cantidad + '</span><span>' + money(it.subtotal != null ? it.subtotal : (Number(it.precio_unitario) * Number(it.cantidad))) + '</span></div>';
    }).join('');
    return '<div class="mv-track-card">' +
      '<div class="mv-track-head"><div><span class="mv-track-code">' + esc(o.codigo || ('#' + o.id)) + '</span> <span class="mv-track-date">· ' + fecha(o.creado_en) + '</span></div><span class="mv-badge ' + o.estado + '">' + esc(TXT[o.estado] || o.estado) + '</span></div>' +
      '<div class="mv-track-body">' + lines +
        '<div class="mv-track-total"><span>Total</span><span>' + money(o.total) + '</span></div>' +
        '<div class="text-end mt-2"><a class="btn btn-outline-mv btn-sm" href="/seguimiento/?orden=' + encodeURIComponent(o.codigo || '') + '"><i class="bi bi-geo-alt"></i> Ver seguimiento</a></div>' +
      '</div></div>';
  }
  MV.me().then(function (u){
    if (!u) { location.replace('/login/?next=/mis-compras/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/panel/'); return; }
    var box = document.getElementById('mc-list');
    api.get('/orders/ordenes/').then(function (r){
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      if (!list.length) { box.innerHTML = '<div class="mv-empty"><span class="ico"><i class="bi bi-bag"></i></span>Aún no tienes compras.<br><a class="btn btn-cta btn-sm mt-3" href="/catalogo/">Ir al catálogo</a></div>'; return; }
      box.innerHTML = list.map(card).join('');
    });
  });
})();