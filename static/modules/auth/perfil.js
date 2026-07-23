(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, toast = MV.toast, esc = MV.escape, fmtRut = MV.formatRut || function (s) { return s; };
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  function fecha(iso){ try { return new Date(iso).toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' }); } catch (e) { return iso || '—'; } }
  function hora(h){ return String(h || '').slice(0, 5); }
  function iniciales(nombre, email){
    var parts = (nombre || '').trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (email || '?').slice(0, 2).toUpperCase();
  }
  function set(id, v){ var e = document.getElementById(id); if (e) e.textContent = v; }
  function val(id){ var e = document.getElementById(id); return e ? e.value : ''; }
  var TXT = { PENDIENTE:'Pendiente', PAGADA:'Pagada', EN_PREPARACION:'En preparación', ENVIADA:'Enviada', ENTREGADA:'Entregada', CANCELADA:'Cancelada', FALLIDA:'Fallida', AGENDADA:'Agendada', CONFIRMADA:'Confirmada', COMPLETADA:'Completada', NO_ASISTIO:'No asistió' };

  /* Activa la pestaña del perfil segun el #hash de la URL (Mis Compras/Citas/Datos) */
  function activateTabFromHash(){
    var map = { '#pedidos': 't-pedidos', '#citas': 't-citas', '#contacto': 't-contacto' };
    var id = map[location.hash] || 't-pedidos';
    var btn = document.getElementById(id);
    if (btn && window.bootstrap && bootstrap.Tab) { new bootstrap.Tab(btn).show(); }
  }

  function loadIdentidad(){
    return Promise.all([api.get('/accounts/me/'), api.get('/accounts/profile/')]).then(function (res) {
      var me = (res[0].ok && res[0].data) ? res[0].data : {};
      var pf = (res[1].ok && res[1].data) ? res[1].data : {};
      var nombre = ((me.first_name || '') + ' ' + (me.last_name || '')).trim();
      set('pf-name', nombre || 'Mi cuenta');
      set('pf-email', me.email || '—');
      set('pf-rut-ro', fmtRut(pf.rut) || '—');
      set('pf-avatar', iniciales(nombre, me.email));
      var tl = document.getElementById('pf-tel'); if (tl) tl.value = pf.telefono || '';
      var dr = document.getElementById('pf-dir'); if (dr) dr.value = pf.direccion || '';
    });
  }
  function loadPedidos(){
    var box = document.getElementById('tab-pedidos');
    api.get('/orders/ordenes/').then(function (r) {
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      set('cnt-pedidos', String(list.length));
      if (!list.length) { box.innerHTML = '<div class="mv-empty"><span class="ico">📦</span>Aún no tienes compras.<br><a class="btn btn-cta btn-sm mt-3" href="/catalogo/">Ir al catálogo</a></div>'; return; }
      box.innerHTML = list.map(function (o) {
        var lineas = (o.items || []).map(function (it) {
          return '<div class="mv-order-line"><span>' + esc(it.producto_nombre) + ' × ' + it.cantidad + '</span><span>' + money(it.subtotal != null ? it.subtotal : (Number(it.precio_unitario) * Number(it.cantidad))) + '</span></div>';
        }).join('');
        return '<div class="mv-order-card">' +
          '<div class="mv-order-head"><div><span class="oid">Orden #' + o.id + '</span> <span class="odate">· ' + fecha(o.creado_en) + '</span></div><span class="mv-badge ' + o.estado + '">' + esc(TXT[o.estado] || o.estado) + '</span></div>' +
          '<div class="mv-order-body">' + (lineas || '<div class="mv-order-line"><span>Sin detalle</span><span></span></div>') +
          '<div class="mv-order-total"><span>Total</span><span>' + money(o.total) + '</span></div></div></div>';
      }).join('');
    });
  }
  function loadCitas(){
    var box = document.getElementById('tab-citas');
    api.get('/appointments/citas/').then(function (r) {
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      set('cnt-citas', String(list.length));
      if (!list.length) { box.innerHTML = '<div class="mv-empty"><span class="ico">🩺</span>No tienes citas agendadas.<br><a class="btn btn-cta btn-sm mt-3" href="/citas/">Agendar una cita</a></div>'; return; }
      box.innerHTML = list.map(function (c) {
        var cancelable = (c.estado === 'AGENDADA' || c.estado === 'CONFIRMADA');
        var acc = cancelable ? '<button class="btn btn-outline-mv btn-sm" data-cancel="' + c.id + '">Cancelar cita</button>' : '';
        return '<div class="mv-cita-row"><div><div class="mv-cita-when">' + fecha(c.bloque_fecha) + ' · ' + hora(c.bloque_hora_inicio) + '</div>' +
          '<div class="mv-cita-meta">' + esc(c.tecnologo_nombre || '') + ' · ' + esc(c.sucursal_nombre || '') + '</div></div>' +
          '<div class="d-flex align-items-center gap-2"><span class="mv-badge ' + c.estado + '">' + esc(TXT[c.estado] || c.estado) + '</span>' + acc + '</div></div>';
      }).join('');
    });
  }
  document.getElementById('tab-citas').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-cancel]'); if (!b) return;
    if (!confirm('¿Cancelar esta cita? El bloque volverá a quedar disponible.')) return;
    var id = b.getAttribute('data-cancel'); b.disabled = true;
    api.post('/appointments/citas/' + id + '/cancelar/').then(function (r) {
      if (r.ok) { toast('Cita cancelada.', 'success'); loadCitas(); }
      else { toast((r.data && r.data.error) || 'No se pudo cancelar.', 'error'); b.disabled = false; }
    });
  });
  var form = document.getElementById('pf-form');
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    var body = { telefono: val('pf-tel'), direccion: val('pf-dir') };
    var btn = document.getElementById('pf-save');
    if (btn) { btn.disabled = true; btn.textContent = 'Guardando…'; }
    api.put('/accounts/profile/', { body: body }).then(function (r) {
      if (btn) { btn.disabled = false; btn.textContent = 'Guardar cambios'; }
      if (r.ok) toast('Datos de contacto actualizados.', 'success');
      else toast('No se pudo guardar. Revisa los datos.', 'error');
    });
  });
  MV.me().then(function (u) {
    if (!u) { window.location.replace('/login/?next=/perfil/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { window.location.replace('/panel/'); return; }
    loadIdentidad(); loadPedidos(); loadCitas();
    activateTabFromHash();
    window.addEventListener('hashchange', activateTabFromHash);
  });
})();