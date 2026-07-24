(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) return;
  var api = MV.api;
  var params = new URLSearchParams(location.search);
  var uid = params.get('uid') || '', token = params.get('token') || '';
  var form = document.getElementById('rp-form'), btn = document.getElementById('rp-btn'),
      msg = document.getElementById('rp-msg');
  if (!uid || !token) { msg.className = 'text-center mt-3 mb-0 text-danger'; msg.textContent = 'Enlace inválido. Solicita uno nuevo.'; btn.disabled = true; }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var pw = document.getElementById('rp-pw').value, pw2 = document.getElementById('rp-pw2').value;
    msg.className = 'text-center mt-3 mb-0 text-danger';
    if (pw.length < 8) { msg.textContent = 'Mínimo 8 caracteres.'; return; }
    if (pw !== pw2) { msg.textContent = 'Las contraseñas no coinciden.'; return; }
    btn.disabled = true; btn.textContent = 'Guardando…'; msg.textContent = '';
    api.post('/accounts/password-reset-confirm/', { body: { uid: uid, token: token, new_password: pw } }).then(function (r) {
      btn.disabled = false; btn.textContent = 'Guardar contraseña';
      if (r.ok) { msg.className = 'text-center mt-3 mb-0 text-cta'; msg.innerHTML = 'Contraseña actualizada. <a href="/login/">Inicia sesión</a>.'; }
      else { msg.textContent = (r.data && r.data.error) || 'No se pudo actualizar. El enlace pudo expirar.'; }
    });
  });
})();