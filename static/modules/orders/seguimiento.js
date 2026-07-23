(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, esc = MV.escape;
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  function fecha(iso){ try { return new Date(iso).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' }); } catch (e) { return iso || '—'; } }
  var LABEL = { PENDIENTE:'Pedido creado', PAGADA:'Pagado', EN_PREPARACION:'En preparación', LISTO_PARA_RETIRO:'Listo para retiro', ENVIADA:'Enviado', ENTREGADA:'Entregado' };
  var TXT = { PENDIENTE:'Pendiente', PAGADA:'Pagada', EN_PREPARACION:'En preparación', LISTO_PARA_RETIRO:'Listo para retiro', ENVIADA:'Enviada', ENTREGADA:'Entregada', CANCELADA:'Cancelada', FALLIDA:'Fallida' };
  var RETIRO = ['PENDIENTE','PAGADA','EN_PREPARACION','LISTO_PARA_RETIRO','ENTREGADA'];
  var DESPACHO = ['PENDIENTE','PAGADA','EN_PREPARACION','ENVIADA','ENTREGADA'];
  function pickSeq(o){ var h = (o.historial || []).map(function (x){ return x.estado_nuevo; }); if (o.estado === 'ENVIADA' || h.indexOf('ENVIADA') !== -1) return DESPACHO; return RETIRO; }
  function timelineHtml(o){
    var seq = pickSeq(o), cur = seq.indexOf(o.estado);
    if (cur < 0) return '';
    return '<ol class="mv-timeline">' + seq.map(function (s, i){
      var cls = i < cur ? 'done' : (i === cur ? 'done current' : '');
      var num = i < cur ? '<i class="bi bi-check-lg"></i>' : (i + 1);
      return '<li class="mv-tl-step ' + cls + '"><span class="mv-tl-dot">' + num + '</span><span class="mv-tl-label">' + esc(LABEL[s] || s) + '</span></li>';
    }).join('') + '</ol>';
  }
  function orderCard(o){
    var st = o.estado;
    var banner = '';
    if (st === 'CANCELADA') banner = '<div class="mv-track-banner cancel">Este pedido fue cancelado.</div>';
    else if (st === 'FALLIDA') banner = '<div class="mv-track-banner fail">El pago de este pedido no pudo completarse.</div>';
    var tl = (st === 'CANCELADA' || st === 'FALLIDA') ? '' : timelineHtml(o);
    var lines = (o.items || []).map(function (it){
      return '<div class="mv-track-line"><span>' + esc(it.producto_nombre) + ' <span class="mv-track-sku">' + esc(it.producto_sku || '') + '</span> × ' + it.cantidad + '</span><span>' + money(it.subtotal != null ? it.subtotal : (Number(it.precio_unitario) * Number(it.cantidad))) + '</span></div>';
    }).join('');
    return '<div class="mv-track-card">' +
      '<div class="mv-track-head"><div><span class="mv-track-code">' + esc(o.codigo || ('#' + o.id)) + '</span> <span class="mv-track-date">· ' + fecha(o.creado_en) + '</span></div><span class="mv-badge ' + st + '">' + esc(TXT[st] || st) + '</span></div>' +
      '<div class="mv-track-body">' + banner + tl + lines + '<div class="mv-track-total"><span>Total</span><span>' + money(o.total) + '</span></div></div>' +
    '</div>';
  }
  MV.me().then(function (u){
    if (!u) { location.replace('/login/?next=/seguimiento/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/panel/'); return; }
    var box = document.getElementById('seg-list');
    var ordenParam = (new URLSearchParams(location.search).get('orden') || '').trim().toUpperCase();
    api.get('/orders/ordenes/').then(function (r){
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      if (ordenParam) list = list.filter(function (o){ return (o.codigo || '').toUpperCase() === ordenParam; });
      if (!list.length) {
        var msg = ordenParam ? 'No encontramos ese pedido entre tus compras.' : 'Aún no tienes compras.';
        box.innerHTML = '<div class="mv-empty"><span class="ico"><i class="bi bi-box-seam"></i></span>' + msg + '<br><a class="btn btn-cta btn-sm mt-3" href="/catalogo/">Ir al catálogo</a></div>';
        return;
      }
      box.innerHTML = list.map(orderCard).join('');
    });
  });
})();