(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) return;
  var api = MV.api, esc = MV.escape || function (s){ return s; };
  // Doble seguro: si el link llego con &amp; (escape HTML del mail), lo reparamos
  var rawSearch = (location.search || '').replace(/&amp;/g, '&');
  var params = new URLSearchParams(rawSearch);
  var uid = params.get('uid') || '', token = params.get('token') || '';
  var form = document.getElementById('rp-form'), btn = document.getElementById('rp-btn'), msg = document.getElementById('rp-msg');

  function resendLink() {
    return '<a href="/recuperar/" class="btn btn-cta btn-sm mt-2"><i class="bi bi-envelope"></i> Solicitar un enlace nuevo</a>';
  }
  function fail(extra) {
    msg.className = 'text-center mt-3 mb-0 text-danger';
    msg.innerHTML = (extra ? (esc(extra) + '<br>') : '') +
      'Este enlace no es válido o ya expiró.<br>' +
      '<span class="small">Nota: también caduca si iniciaste sesión después de pedirlo.</span><br>' + resendLink();
    if (btn) btn.disabled = true;
  }

  if (!uid || !token) { fail(''); return; }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var pw = document.getElementById('rp-pw').value, pw2 = document.getElementById('rp-pw2').value;
    msg.className = 'text-center mt-3 mb-0 text-danger';
    if (pw.length < 8) { msg.textContent = 'Mínimo 8 caracteres.'; return; }
    if (pw !== pw2) { msg.textContent = 'Las contraseñas no coinciden.'; return; }
    btn.disabled = true; btn.textContent = 'Guardando…'; msg.textContent = '';
    api.post('/accounts/password-reset-confirm/', { body: { uid: uid, token: token, new_password: pw } }).then(function (r) {
      btn.textContent = 'Guardar contraseña';
      if (r.ok) {
        msg.className = 'text-center mt-3 mb-0 text-cta';
        msg.innerHTML = 'Contraseña actualizada. <a href="/login/" class="btn btn-cta btn-sm mt-2">Iniciar sesión</a>';
      } else {
        btn.disabled = false;
        fail((r.data && r.data.error) || '');
      }
    });
  });
})();