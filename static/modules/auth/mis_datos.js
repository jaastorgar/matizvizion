(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, toast = MV.toast, fmtRut = MV.formatRut || function (s){ return s; };
  function set(id, v){ var e = document.getElementById(id); if (e) e.textContent = v; }
  function val(id){ var e = document.getElementById(id); return e ? e.value : ''; }
  function iniciales(nombre, email){
    var parts = (nombre || '').trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (email || '?').slice(0, 2).toUpperCase();
  }
  MV.me().then(function (u){
    if (!u) { location.replace('/login/?next=/mis-datos/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/panel/'); return; }
    var nombre = ((u.first_name || '') + ' ' + (u.last_name || '')).trim();
    set('pf-name', nombre || 'Mi cuenta');
    set('pf-email', u.email || '—');
    set('pf-avatar', iniciales(nombre, u.email));
    api.get('/accounts/profile/').then(function (r){
      var pf = (r.ok && r.data) ? r.data : {};
      set('pf-rut-ro', fmtRut(pf.rut) || '—');
      var tl = document.getElementById('pf-tel'); if (tl) tl.value = pf.telefono || '';
      var dr = document.getElementById('pf-dir'); if (dr) dr.value = pf.direccion || '';
    });
  });
  var form = document.getElementById('pf-form');
  if (form) form.addEventListener('submit', function (e){
    e.preventDefault();
    var body = { telefono: val('pf-tel'), direccion: val('pf-dir') };
    var btn = document.getElementById('pf-save');
    if (btn) { btn.disabled = true; btn.textContent = 'Guardando…'; }
    api.put('/accounts/profile/', { body: body }).then(function (r){
      if (btn) { btn.disabled = false; btn.textContent = 'Guardar cambios'; }
      if (r.ok) toast('Datos de contacto actualizados.', 'success');
      else toast('No se pudo guardar. Revisa los datos.', 'error');
    });
  });
})();