(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('dashboard.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape, fmtRut = MV.formatRut || function (s) { return s; };
  var root = document.getElementById('dash-root');
  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function todayStr(){ var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
  function norm(s){ return (s || '').toUpperCase().replace(/[.\-\s]/g, ''); }
  function fecha(iso){ if(!iso) return '—'; var s=String(iso); var m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/); if(m){ return new Date(+m[1],+m[2]-1,+m[3]).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); } try{ return new Date(s).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); }catch(e){ return s; } }

  var NEXT = { 'PAGADA': 'EN_PREPARACION', 'EN_PREPARACION': 'LISTO_PARA_RETIRO', 'LISTO_PARA_RETIRO': 'ENTREGADA', 'ENVIADA': 'ENTREGADA' };
  var LABEL = { 'PAGADA': 'Marcar en preparación', 'EN_PREPARACION': 'Listo para retiro', 'LISTO_PARA_RETIRO': 'Marcar entregada', 'ENVIADA': 'Marcar entregada' };
  var STATE_TXT = { 'PAGADA': 'Pagada', 'EN_PREPARACION': 'En preparación', 'LISTO_PARA_RETIRO': 'Listo para retiro', 'ENVIADA': 'Enviada', 'ENTREGADA': 'Entregada', 'DEVUELTA': 'Devuelta' };
  var BASE_TXT = { LEGAL:'Legal', FABRICANTE:'Técnica', CONFORT:'Confort' };
  var RES_LABEL = { devolucion:'Devolución del dinero', cambio:'Cambio directo', reparacion:'Reparación gratuita', rehacer:'Re-hacer (multifocal)' };
  var CONSECUENCIA = {
    devolucion: 'La orden pasará a <strong>Devuelta</strong> y el stock del producto se repone al inventario.',
    cambio: 'No cambia el estado de la orden ni el stock: se registra un <strong>cambio directo</strong>.',
    reparacion: 'No cambia el estado ni el stock: se abre un <strong>caso de reparación</strong>.',
    rehacer: 'No cambia el estado ni el stock: se genera un <strong>trabajo óptico de re-hacer</strong>.'
  };
  var ORD = [], allCitas = [], DEV = [], STOCK_BAJO = [];

  function layout(){
    root.innerHTML =
      '<h1 class="h3 mb-3"><i class="bi bi-clipboard2-pulse"></i>  Panel de operaciones</h1>' +
      '<div class="mv-dash-wrap">' +
        '<aside class="mv-dash-side">' +
          '<button class="mv-side-item active" data-pane="pedidos"><i class="bi bi-box-seam"></i>  Pedidos por Entregar</button>' +
          '<button class="mv-side-item" data-pane="devoluciones"><i class="bi bi-arrow-return-left"></i>  Devoluciones</button>' +
          '<button class="mv-side-item" data-pane="stock"><i class="bi bi-exclamation-triangle"></i>  Stock bajo</button>' +
          '<button class="mv-side-item" data-pane="citas"><i class="bi bi-calendar2-heart"></i>  Citas del Día</button>' +
          '<button class="mv-side-item" data-pane="rut"><i class="bi bi-search"></i>  Buscar por RUT</button>' +
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
      var acc = NEXT[st] ? '<button class="btn btn-cta btn-sm" data-id="' + o.id + '" data-next="' + NEXT[st] + '">' + esc(LABEL[st]) + '</button>' : '<span class="text-muted">—</span>';
      return '<tr><td>' + esc(o.codigo || ('#' + o.id)) + '</td><td>' + esc(o.cliente_email) + '<br><small class="text-muted">' + esc(fmtRut(o.cliente_rut) || '—') + '</small></td><td><span class="mv-badge ' + st + '">' + esc(STATE_TXT[st] || st) + '</span></td><td>' + acc + '</td></tr>';
    }).join('');
    body.innerHTML = '<table class="mv-dash-table"><thead><tr><th>Código</th><th>Cliente / RUT</th><th>Estado</th><th>Acción</th></tr></thead><tbody>' + rows + '</tbody></table>';
  }
  function renderRut(v){ renderPedidos(v); }

  // ---------- Mesa de resolucion de garantias ----------
  function garMini(g, idx){
    var cls = g.vigente ? (g.dias_restantes <= 7 ? 'warn' : 'ok') : 'exp';
    var pct = g.plazo_dias_max > 0 ? Math.max(0, Math.min(100, Math.round(g.dias_restantes / g.plazo_dias_max * 100))) : 0;
    if (!g.vigente) pct = 0;
    return '<div class="mv-res-gar" data-base="' + esc(g.base) + '" style="animation-delay:' + (idx * 0.05) + 's">' +
      '<div class="mv-res-gar-top"><span class="mv-res-gar-name">' + esc(g.nombre) + '</span><span class="mv-res-gar-base ' + esc(g.base) + '">' + esc(BASE_TXT[g.base] || g.base) + '</span></div>' +
      '<div class="mv-res-bar ' + cls + '"><span style="width:' + pct + '%"></span></div>' +
      '<div class="mv-res-gar-meta"><span>' + esc(g.plazo_label || '') + '</span><span>' + (g.vigente ? ('vence ' + esc(fecha(g.vence_en))) : 'vencida') + '</span></div>' +
    '</div>';
  }
  function buildResMap(garantias){
    // Para cada resolucion: esta permitida si alguna garantia VIGENTE la permite.
    // La garantia aplicable = la vigente de mayor prioridad (menor orden) que la permita.
    var vig = (garantias || []).filter(function (g){ return g.vigente; });
    var map = {};
    ['devolucion','cambio','reparacion','rehacer'].forEach(function (r){
      var hit = null;
      for (var i = 0; i < vig.length; i++) {
        if (vig[i]['permite_' + r]) { hit = vig[i]; break; }
      }
      map[r] = hit ? { ok: true, codigo: hit.codigo, nombre: hit.nombre } : { ok: false, codigo: null, nombre: null };
    });
    return map;
  }
  function resChips(map){
    return ['devolucion','cambio','reparacion','rehacer'].map(function (r){
      var m = map[r];
      var dis = m.ok ? '' : ' disabled';
      var title = m.ok ? ('Amparado por: ' + m.nombre) : 'Sin garantía vigente que lo permita';
      return '<button type="button" class="mv-res-chip" data-res="' + r + '"' + dis + ' title="' + esc(title) + '"><i class="bi bi-check2-circle"></i> ' + esc(RES_LABEL[r]) + '</button>';
    }).join('');
  }
  function renderDevoluciones(){
    var body = document.getElementById('dev-body');
    var pend = DEV.filter(function (d){ return d.estado === 'PENDIENTE'; });
    if (!pend.length) { body.innerHTML = '<div class="mv-empty">No hay devoluciones pendientes. 🎉</div>'; return; }
    body.innerHTML = pend.map(function (d){
      return '<div class="mv-dev-card" data-devcard="' + d.id + '">' +
        '<div class="mv-dev-head">' +
          '<div><strong class="mv-dev-code">' + esc(d.orden_codigo || ('#' + d.orden)) + '</strong> · ' + esc(d.cliente_email || '') +
            '<div class="mv-dev-motivo"><i class="bi bi-chat-left-text"></i> ' + esc(d.motivo || '') + '</div></div>' +
          '<div class="mv-dev-actions"><button class="btn btn-cta btn-sm" data-res-toggle="' + d.id + '"><i class="bi bi-shield-check"></i> Resolver con garantía</button>' +
          '<button class="btn btn-outline-mv btn-sm" data-dev-rech="' + d.id + '"><i class="bi bi-x-lg"></i> Rechazar</button></div>' +
        '</div>' +
        '<div class="mv-res-detail" id="res-detail-' + d.id + '" hidden></div>' +
      '</div>';
    }).join('');
  }
  function openResPanel(id){
    var detail = document.getElementById('res-detail-' + id);
    if (!detail) return;
    var d = DEV.filter(function (x){ return String(x.id) === String(id); })[0];
    if (!d) return;
    detail.hidden = false;
    detail.innerHTML = '<div class="mv-res-loading"><span class="spinner-border spinner-border-sm"></span> Cargando marco de garantía…</div>';
    api.get('/orders/garantias-marco/?orden=' + d.orden).then(function (r){
      if (!r.ok || !r.data) { detail.innerHTML = '<div class="mv-res-note err"><i class="bi bi-exclamation-triangle"></i> No se pudo cargar el marco de garantía.</div>'; return; }
      var g = r.data.garantias || [];
      var map = buildResMap(g);
      var algunaVigente = g.some(function (x){ return x.vigente; });
      detail.dataset.res = '';
      detail.dataset.gar = '';
      var fichas = g.length ? g.map(garMini).join('') : '<div class="mv-res-note">Sin políticas cargadas. Ejecuta <code>seed_garantias</code>.</div>';
      detail.innerHTML =
        '<div class="mv-res-kicker"><i class="bi bi-shield-check"></i> Marco de garantía de esta compra</div>' +
        '<div class="mv-res-gar-grid">' + fichas + '</div>' +
        '<div class="mv-res-kicker" style="margin-top:1rem;"><i class="bi bi-hand-index"></i> Resolución a aplicar</div>' +
        '<div class="mv-res-chips">' + resChips(map) + '</div>' +
        '<div class="mv-res-consec" id="res-consec-' + id + '" hidden></div>' +
        '<div class="mv-res-foot">' +
          '<button class="btn btn-cta" data-res-apr="' + id + '" disabled><i class="bi bi-check-lg"></i> Aprobar con esta resolución</button>' +
          '<button class="btn btn-outline-mv btn-sm" data-res-close="' + id + '">Cerrar</button>' +
        '</div>';
      if (!algunaVigente) {
        detail.querySelector('.mv-res-consec').hidden = false;
        detail.querySelector('.mv-res-consec').className = 'mv-res-consec err';
        detail.querySelector('.mv-res-consec').innerHTML = '<i class="bi bi-calendar-x"></i> Ninguna garantía está vigente para esta compra hoy. Solo procede <strong>Rechazar</strong> (o evaluar fuera de garantía).';
      }
    });
  }
  function selectRes(id, res){
    var detail = document.getElementById('res-detail-' + id);
    if (!detail) return;
    detail.dataset.res = res;
    detail.querySelectorAll('.mv-res-chip').forEach(function (c){ c.classList.toggle('active', c.getAttribute('data-res') === res); });
    // garantia aplicable = la primera vigente que permita esta res (mismo criterio que buildResMap)
    var gar = '';
    api.get('/orders/garantias-marco/?orden=' + (DEV.filter(function (x){ return String(x.id) === String(id); })[0] || {}).orden).then(function (r){
      var vig = (r.ok && r.data && r.data.garantias) ? r.data.garantias.filter(function (x){ return x.vigente; }) : [];
      for (var i = 0; i < vig.length; i++) { if (vig[i]['permite_' + res]) { gar = vig[i].codigo; break; } }
      detail.dataset.gar = gar;
      var consec = document.getElementById('res-consec-' + id);
      consec.hidden = false; consec.className = 'mv-res-consec';
      consec.innerHTML = '<i class="bi bi-info-circle"></i> <strong>' + esc(RES_LABEL[res]) + '</strong>' + (gar ? ' bajo <em>' + esc(gar) + '</em>.' : '.') + '<br>' + CONSECUENCIA[res];
      var apr = detail.querySelector('button[data-res-apr]'); if (apr) apr.disabled = false;
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
    var tg = e.target.closest('button[data-res-toggle]');
    if (tg) { openResPanel(tg.getAttribute('data-res-toggle')); return; }
    var cl = e.target.closest('button[data-res-close]');
    if (cl) { var dt = document.getElementById('res-detail-' + cl.getAttribute('data-res-close')); if (dt) dt.hidden = true; return; }
    var ch = e.target.closest('button[data-res]');
    if (ch && !ch.disabled) { var card = ch.closest('.mv-dev-card'); selectRes(card.getAttribute('data-devcard'), ch.getAttribute('data-res')); return; }
    var ap = e.target.closest('button[data-res-apr]');
    if (ap && !ap.disabled) {
      var did = ap.getAttribute('data-res-apr');
      var det = document.getElementById('res-detail-' + did);
      var res = det ? det.dataset.res : '';
      var gar = det ? det.dataset.gar : '';
      if (!res) { toast('Elige una resolución antes de aprobar.', 'error'); return; }
      if (!confirm('¿Aprobar como "' + RES_LABEL[res] + '"? ' + (res === 'devolucion' ? 'El stock se repone y la orden pasa a Devuelta.' : 'Se registra el caso sin mover el estado de la orden.'))) return;
      ap.disabled = true;
      api.post('/orders/devoluciones/' + did + '/aprobar/', { body: { resolucion: res, garantia_aplicada: gar } }).then(function (r){
        if (r.ok) { toast('Resuelto como ' + RES_LABEL[res] + '.', 'success'); loadAll(); }
        else { toast((r.data && r.data.error) || 'No se pudo aprobar.', 'error'); ap.disabled = false; }
      });
      return;
    }
    var dr = e.target.closest('button[data-dev-rech]');
    if (dr) {
      var motivo = (prompt('Motivo del rechazo (opcional):') || '').trim();
      dr.disabled = true;
      api.post('/orders/devoluciones/' + dr.getAttribute('data-dev-rech') + '/rechazar/', { body: { motivo_rechazo: motivo } }).then(function (r){
        if (r.ok) { toast('Devolución rechazada.', 'success'); loadAll(); }
        else { toast((r.data && r.data.error) || 'No se pudo rechazar.', 'error'); dr.disabled = false; }
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