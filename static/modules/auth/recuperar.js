(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) return;
  var api = MV.api;
  var form = document.getElementById('rec-form'), btn = document.getElementById('rec-btn'),
      msg = document.getElementById('rec-msg'), inp = document.getElementById('rec-email');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var email = (inp.value || '').trim();
    if (!email) { msg.className = 'text-center mt-3 mb-0 text-danger'; msg.textContent = 'Escribe tu correo.'; return; }
    btn.disabled = true; btn.textContent = 'Enviando…'; msg.textContent = '';
    api.post('/accounts/password-reset/', { body: { email: email } }).then(function (r) {
      btn.disabled = false; btn.textContent = 'Enviar enlace';
      msg.className = 'text-center mt-3 mb-0 text-cta';
      msg.textContent = 'Si ese correo existe, te enviamos un enlace. Revisa tu bandeja (en desarrollo, mira la terminal del servidor).';
    });
  });
})();