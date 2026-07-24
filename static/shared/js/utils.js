(function () {
  'use strict';
  var API_BASE = '/api';
  var TOKEN_KEY = 'mv_access_token';
  var REFRESH_KEY = 'mv_refresh_token';
  var auth = {
    getAccess:  function () { return localStorage.getItem(TOKEN_KEY); },
    getRefresh: function () { return localStorage.getItem(REFRESH_KEY); },
    setTokens: function (access, refresh) { localStorage.setItem(TOKEN_KEY, access); if (refresh) localStorage.setItem(REFRESH_KEY, refresh); mePromise = null; },
    clearTokens: function () { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_KEY); mePromise = null; },
    isAuthenticated: function () { return !!this.getAccess(); },
    logout: function (redirectToLogin) { this.clearTokens(); if (redirectToLogin !== false) window.location.href = '/login/'; }
  };
  var refreshPromise = null;
  function refreshAccessToken() {
    var refresh = auth.getRefresh();
    if (!refresh) return Promise.resolve(false);
    if (!refreshPromise) {
      refreshPromise = fetch(API_BASE + '/auth/refresh/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh: refresh }) })
        .then(function (res) { return res.ok ? res.json() : null; })
        .finally(function () { refreshPromise = null; });
    }
    return refreshPromise.then(function (data) { if (data && data.access) { auth.setTokens(data.access, auth.getRefresh()); return true; } return false; });
  }
  function apiRequest(method, path, opts) {
    opts = opts || {};
    var headers = Object.assign({ 'Accept': 'application/json' }, opts.headers || {});
    var token = auth.getAccess();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var body = opts.body;
    if (body && typeof body === 'object' && !(body instanceof FormData)) { headers['Content-Type'] = headers['Content-Type'] || 'application/json'; body = JSON.stringify(body); }
    var url = (path.indexOf('http') === 0) ? path : (API_BASE + path);
    return fetch(url, { method: method, headers: headers, body: body }).then(function (response) {
      if (response.status === 401 && !opts.isRetry) {
        return refreshAccessToken().then(function (refreshed) {
          if (refreshed) { opts.isRetry = true; return apiRequest(method, path, opts); }
          auth.logout(true); return { ok: false, status: 401, data: null };
        });
      }
      return response.text().then(function (text) {
        var data = null; if (text) { try { data = JSON.parse(text); } catch (e) { data = text; } }
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }
  var api = {
    get: function (p, o) { return apiRequest('GET', p, o); },
    post: function (p, o) { return apiRequest('POST', p, o); },
    put: function (p, o) { return apiRequest('PUT', p, o); },
    patch: function (p, o) { return apiRequest('PATCH', p, o); },
    'delete': function (p, o) { return apiRequest('DELETE', p, o); }
  };
  function toast(message, type, timeout) {
    type = type || 'success'; timeout = timeout || 3000;
    var el = document.createElement('div'); el.className = 'mv-toast ' + type; el.textContent = message;
    document.body.appendChild(el); setTimeout(function () { el.remove(); }, timeout);
  }
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function formatRut(rut) {
    if (rut === null || rut === undefined) return '';
    var clean = String(rut).toUpperCase().replace(/[^0-9K]/g, '');
    if (clean.length < 2) return clean;
    var dv = clean.slice(-1);
    var body = clean.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return body + '-' + dv;
  }
  var mePromise = null;
  function me() {
    if (!auth.isAuthenticated()) return Promise.resolve(null);
    if (!mePromise) {
      mePromise = api.get('/accounts/me/').then(function (r) { return (r.ok && r.data) ? r.data : null; }).catch(function () { return null; });
    }
    return mePromise;
  }
  function refreshCartBadge() {
    var badge = document.getElementById('cart-badge');
    if (!badge) return;
    if (!auth.isAuthenticated()) { badge.hidden = true; badge.textContent = '0'; return; }
    api.get('/orders/carrito/').then(function (r) {
      if (!r.ok || !Array.isArray(r.data)) { badge.hidden = true; badge.textContent = '0'; return; }
      var total = r.data.reduce(function (a, it) { return a + (Number(it.cantidad) || 0); }, 0);
      badge.textContent = String(total); badge.hidden = total <= 0;
    });
  }
  function ensureGuest() {
    if (auth.isAuthenticated()) return Promise.resolve(true);
    return new Promise(function (resolve) {
      var ov = document.createElement('div');
      ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:2000;display:flex;align-items:center;justify-content:center;padding:1rem;';
      var box = document.createElement('div');
      box.style.cssText = 'background:#fff;border-radius:12px;max-width:420px;width:100%;padding:1.75rem;box-shadow:0 10px 30px rgba(0,0,0,.2);';
      box.innerHTML =
        '<h3 style="margin:0 0 .5rem;font-weight:800;">Continuar como invitado</h3>' +
        '<p style="margin:0 0 1rem;color:#6B7280;font-size:.92rem;">Solo necesitamos tu email para guardar tu carrito y que puedas rastrear tu pedido. <strong>No creamos contraseña.</strong></p>' +
        '<input id="gv-email" type="email" placeholder="tu@correo.cl" style="width:100%;padding:.6rem .75rem;border:1px solid #E5E7EB;border-radius:8px;margin-bottom:.5rem;box-sizing:border-box;" />' +
        '<div id="gv-msg" style="min-height:1.2rem;font-size:.85rem;margin-bottom:.75rem;"></div>' +
        '<div style="display:flex;gap:.5rem;">' +
          '<button id="gv-go" type="button" style="flex:1;padding:.6rem;border:none;border-radius:8px;background:#10B981;color:#fff;font-weight:700;cursor:pointer;">Continuar</button>' +
          '<button id="gv-login" type="button" style="padding:.6rem .9rem;border:1px solid #10B981;border-radius:8px;background:#fff;color:#065F46;font-weight:600;cursor:pointer;">Iniciar sesión</button>' +
        '</div>';
      ov.appendChild(box);
      document.body.appendChild(ov);
      var email = box.querySelector('#gv-email');
      var msg = box.querySelector('#gv-msg');
      var go = box.querySelector('#gv-go');
      var login = box.querySelector('#gv-login');
      function close(val) { if (ov.parentNode) document.body.removeChild(ov); resolve(val); }
      email.focus();
      login.addEventListener('click', function () { close(false); window.location.href = '/login/?next=' + encodeURIComponent(location.pathname); });
      ov.addEventListener('click', function (e) { if (e.target === ov) close(false); });
      function submit() {
        var em = (email.value || '').trim();
        msg.style.color = '#DC2626';
        if (!em) { msg.textContent = 'Escribe tu email.'; return; }
        go.disabled = true; go.textContent = 'Continuando…'; msg.textContent = '';
        api.post('/accounts/guest/', { body: { email: em } }).then(function (r) {
          if (r.ok && r.data && r.data.access) {
            auth.setTokens(r.data.access, r.data.refresh);
            msg.style.color = '#065F46'; msg.textContent = 'Listo. Agregando…';
            setTimeout(function () { close(true); }, 250);
          } else if (r.status === 409) {
            go.disabled = false; go.textContent = 'Continuar';
            msg.textContent = 'Ese correo ya tiene una cuenta. Inicia sesión.';
          } else {
            go.disabled = false; go.textContent = 'Continuar';
            msg.textContent = (r.data && (r.data.email || r.data.error)) || 'No se pudo continuar.';
          }
        });
      }
      go.addEventListener('click', submit);
      email.addEventListener('keydown', function (e) { if (e.key === 'Enter') submit(); });
    });
  }
  window.MV = window.MV || {};
  window.MV.api = api; window.MV.auth = auth; window.MV.toast = toast; window.MV.escape = escapeHtml;
  window.MV.formatRut = formatRut; window.MV.me = me; window.MV.refreshCartBadge = refreshCartBadge;
  window.MV.ensureGuest = ensureGuest; window.MV.API_BASE = API_BASE;
})();