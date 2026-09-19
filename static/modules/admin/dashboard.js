(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('dashboard.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape, fmtRut = MV.formatRut || function (s) { return s; };
  var root = document.getElementById('dash-root');
  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function todayStr(){ var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
  function norm(s){ return (s || '').toUpperCase().replace(/[.-\s]/g, ''); }
  function fecha(iso){ if(!iso) return '—'; var s=String(iso).slice(0,10); var m=s.split('-'); if(m.length===3){ return new Date(+m[0],+m[1]-1,+m[2]).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); } return s; }
  var NEXT = { 'PAGADA': 'EN_PREPARACION', 'EN_PREPARACION': 'LISTO_PARA_RETIRO', 'LISTO_PARA_RETIRO': 'ENTREGADA', 'ENVIADA': 'ENTREGADA' };
  var LABEL = { 'PAGADA': 'Marcar en preparación', 'EN_PREPARACION': 'Listo para retiro', 'LISTO_PARA_RETIRO': 'Marcar entregada', 'ENVIADA': 'Marcar entregada' };
  var STATE_TXT = { 'PAGADA': 'Pagada', 'EN_PREPARACION': 'En preparación', 'LISTO_PARA_RETIRO': 'Listo para retiro', 'ENVIADA': 'Enviada', 'ENTREGADA': 'Entregada', 'DEVUELTA': 'Devuelta' };
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
var BASE_TXT = { LEGAL:'Legal', FABRICANTE:'Técnica', CONFORT:'Confort' };
  var RES_LABEL = { devolucion:'Devolución del dinero', cambio:'Cambio directo', reparacion:'Reparación gratuita', rehacer:'Re-hacer (multifocal)' };
  var ORD = [], allCitas = [], DEV = [], STOCK_BAJO = [];

  // Estilos de los modales propios (confirm / prompt) - se inyectan una vez
  (function(){
    if (document.getElementById('mv-dlg-css')) return;
    var s = document.createElement('style'); s.id = 'mv-dlg-css';
    s.textContent = '.mv-dlg-ov{position:fixed;inset:0;z-index:2100;display:flex;align-items:center;justify-content:center;background:rgba(17,24,39,.55);backdrop-filter:blur(3px);padding:1rem;}' +
      '.mv-dlg-card{width:100%;max-width:460px;background:var(--white);border-radius:16px;padding:1.5rem 1.6rem;box-shadow:0 30px 70px rgba(17,24,39,.4);}' +
      '.mv-dlg-card h3{font-family:var(--font-head);font-weight:800;color:var(--lead-dark);margin:0 0 .6rem;font-size:1.1rem;}' +
      '.mv-dlg-card p{color:var(--lead-muted,#6B7280);font-size:.92rem;margin:0 0 1.1rem;line-height:1.5;}' +
      '.mv-dlg-card textarea{width:100%;border:1px solid var(--border-color);border-radius:10px;padding:.6rem .7rem;font-family:inherit;font-size:.92rem;box-sizing:border-box;}' +
      '.mv-dlg-card textarea:focus{outline:none;border-color:var(--green-primary);box-shadow:0 0 0 3px rgba(16,185,129,.16);}' +
      '.mv-dlg-foot{display:flex;justify-content:flex-end;gap:.6rem;}';
    document.head.appendChild(s);
  })();

  // Confirmacion propia (reemplaza confirm())
  function confirmBox(message, okLabel) {
    return new Promise(function (resolve) {
      var ov = document.createElement('div'); ov.className = 'mv-dlg-ov';
      ov.innerHTML = '<div class="mv-dlg-card"><h3>Confirmar acción</h3><p>' + message + '</p>' +
        '<div class="mv-dlg-foot"><button class="btn btn-outline-mv btn-sm" id="dlg-no">Cancelar</button>' +
        '<button class="btn btn-cta" id="dlg-yes">' + (okLabel || 'Sí, continuar') + '</button></div></div>';
      document.body.appendChild(ov);
      function done(v){ if (ov.parentNode) ov.parentNode.removeChild(ov); resolve(v); }
      ov.querySelector('#dlg-no').addEventListener('click', function(){ done(false); });
      ov.querySelector('#dlg-yes').addEventListener('click', function(){ done(true); });
      ov.addEventListener('click', function(e){ if (e.target === ov) done(false); });
    });
  }
  // Prompt propio (reemplaza prompt()) -> resuelve el texto o null si cancela
  function promptBox(title, placeholder) {
    return new Promise(function (resolve) {
      var ov = document.createElement('div'); ov.className = 'mv-dlg-ov';
      ov.innerHTML = '<div class="mv-dlg-card"><h3>' + title + '</h3>' +
        '<textarea id="dlg-val" rows="3" placeholder="' + (placeholder || '') + '"></textarea>' +
        '<div class="mv-dlg-foot" style="margin-top:1rem;"><button class="btn btn-outline-mv btn-sm" id="dlg-no">Cancelar</button>' +
        '<button class="btn btn-cta" id="dlg-yes">Aceptar</button></div></div>';
      document.body.appendChild(ov);
      function done(ok, val){ if (ov.parentNode) ov.parentNode.removeChild(ov); resolve(ok ? val : null); }
      ov.querySelector('#dlg-no').addEventListener('click', function(){ done(false); });
      ov.querySelector('#dlg-yes').addEventListener('click', function(){ done(true, ov.querySelector('#dlg-val').value.trim()); });
      ov.addEventListener('click', function(e){ if (e.target === ov) done(false); });
    });
  }
  function consecuencia(res, garNombre) {
    var g = garNombre ? (' bajo <em>' + esc(garNombre) + '</em>') : '';
    if (res === 'devolucion') return '<strong>Devolución del dinero</strong>' + g + '. La orden pasará a <strong>Devuelta</strong> y el stock del producto se repone al inventario.';
    if (res === 'cambio') return '<strong>Cambio directo</strong>' + g + '. No cambia el estado de la orden ni el stock; se registra el cambio.';
    if (res === 'reparacion') return '<strong>Reparación gratuita</strong>' + g + '. No cambia el estado ni el stock; se abre un caso de reparación.';
    return '<strong>Re-hacer (multifocal)</strong>' + g + '. No cambia el estado ni el stock; se genera un trabajo óptico.';
  }

  function layout(){
    root.innerHTML =
      '<h1 class="h3 mb-3"><i class="bi bi-clipboard2-pulse"></i> Panel de operaciones</h1>' +
      '<div class="mv-dash-wrap">' +
        '<aside class="mv-dash-side">' +
          '<button class="mv-side-item active" data-pane="pedidos"><i class="bi bi-box-seam"></i> Pedidos por Entregar</button>' +
          '<button class="mv-side-item" data-pane="devoluciones"><i class="bi bi-arrow-return-left"></i> Devoluciones</button>' +
          '<button class="mv-side-item" data-pane="stock"><i class="bi bi-exclamation-triangle"></i> Stock bajo</button>' +
          '<button class="mv-side-item" data-pane="citas"><i class="bi bi-calendar2-heart"></i> Citas del Día</button>' +
          '<button class="mv-side-item" data-pane="rut"><i class="bi bi-search"></i> Buscar por RUT</button>' +
        '</aside>' +
        '<section>' +
          '<div class="mv-dash-panel" id="pane-pedidos"><h2 class="h5 mb-3">Gestión de entregas</h2><div id="pedidos-body"></div></div>' +
          '<div class="mv-dash-panel d-none" id="pane-devoluciones"><h2 class="h5 mb-3">Mesa de resolución de garantías</h2><p class="text-secondary small mb-3">Abre cada caso para ver el marco de garantía aplicable y elegir la resolución. Solo <em>Devolución</em> mueve el estado de la orden y repone stock; cambio, reparación y re-hacer registran el caso.</p><div id="dev-body"></div></div>' +
          '<div class="mv-dash-panel d-none" id="pane-stock"><h2 class="h5 mb-3">Productos con stock bajo o agotados</h2><div id="stock-body"></div></div>' +
          '<div class="mv-dash-panel d-none" id="pane-citas"><h2 class="h5 mb-3">Citas del día</h2><div id="citas-body"></div></div>' +
          '<div class="mv-dash-panel d-none" id="pane-rut"><h2 class="h5 mb-3">Buscar cliente por RUT</h2><input type="text" class="form-control mb-3" id="rut-input" placeholder="Ej: 11.111.111-1" /><div id="rut-body"></div></div>' +
        '</section>' +
      '</div>';
    root.querySelectorAll('.mv-side-item').forEach(function (b){
      b.addEventListener('click', function (){
        root.querySelectorAll('.mv-side-item').forEach(function (x){ x.classList.remove('active'); });
        b.classList.add('active');
        ['pedidos','devoluciones','stock','citas','rut'].forEach(function (p){ document.getElementById('pane-' + p).classList.toggle('d-none', p !== b.getAttribute('data-pane')); });
        if (b.getAttribute('data-pane') === 'rut') { var ri = document.getElementById('rut-input'); if (ri) ri.focus(); renderRut(''); }
      });
    });
    var ri = document.getElementById('rut-input'); if (ri) ri.addEventListener('input', function (){ renderRut(ri.value); });
  }

  function renderPedidos(filterRut){
    var body = document.getElementById('pedidos-body');
    var fr = norm(filterRut);
    var list = ORD.filter(function (o){ return !fr || norm(o.cliente_rut).indexOf(fr) !== -1 || norm(o.cliente_email).indexOf(fr) !== -1; });
    if (!list.length) { body.innerHTML = '<div class="mv-empty">No hay pedidos para mostrar.</div>'; return; }
    var rows = list.map(function (o){
      var st = o.estado;
      var saldoBtn = (o.modo_pago === 'ABONO' && !o.saldo_cancelado && Number(o.saldo_pendiente) > 0) ? '<button class="btn btn-outline-mv btn-sm me-1" data-saldo="' + o.id + '"><i class="bi bi-cash-coin"></i> Saldo ' + money(o.saldo_pendiente) + '</button>' : '';
    var nextDis = (o.modo_pago === 'ABONO' && !o.saldo_cancelado && st === 'LISTO_PARA_RETIRO') ? ' disabled title="Registra el pago del saldo primero"' : '';
    var acc = saldoBtn + (NEXT[st] ? '<button class="btn btn-cta btn-sm" data-id="' + o.id + '" data-next="' + NEXT[st] + '"' + nextDis + '>' + esc(LABEL[st]) + '</button>' : '<span class="text-muted">—</span>');
      return '<tr><td>' + esc(o.codigo || ('#' + o.id)) + '</td><td>' + esc(o.cliente_email) + '<br><small class="text-muted">' + esc(fmtRut(o.cliente_rut) || '—') + '</small></td><td><span class="mv-badge ' + st + '">' + esc(STATE_TXT[st] || st) + '</span></td><td>' + acc + '</td></tr>';
    }).join('');
    body.innerHTML = '<table class="mv-dash-table"><thead><tr><th>Código</th><th>Cliente / RUT</th><th>Estado</th><th>Acción</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }
  function renderRut(v){ renderPedidos(v); }

  function renderDevoluciones(){
    var body = document.getElementById('dev-body');
    var pend = DEV.filter(function (d){ return d.estado === 'PENDIENTE'; });
    if (!pend.length) { body.innerHTML = '<div class="mv-empty">No hay devoluciones pendientes.</div>'; return; }
    body.innerHTML = pend.map(function (d){
      return '<div class="mv-dev-card" data-devcard="' + d.id + '">' +
        '<div class="mv-dev-head"><div><strong>' + esc(d.orden_codigo || ('#' + d.orden)) + '</strong> · ' + esc(d.cliente_email || '') +
        '<div class="mv-dev-motivo"><i class="bi bi-chat-left-text"></i> ' + esc(d.motivo || '') + '</div>' +
        '<div class="mv-dev-motivo"><i class="bi bi-box-seam"></i> ' + (d.items_detalle || []).map(function (it){ var q = (it.cantidad_devuelta != null ? it.cantidad_devuelta : it.cantidad); return esc(it.nombre) + ' ×' + q + (q !== it.cantidad ? ' de ' + it.cantidad : ''); }).join(', ') + '</div></div>' +
        '<div class="mv-dev-actions"><button class="btn btn-cta btn-sm" data-dev-open="' + d.id + '"><i class="bi bi-shield-check"></i> Resolver con garantía</button>' +
        '<button class="btn btn-outline-mv btn-sm" data-dev-rech="' + d.id + '"><i class="bi bi-x-lg"></i> Rechazar</button></div></div>' +
        '<div class="mv-res-detail" id="res-detail-' + d.id + '" hidden></div></div>';
    }).join('');
  }

  function openResPanel(id){
    var detail = document.getElementById('res-detail-' + id); if (!detail) return;
    var d = DEV.filter(function (x){ return String(x.id) === String(id); })[0]; if (!d) return;
    detail.hidden = false;
    detail.innerHTML = '<div class="mv-res-loading">Cargando marco de garantía…</div>';
    api.get('/orders/garantias-marco/?orden=' + d.orden).then(function (r){
      if (!r.ok || !r.data) { detail.innerHTML = '<div class="mv-res-note err">No se pudo cargar el marco de garantía.</div>'; return; }
      var g = r.data.garantias || [];
      var vig = g.filter(function (x){ return x.vigente; });
      var map = {};
      ['devolucion','cambio','reparacion','rehacer'].forEach(function (res){
        var hit = null;
        for (var i = 0; i < vig.length; i++) { if (vig[i]['permite_' + res]) { hit = vig[i]; break; } }
        map[res] = hit;
      });
      detail.dataset.res = ''; detail.dataset.gar = '';
      detail._map = map;
      var fichas = g.length ? g.map(function (x){
        var cls = x.vigente ? (x.dias_restantes <= 7 ? 'warn' : 'ok') : 'exp';
        var pct = x.plazo_dias_max > 0 ? Math.max(0, Math.min(100, Math.round(x.dias_restantes / x.plazo_dias_max * 100))) : 0;
        if (!x.vigente) pct = 0;
        return '<div class="mv-res-gar" data-base="' + esc(x.base) + '">' +
          '<div class="mv-res-gar-top"><span class="mv-res-gar-name">' + esc(x.nombre) + '</span><span class="mv-res-gar-base ' + esc(x.base) + '">' + esc(BASE_TXT[x.base] || x.base) + '</span></div>' +
          '<div class="mv-res-bar ' + cls + '"><span style="width:' + pct + '%"></span></div>' +
          '<div class="mv-res-gar-meta"><span>' + esc(x.plazo_label || '') + '</span><span>' + (x.vigente ? ('vence ' + esc(fecha(x.vence_en))) : 'vencida') + '</span></div></div>';
      }).join('') : '<div class="mv-res-note">Sin políticas cargadas. Ejecuta <code>seed_garantias</code>.</div>';
      var chips = ['devolucion','cambio','reparacion','rehacer'].map(function (res){
        var ok = !!map[res];
        return '<button type="button" class="mv-res-chip" data-res="' + res + '"' + (ok ? '' : ' disabled') + ' title="' + (ok ? ('Amparado por: ' + esc(map[res].nombre)) : 'Sin garantía vigente que lo permita') + '"><i class="bi bi-check2-circle"></i> ' + esc(RES_LABEL[res]) + '</button>';
      }).join('');
      detail.innerHTML =
        '<div class="mv-res-kicker"><i class="bi bi-shield-check"></i> Marco de garantía de esta compra</div>' +
        '<div class="mv-res-gar-grid">' + fichas + '</div>' +
        '<div class="mv-res-kicker" style="margin-top:1rem;"><i class="bi bi-hand-index"></i> Resolución a aplicar</div>' +
        '<div class="mv-res-chips">' + chips + '</div>' +
        '<div class="mv-res-consec" id="res-consec-' + id + '" hidden></div>' +
        '<div class="mv-res-foot"><button class="btn btn-cta" data-res-apr="' + id + '" disabled><i class="bi bi-check-lg"></i> Aprobar con esta resolución</button>' +
        '<button class="btn btn-outline-mv btn-sm" data-res-close="' + id + '">Cerrar</button></div>';
      if (!vig.length) {
        var c = detail.querySelector('.mv-res-consec'); c.hidden = false; c.className = 'mv-res-consec err';
        c.innerHTML = '<i class="bi bi-calendar-x"></i> Ninguna garantía está vigente para esta compra hoy. Solo procede <strong>Rechazar</strong> (o evaluar fuera de garantía).';
      }
    });
  }

  function renderStock(){
    var body = document.getElementById('stock-body');
    if (!STOCK_BAJO.length) { body.innerHTML = '<div class="mv-empty">No hay productos con stock bajo. ¡Buen trabajo!</div>'; return; }
    var rows = STOCK_BAJO.map(function (p){
      var tag = p.stock <= 0 ? '<span class="mv-badge CANCELADA">AGOTADO</span>' : '<span class="mv-badge EN_PREPARACION">BAJO</span>';
      return '<tr><td>' + esc(p.nombre) + '</td><td>' + esc(p.sku || '—') + '</td><td>' + p.stock + '</td><td>' + (p.stock_minimo != null ? p.stock_minimo : '—') + '</td><td>' + tag + '</td></tr>';
    }).join('');
    body.innerHTML = '<table class="mv-dash-table"><thead><tr><th>Producto</th><th>SKU</th><th>Stock</th><th>Mínimo</th><th>Estado</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }
  function renderCitas(){
    var body = document.getElementById('citas-body');
    var hoy = todayStr();
    var list = allCitas.filter(function (c){ return c.bloque_fecha === hoy; });
    if (!list.length) { body.innerHTML = '<div class="mv-empty">No hay citas para hoy.</div>'; return; }
    body.innerHTML = list.map(function (c){
      var st = c.estado;
      var acc = '';
      if (st === 'AGENDADA' || st === 'CONFIRMADA') {
        acc = '<div class="mv-cita-actions">' +
          '<button class="ok" data-cita="' + c.id + '" data-cstate="COMPLETADA">✓ Asistió</button>' +
          '<button class="no" data-cita="' + c.id + '" data-cstate="NO_ASISTIO">✗ No asistió</button>' +
          '<button class="cancel" data-cita="' + c.id + '" data-cstate="CANCELADA">Cancelar</button>' +
        '</div>';
      }
      return '<div class="mv-cita-row"><div><strong>' + esc(c.cliente_email) + '</strong><br><small class="text-muted">' + esc(c.tecnologo_nombre) + ' · ' + esc(c.sucursal_nombre) + '</small>' + acc + '</div><div class="text-end"><div>' + esc(String(c.bloque_hora_inicio).slice(0,5)) + '</div><span class="mv-badge ' + st + '">' + esc(st) + '</span></div></div>';
    }).join('');
  }

  root.addEventListener('click', function (e){
    var b = e.target.closest('button[data-next]');
    if (b) {
      var id = b.getAttribute('data-id'), next = b.getAttribute('data-next');
      b.disabled = true;
      api.patch('/orders/operaciones/' + id + '/actualizar-entrega/', { body: { estado: next } }).then(function (r){
        if (r.ok) { toast('Estado actualizado.', 'success'); loadAll(); }
        else { toast((r.data && r.data.error) || 'No se pudo actualizar.', 'error'); b.disabled = false; }
      });
      return;
    }
    var sb = e.target.closest('button[data-saldo]');
    if (sb) {
      var sid = sb.getAttribute('data-saldo');
      confirmBox('¿Confirmas que el cliente canceló el saldo restante en tienda? Esto habilita marcar la orden como entregada.', 'Confirmar saldo').then(function (ok) {
        if (!ok) return;
        sb.disabled = true;
        api.post('/orders/operaciones/' + sid + '/confirmar-saldo/', {}).then(function (r) {
          if (r.ok) { toast('Saldo registrado como cancelado.', 'success'); loadAll(); }
          else { toast((r.data && r.data.error) || 'No se pudo confirmar el saldo.', 'error'); sb.disabled = false; }
        });
      });
      return;
    }
    var c = e.target.closest('button[data-cita]');
    if (c) {
      var cid = c.getAttribute('data-cita'), cst = c.getAttribute('data-cstate');
      c.disabled = true;
      api.patch('/appointments/citas/' + cid + '/marcar/', { body: { estado: cst } }).then(function (r){
        if (r.ok) { toast('Cita actualizada.', 'success'); loadAll(); }
        else { toast((r.data && r.data.error) || 'No se pudo actualizar la cita.', 'error'); c.disabled = false; }
      });
      return;
    }
    var op = e.target.closest('button[data-dev-open]');
    if (op) { openResPanel(op.getAttribute('data-dev-open')); return; }
    var cl = e.target.closest('button[data-res-close]');
    if (cl) { var dt = document.getElementById('res-detail-' + cl.getAttribute('data-res-close')); if (dt) dt.hidden = true; return; }
    var ch = e.target.closest('.mv-res-chip');
    if (ch && !ch.disabled) {
      var card = ch.closest('.mv-dev-card'); var cid2 = card.getAttribute('data-devcard');
      var detail = document.getElementById('res-detail-' + cid2);
      detail.querySelectorAll('.mv-res-chip').forEach(function (x){ x.classList.toggle('active', x === ch); });
      var res = ch.getAttribute('data-res');
      var hit = detail._map ? detail._map[res] : null;
      detail.dataset.res = res;
      detail.dataset.gar = hit ? hit.codigo : '';
      var c2 = document.getElementById('res-consec-' + cid2);
      c2.hidden = false; c2.className = 'mv-res-consec';
      c2.innerHTML = '<i class="bi bi-info-circle"></i> ' + consecuencia(res, hit ? hit.nombre : '');
      var apr = detail.querySelector('[data-res-apr]'); if (apr) apr.disabled = false;
      return;
    }
    var ap = e.target.closest('[data-res-apr]');
    if (ap && !ap.disabled) {
      var id2 = ap.getAttribute('data-res-apr');
      var det = document.getElementById('res-detail-' + id2);
      var res2 = det.dataset.res, gar = det.dataset.gar;
      if (!res2) { toast('Elige una resolución antes de aprobar.', 'error'); return; }
      confirmBox('¿Aprobar como "' + RES_LABEL[res2] + '"? ' + (res2 === 'devolucion' ? 'El stock se repone y la orden pasa a Devuelta.' : 'Se registra el caso sin mover el estado de la orden.'), 'Aprobar').then(function (ok){
        if (!ok) return;
        ap.disabled = true;
        api.post('/orders/devoluciones/' + id2 + '/aprobar/', { body: { resolucion: res2, garantia_aplicada: gar } }).then(function (r){
          if (r.ok) { toast('Resuelto como ' + RES_LABEL[res2] + '.', 'success'); loadAll(); }
          else { toast((r.data && r.data.error) || 'No se pudo aprobar.', 'error'); ap.disabled = false; }
        });
      });
      return;
    }
    var dr = e.target.closest('button[data-dev-rech]');
    if (dr) {
      promptBox('Motivo del rechazo', 'Motivo (opcional)').then(function (motivo){
        if (motivo === null) return;
        dr.disabled = true;
        api.post('/orders/devoluciones/' + dr.getAttribute('data-dev-rech') + '/rechazar/', { body: { motivo_rechazo: motivo } }).then(function (r){
          if (r.ok) { toast('Devolución rechazada.', 'success'); loadAll(); }
          else { toast((r.data && r.data.error) || 'No se pudo rechazar.', 'error'); dr.disabled = false; }
        });
      });
    }
  });

  function loadAll(){
    Promise.all([
      api.get('/orders/operaciones/'),
      api.get('/appointments/citas/'),
      api.get('/orders/devoluciones/'),
      api.get('/store/productos/')
    ]).then(function (res){
      ORD = (res[0].ok && Array.isArray(res[0].data)) ? res[0].data : [];
      allCitas = (res[1].ok && Array.isArray(res[1].data)) ? res[1].data : [];
      DEV = (res[2].ok && Array.isArray(res[2].data)) ? res[2].data : [];
      var productos = (res[3].ok && Array.isArray(res[3].data)) ? res[3].data : [];
      STOCK_BAJO = productos.filter(function (p){ return p.stock_bajo === true; }).sort(function (a, b){ return a.stock - b.stock; });
      renderPedidos(''); renderCitas(); renderDevoluciones(); renderStock();
    });
  }

  if (!auth.isAuthenticated()) { window.location.href = '/login/?next=/panel/'; return; }
  api.get('/accounts/me/').then(function (r){
    if (!r.ok || !r.data || (r.data.role !== 'VENDEDOR' && r.data.role !== 'ADMIN')) {
      root.innerHTML = '<div class="mv-empty">⛔ Acceso denegado. Este panel es solo para vendedores y administradores.</div>';
      return;
    }
    layout(); loadAll();
  });
})();