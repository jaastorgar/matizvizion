/* =========================================================
   Óptica Matiz Visión — auth.js (Fase 08)
   Login + Registro contra la API DRF. Guarda JWT con MV.auth.
   ========================================================= */
(function () {
  'use strict';

  const api = window.MV && window.MV.api;
  const auth = window.MV && window.MV.auth;
  const toast = window.MV && window.MV.toast;

  if (!api || !auth) {
    console.error('auth.js: window.MV.api / window.MV.auth no disponibles. Revisa utils.js.');
    return;
  }

  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  /* ---------- Helpers de UI ---------- */
  function clearErrors(form) {
    form.querySelectorAll('.mv-field-error').forEach(el => { el.textContent = ''; });
    const general = form.parentElement.querySelector('.mv-form-error');
    if (general) general.textContent = '';
  }

  function setFieldError(form, field, message) {
    const el = form.querySelector(`[data-error-for="${field}"]`);
    if (el) el.textContent = message;
  }

  function setGeneralError(form, message) {
    const el = form.parentElement.querySelector('.mv-form-error');
    if (el) el.textContent = message;
  }

  function setLoading(button, loading, labelBusy) {
    if (!button) return;
    button.disabled = loading;
    if (loading) {
      button.dataset.label = button.dataset.label || button.textContent;
      button.textContent = labelBusy || 'Procesando...';
      button.classList.add('is-loading');
    } else {
      button.textContent = button.dataset.label || button.textContent;
      button.classList.remove('is-loading');
    }
  }

  // Muestra errores devueltos por DRF: {campo: ["msg"], non_field_errors: [...], detail: "..."}
  function showServerErrors(form, data) {
    if (!data || typeof data !== 'object') {
      setGeneralError(form, 'Error inesperado del servidor.');
      return;
    }
    if (data.detail) {
      setGeneralError(form, data.detail);
      return;
    }
    let shown = false;
    Object.keys(data).forEach(key => {
      const msgs = Array.isArray(data[key]) ? data[key].join(' ') : String(data[key]);
      if (key === 'non_field_errors') {
        setGeneralError(form, msgs);
      } else if (form.querySelector(`[data-error-for="${key}"]`)) {
        setFieldError(form, key, msgs);
      } else {
        setGeneralError(form, msgs);
      }
      shown = true;
    });
    if (!shown) setGeneralError(form, 'No se pudo completar la operación.');
  }

  // Redirección segura: solo rutas internas (evita open redirect)
  function safeNext() {
    const params = new URLSearchParams(window.location.search);
    const next = params.get('next');
    return next && next.startsWith('/') ? next : '/';
  }

  /* ---------- LOGIN ---------- */
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors(loginForm);

      const email = document.getElementById('login-email').value.trim();
      const password = document.getElementById('login-password').value;
      const submitBtn = document.getElementById('login-submit');

      // Validación cliente
      let ok = true;
      if (!EMAIL_RE.test(email)) { setFieldError(loginForm, 'email', 'Ingresa un correo válido.'); ok = false; }
      if (!password) { setFieldError(loginForm, 'password', 'Ingresa tu contraseña.'); ok = false; }
      if (!ok) return;

      setLoading(submitBtn, true, 'Ingresando...');
      const r = await api.post('/auth/login/', { body: { email, password } });
      setLoading(submitBtn, false);

      if (!r.ok) {
        showServerErrors(loginForm, r.data);
        return;
      }

      auth.setTokens(r.data.access, r.data.refresh);
      toast('Sesión iniciada correctamente.', 'success');
      window.location.href = safeNext();
    });
  }

  /* ---------- REGISTRO ---------- */
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors(registerForm);

      const payload = {
        first_name: document.getElementById('reg-first-name').value.trim(),
        last_name: document.getElementById('reg-last-name').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        rut: document.getElementById('reg-rut').value.trim(),
        telefono: document.getElementById('reg-phone').value.trim(),
        direccion: document.getElementById('reg-address').value.trim(),
        password: document.getElementById('reg-password').value,
      };
      const password2 = document.getElementById('reg-password2').value;
      const submitBtn = document.getElementById('register-submit');

      // Validación cliente
      let ok = true;
      if (!EMAIL_RE.test(payload.email)) { setFieldError(registerForm, 'email', 'Ingresa un correo válido.'); ok = false; }
      if (!payload.rut) { setFieldError(registerForm, 'rut', 'El RUT es obligatorio.'); ok = false; }
      if (payload.password.length < 8) { setFieldError(registerForm, 'password', 'Mínimo 8 caracteres.'); ok = false; }
      if (payload.password !== password2) { setFieldError(registerForm, 'password2', 'Las contraseñas no coinciden.'); ok = false; }
      if (!ok) return;

      setLoading(submitBtn, true, 'Creando cuenta...');
      const r = await api.post('/accounts/register/', { body: payload });
      setLoading(submitBtn, false);

      if (!r.ok) {
        showServerErrors(registerForm, r.data);
        return;
      }

      // Registro OK -> login automático con las mismas credenciales
      const lr = await api.post('/auth/login/', {
        body: { email: payload.email, password: payload.password }
      });

      if (lr.ok) {
        auth.setTokens(lr.data.access, lr.data.refresh);
        toast('Cuenta creada. ¡Bienvenido/a!', 'success');
        window.location.href = '/';
      } else {
        // Raro, pero posible: cuenta creada pero login automático falló
        toast('Cuenta creada. Inicia sesión para continuar.', 'success');
        window.location.href = '/login/';
      }
    });
  }
})();