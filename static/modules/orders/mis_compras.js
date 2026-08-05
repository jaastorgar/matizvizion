(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, toast = MV.toast, esc = MV.escape;
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  function fecha(iso){ if(!iso) return '—'; var s=String(iso); var m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/); if(m){ return new Date(+m[1],+m[2]-1,+m[3]).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); } try{ return new Date(s).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); }catch(e){ return s; } }
  var TXT = { PAGADA:'Pagada', EN_PREPARACION:'En preparación', LISTO_PARA_RETIRO:'Listo para retiro', ENVIADA:'Enviada', ENTREGADA:'Entregada', DEVUELTA:'Devuelta' };
  var BASE_TXT = { LEGAL:'Legal', FABRICANTE:'Técnica', CONFORT:'Confort' };
  var RES_TXT = { devolucion:'Devolución', cambio:'Cambio', reparacion:'Reparación', rehacer:'Re-hacer' };
  var ESTADO_PILL = { PENDIENTE:{c:'pend', t:'En revisión'}, APROBADA:{c:'ok', t:'Aprobada'}, RECHAZADA:{c:'no', t:'Rechazada'} };

  // ---------- Fichas de garantia ----------
  function garCard(g, idx){
    var cls = g.vigente ? (g.dias_restantes <= 7 ? 'warn' : 'ok') : 'exp';
    var pct = g.plazo_dias_max > 0 ? Math.max(0, Math.min(100, Math.round(g.dias_restantes / g.plazo_dias_max * 100))) : 0;
    if (!g.vigente) pct = 0;
    var st = g.vigente ? (g.dias_restantes <= 7 ? 'Por vencer' : 'Vigente') : 'Vencida';
    var cov = '';
    if (g.permite_devolucion) cov += '<li><i class="bi bi-check-circle-fill"></i> Devolución del dinero</li>';
    if (g.permite_cambio)     cov += '<li><i class="bi bi-check-circle-fill"></i> Cambio directo</li>';
    if (g.permite_reparacion) cov += '<li><i class="bi bi-check-circle-fill"></i> Reparación gratuita</li>';
    if (g.permite_rehacer)    cov += '<li><i class="bi bi-check-circle-fill"></i> Re-hacer (multifocal)</li>';
    return '<div class="mv-gar-card" data-base="' + esc(g.base) + '" style="animation-delay:' + (idx * 0.06) + 's">' +
      '<div class="mv-gar-top"><div class="mv-gar-name">' + esc(g.nombre) + '</div><span class="mv-gar-base ' + esc(g.base) + '">' + esc(BASE_TXT[g.base] || g.base) + '</span></div>' +
      '<div class="mv-gar-status ' + cls + '"><span class="dot"></span>' + st + ' · ' + esc(g.plazo_label || '') + '</div>' +
      '<div class="mv-gar-bar ' + cls + '"><span style="width:' + pct + '%"></span></div>' +
      '<div class="mv-gar-meta"><span>Vence ' + esc(fecha(g.vence_en)) + '</span><span>' + (g.vigente ? ('quedan <strong>' + g.dias_restantes + ' días</strong>') : 'plazo cumplido') + '</span></div>' +
      (cov ? '<ul class="mv-gar-cov">' + cov + '</ul>' : '') +
    '</div>';
  }
  function garantiasHtml(info){
    if (info.pendiente_entrega) return '<div class="mv-gar-wrap"><div class="mv-gar-kicker"><i class="bi bi-shield-check"></i> Garantías</div><div class="mv-gar-note"><i class="bi bi-truck"></i> Tus garantías comienzan a correr el día que recibas este pedido.</div></div>';
    if (!info.garantias || !info.garantias.length) return '';
    return '<div class="mv-gar-wrap"><div class="mv-gar-kicker"><i class="bi bi-shield-check"></i> Certificado de garantía de esta compra</div><div class="mv-gar-grid">' + info.garantias.map(garCard).join('') + '</div></div>';
  }

  // ---------- Estado de devoluciones bajo el total ----------
  function devPills(sols){
    if (!sols || !sols.length) return '';
    var pills = sols.map(function (s){
      var e = ESTADO_PILL[s.estado] || {c:'pend', t:s.estado};
      var res = (s.estado === 'APROBADA' && s.resolucion) ? (' · ' + (RES_TXT[s.resolucion] || s.resolucion)) : '';
      var prods = (s.items_detalle || []).map(function (it){ return esc(it.nombre); }).join(', ');
      return '<span class="mv-dev-pill ' + e.c + '" title="' + esc(prods) + '"><i class="bi bi-arrow-return-left"></i> ' + esc(e.t) + res + '</span>';
    }).join('');
    var detalle = sols.map(function (s){
      var prods = (s.items_detalle || []).map(function (it){ return esc(it.nombre) + ' ×' + it.cantidad; }).join(' · ');
      return prods ? '<div class="mv-dev-pill-detail">' + prods + '</div>' : '';
    }).join('');
    return '<div class="mv-dev-status"><div class="mv-dev-status-kicker"><i class="bi bi-clipboard2-check"></i> Devoluciones de esta compra</div><div class="mv-dev-pills">' + pills + '</div>' + detalle + '</div>';
  }

  // ---------- Tarjeta de compra ----------
  function card(o, gmap, devByOrden){
    var lines = (o.items || []).map(function (it){
      return '<div class="mv-track-line"><span>' + esc(it.producto_nombre) + ' <span class="mv-track-sku">' + esc(it.producto_sku || '') + '</span> × ' + it.cantidad + '</span><span>' + money(it.subtotal != null ? it.subtotal : (Number(it.precio_unitario) * Number(it.cantidad))) + '</span></div>';
    }).join('');
    var puedeDev = (o.estado === 'ENTREGADA' || o.estado === 'ENVIADA');
    var devBtn = puedeDev ? '<button class="btn btn-outline-mv btn-sm ms-2" data-dev="' + o.id + '"><i class="bi bi-arrow-return-left"></i> Devolución por garantía</button>' : '';
    var gar = garantiasHtml(gmap[o.codigo] || { garantias: [], pendiente_entrega: false });
    var devs = devPills(devByOrden[o.id] || []);
    return '<div class="mv-track-card" data-orden="' + o.id + '">' +
      '<div class="mv-track-head"><div><span class="mv-track-code">' + esc(o.codigo || ('#' + o.id)) + '</span> <span class="mv-track-date">· ' + fecha(o.creado_en) + '</span></div><span class="mv-badge ' + o.estado + '">' + esc(TXT[o.estado] || o.estado) + '</span></div>' +
      '<div class="mv-track-body">' + lines +
        '<div class="mv-track-total"><span>Total</span><span>' + money(o.total) + '</span></div>' + gar + devs +
        '<div class="text-end mt-2"><a class="btn btn-outline-mv btn-sm" href="/seguimiento/?orden=' + encodeURIComponent(o.codigo || '') + '"><i class="bi bi-geo-alt"></i> Ver seguimiento</a>' + devBtn + '</div>' +
      '</div></div>';
  }

  // ---------- Modal de devolucion con selector de productos ----------
  function openDevModal(orden, blocked){
    var ov = document.createElement('div'); ov.className = 'mv-modal-ov';
    var items = (orden.items || []);
    var rows = items.map(function (it, i){
      var sku = (it.producto_sku || '').toUpperCase();
      var b = blocked[sku];
      var dis = b ? ' disabled' : '';
      var tag = b ? '<span class="mv-dev-item-tag ' + (b.cls) + '">' + esc(b.label) + '</span>' : '';
      return '<label class="mv-dev-item' + (b ? ' locked' : '') + '" style="animation-delay:' + (i * 0.05) + 's" data-sku="' + esc(sku) + '">' +
        '<span class="mv-dev-check"><i class="bi bi-check-lg"></i></span>' +
        '<input type="checkbox" class="mv-dev-cb" value="' + esc(sku) + '"' + dis + ' />' +
        '<span class="mv-dev-item-info"><span class="mv-dev-item-name">' + esc(it.producto_nombre) + '</span>' +
        '<span class="mv-dev-item-meta">' + esc(sku || '—') + ' · ×' + it.cantidad + ' · ' + money(it.subtotal != null ? it.subtotal : (Number(it.precio_unitario) * Number(it.cantidad))) + '</span></span>' +
        tag +
      '</label>';
    }).join('');
    ov.innerHTML =
      '<div class="mv-modal-card" role="dialog" aria-modal="true">' +
        '<button type="button" class="mv-modal-x" aria-label="Cerrar"><i class="bi bi-x-lg"></i></button>' +
        '<span class="mv-modal-eyebrow">Devolución por garantía</span>' +
        '<h2 class="mv-modal-title">Pedido ' + esc(orden.codigo || ('#' + orden.id)) + '</h2>' +
        '<p class="mv-modal-sub">Selecciona el o los productos que deseas devolver y cuéntanos el motivo. Tienes hasta 6 meses desde la entrega para ejercer tu garantía legal.</p>' +
        '<div class="mv-modal-label">¿Qué producto(s) deseas devolver?</div>' +
        '<div class="mv-dev-list">' + rows + '</div>' +
        '<div class="mv-modal-label" style="margin-top:1.1rem;">Motivo de la devolución</div>' +
        '<textarea class="mv-dev-motivo" rows="3" placeholder="Ej: el armazón presenta decoloración en la bisagra izquierda…"></textarea>' +
        '<div class="mv-dev-hint"><i class="bi bi-shield-check"></i> Revisaremos tu caso según la garantía aplicable (legal, técnica o de adaptación) y te avisaremos la resolución.</div>' +
        '<div class="mv-modal-foot">' +
          '<button type="button" class="mv-modal-cancel">Cancelar</button>' +
          '<button type="button" class="mv-modal-submit" disabled><i class="bi bi-send"></i> Enviar solicitud</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(ov);
    requestAnimationFrame(function () { ov.classList.add('in'); });

    var card = ov.querySelector('.mv-modal-card');
    var cbs = Array.prototype.slice.call(ov.querySelectorAll('.mv-dev-cb'));
    var motivo = ov.querySelector('.mv-dev-motivo');
    var submit = ov.querySelector('.mv-modal-submit');
    function refresh(){
      cbs.forEach(function (cb){ cb.closest('.mv-dev-item').classList.toggle('active', cb.checked); });
      var any = cbs.some(function (cb){ return cb.checked; });
      submit.disabled = !(any && motivo.value.trim().length >= 3);
    }
    cbs.forEach(function (cb){ cb.addEventListener('change', refresh); });
    motivo.addEventListener('input', refresh);
    function close(){ ov.classList.remove('in'); setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 200); }
    ov.querySelector('.mv-modal-x').addEventListener('click', close);
    ov.querySelector('.mv-modal-cancel').addEventListener('click', close);
    ov.addEventListener('click', function (e){ if (e.target === ov) close(); });
    submit.addEventListener('click', function (){
      var sel = cbs.filter(function (cb){ return cb.checked; }).map(function (cb){ return cb.value; });
      var mot = motivo.value.trim();
      if (!sel.length || mot.length < 3) { card.classList.add('shake'); setTimeout(function(){ card.classList.remove('shake'); }, 420); return; }
      submit.disabled = true; submit.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando…';
      api.post('/orders/devoluciones/', { body: { orden: orden.id, motivo: mot, items: sel } }).then(function (r){
        if (r.ok) { toast('Solicitud enviada con ' + sel.length + ' producto(s). Te avisaremos la resolución.', 'success'); close(); bootstrap(); }
        else { submit.disabled = false; submit.innerHTML = '<i class="bi bi-send"></i> Enviar solicitud'; toast((r.data && (r.data.error || r.data.non_field_errors)) || 'No se pudo enviar la solicitud.', 'error'); }
      });
    });
    refresh();
  }

  function wireDevolucion(ordenesMap, blockedByOrden){
    document.getElementById('mc-list').addEventListener('click', function (e){
      var b = e.target.closest('button[data-dev]'); if (!b) return;
      var id = b.getAttribute('data-dev');
      openDevModal(ordenesMap[id], blockedByOrden[id] || {});
    });
  }

  function render(list, gmap, devByOrden, blockedByOrden, ordenesMap){
    var box = document.getElementById('mc-list');
    if (!list.length) { box.innerHTML = '<div class="mv-empty"><span class="ico"><i class="bi bi-bag"></i></span>Aún no tienes compras.<br><a class="btn btn-cta btn-sm mt-3" href="/catalogo/">Ir al catálogo</a></div>'; return; }
    box.innerHTML = list.map(function (o){ return card(o, gmap, devByOrden); }).join('');
    wireDevolucion(ordenesMap, blockedByOrden);
  }

  function bootstrap(){
    Promise.all([api.get('/orders/ordenes/'), api.get('/orders/garantias/'), api.get('/orders/devoluciones/')]).then(function (res){
      var list = (res[0].ok && Array.isArray(res[0].data)) ? res[0].data : [];
      var garr = (res[1].ok && Array.isArray(res[1].data)) ? res[1].data : [];
      var devs = (res[2].ok && Array.isArray(res[2].data)) ? res[2].data : [];
      var gmap = {}; garr.forEach(function (g){ gmap[g.codigo] = g; });
      var devByOrden = {}, blockedByOrden = {}, ordenesMap = {};
      list.forEach(function (o){ ordenesMap[o.id] = o; });
      devs.forEach(function (s){
        (devByOrden[s.orden] = devByOrden[s.orden] || []).push(s);
        if (s.estado === 'PENDIENTE' || s.estado === 'APROBADA') {
          var blk = (blockedByOrden[s.orden] = blockedByOrden[s.orden] || {});
          var meta = s.estado === 'PENDIENTE' ? {cls:'pend', label:'En revisión'} : {cls:'ok', label:'Devuelto'};
          (s.items_detalle || []).forEach(function (it){ blk[(it.sku || '').toUpperCase()] = meta; });
        }
      });
      render(list, gmap, devByOrden, blockedByOrden, ordenesMap);
    });
  }

  MV.me().then(function (u){
    if (!u) { location.replace('/login/?next=/mis-compras/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/inicio/'); return; }
    bootstrap();
  });
})();