(function () {
  'use strict';
  var API_BASE = '/api';
  var TOKEN_KEY = 'mv_access_token';
  var REFRESH_KEY = 'mv_refresh_token';
  var auth = {
    getAccess:  function () { return localStorage.getItem(TOKEN_KEY); },
    getRefresh: function () { return localStorage.getItem(REFRESH_KEY); },
    setTokens: function (access, refresh) { localStorage.setItem(TOKEN_KEY, access); if (refresh) localStorage.setItem(REFRESH_KEY, refresh); },
    clearTokens: function () { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(REFRESH_KEY); },
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
  window.MV = window.MV || {};
  window.MV.api = api; window.MV.auth = auth; window.MV.toast = toast; window.MV.escape = escapeHtml; window.MV.API_BASE = API_BASE;
})();