(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('dashboard.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape, fmtRut = MV.formatRut || function (s) { return s; };
  var root = document.getElementById('dash-root');
  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function todayStr(){ var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
  function norm(s){ return (s || '').toUpperCase().replace(/[.\-\s]/g, ''); }
  var NEXT = { 'PAGADA': 'EN_PREPARACION', 'EN_PREPARACION': 'ENVIADA', 'ENVIADA': 'ENTREGADA' };
  var LABEL = { 'PAGADA': 'Marcar en preparación', 'EN_PREPARACION': 'Marcar enviada', 'ENVIADA': 'Marcar entregada' };
  var STATE_TXT = { 'PAGADA': 'Pagada', 'EN_PREPARACION': 'En preparación', 'ENVIADA': 'Enviada' };
  var ORD = [], allCitas = [];

  function layout(){
    root.innerHTML =
      '<h1 class="h3 mb-3">📋 Panel de operaciones</h1>' +
      '<div class="mv-dash-wrap">' +
        '<aside class="mv-dash-side">' +
          '<button class="mv-side-item active" data-pane="pedidos">📦 Pedidos por Entregar</button>' +
          '<button class="mv-side-item" data-pane="citas">🩺 Citas del Día</button>' +
          '<button class="mv-side-item" data-pane="rut">🔍 Buscar por RUT</button>' +
        '</aside>' +
        '<section>' +
          '<div class="mv-dash-panel" id="pane-pedidos"><h2 class="h5 mb-3">Gestión de entregas</h2><div id="pedidos-body"></div></div>' +
          '<div class="mv-dash-panel d-none" id="pane-citas"><h2 class="h5 mb-3">Citas del día</h2><div id="citas-body"></div></div>' +
          '<div class="mv-dash-panel d-none" id="pane-rut"><h2 class="h5 mb-3">Buscar cliente por RUT</h2><input type="text" class="form-control mb-3" id="rut-input" placeholder="Ej: 11.111.111-1" /><div id="rut-body"></div></div>' +
        '</section>' +
      '</div>';
    root.querySelectorAll('.mv-side-item').forEach(function (b){
      b.addEventListener('click', function (){
        root.querySelectorAll('.mv-side-item').forEach(function (x){ x.classList.remove('active'); });
        b.classList.add('active');
        ['pedidos','citas','rut'].forEach(function (p){ document.getElementById('pane-' + p).classList.toggle('d-none', p !== b.getAttribute('data-pane')); });
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
      var acc = NEXT[st] ? '<button class="btn btn-cta btn-sm" data-id="' + o.id + '" data-next="' + NEXT[st] + '">' + esc(LABEL[st]) + '</button>' : '<span class="text-muted">—</span>';
      return '<tr><td>#' + o.id + '</td><td>' + esc(o.cliente_email) + '<br><small class="text-muted">' + esc(fmtRut(o.cliente_rut) || '—') + '</small></td><td><span class="mv-badge ' + st + '">' + esc(STATE_TXT[st] || st) + '</span></td><td>' + acc + '</td></tr>';
    }).join('');
    body.innerHTML = '<table class="mv-dash-table"><thead><tr><th>Orden</th><th>Cliente / RUT</th><th>Estado</th><th>Acción</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }
  function renderRut(v){ renderPedidos(v); }
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
    var c = e.target.closest('button[data-cita]');
    if (c) {
      var cid = c.getAttribute('data-cita'), cst = c.getAttribute('data-cstate');
      c.disabled = true;
      api.patch('/appointments/citas/' + cid + '/marcar/', { body: { estado: cst } }).then(function (r){
        if (r.ok) { toast('Cita actualizada.', 'success'); loadAll(); }
        else { toast((r.data && r.data.error) || 'No se pudo actualizar la cita.', 'error'); c.disabled = false; }
      });
    }
  });
  function loadAll(){
    Promise.all([api.get('/orders/operaciones/'), api.get('/appointments/citas/')]).then(function (res){
      ORD = (res[0].ok && Array.isArray(res[0].data)) ? res[0].data : [];
      allCitas = (res[1].ok && Array.isArray(res[1].data)) ? res[1].data : [];
      renderPedidos(''); renderCitas();
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