(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('reserva.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape;
  var selSuc = document.getElementById('r-sucursal'), selTec = document.getElementById('r-tecnologo');
  var inpFecha = document.getElementById('r-fecha'), chips = document.getElementById('r-chips');
  var selBox = document.getElementById('r-selected'), btn = document.getElementById('r-confirm'), msg = document.getElementById('r-msg');
  var daysWrap = document.getElementById('r-days');
  var TEC = [], selectedBloque = null, selectedHi = null, loadedFecha = null;
  var reagendarId = new URLSearchParams(location.search).get('reagendar');
  var DAYS_ES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  console.log('[reserva] modo inicial =', reagendarId ? ('REAGENDAR cita ' + reagendarId) : 'CREAR');

  // Estilo para chips de horarios que ya pasaron (se inyecta una sola vez)
  if (!document.getElementById('mv-reserva-past-style')) {
    var st = document.createElement('style'); st.id = 'mv-reserva-past-style';
    st.textContent = '.mv-chip.past,.mv-chip:disabled{opacity:.45;border-color:var(--border-color,#e5e7eb);color:var(--lead-muted,#6b7280);background:var(--lead-light,#f3f4f6);cursor:not-allowed;transform:none;box-shadow:none;text-decoration:line-through;}';
    document.head.appendChild(st);
  }

  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function isoOf(d){ return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function todayStr(){ return isoOf(new Date()); }
  function nowHM(){ var d = new Date(); return pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function isPast(f, hi){ return f === todayStr() && hi <= nowHM(); }
  function fmtHora(h){ return String(h).slice(0, 5); }
  function setMsg(t, ok){ msg.textContent = t || ''; msg.className = 'text-center mt-2 mb-0 ' + (ok ? 'text-cta' : 'text-danger'); }
  function showConsentSalud(onAccept) {
  if (document.getElementById('mv-consent-ov')) return;
  var ov = document.createElement('div');
  ov.id = 'mv-consent-ov';
  ov.style.cssText = 'position:fixed;inset:0;z-index:2100;display:flex;align-items:center;justify-content:center;background:rgba(17,24,39,.55);backdrop-filter:blur(3px);padding:1rem;';
  ov.innerHTML =
    '<div style="max-width:520px;width:100%;background:#fff;border-radius:16px;padding:1.6rem;box-shadow:0 30px 70px rgba(17,24,39,.4);">' +
    '<h3 style="font-weight:800;margin:0 0 .6rem;">Consentimiento de datos de salud</h3>' +
    '<p class="text-secondary small mb-3">Para agendar tu examen visual necesitamos tu autorización expresa para tratar tus datos de salud visual (Ley 21.719). Revisa la <a href="/privacidad/" target="_blank" rel="noopener">política de privacidad</a>.</p>' +
    '<div class="form-check"><input class="form-check-input" type="checkbox" id="mv-consent-salud-cb"><label class="form-check-label small" for="mv-consent-salud-cb">Autorizo el almacenamiento y tratamiento de mis datos de salud visual y recetas.</label></div>' +
    '<div style="display:flex;justify-content:flex-end;gap:.6rem;margin-top:1.1rem;">' +
    '<button type="button" class="btn btn-outline-mv btn-sm" id="mv-consent-no">Cancelar</button>' +
    '<button type="button" class="btn btn-cta btn-sm" id="mv-consent-si" disabled>Autorizar y continuar</button></div></div>';
  document.body.appendChild(ov);
  var cb = ov.querySelector('#mv-consent-salud-cb'), si = ov.querySelector('#mv-consent-si'), no = ov.querySelector('#mv-consent-no');
  cb.addEventListener('change', function(){ si.disabled = !cb.checked; });
  function close(){ if (ov.parentNode) ov.parentNode.removeChild(ov); }
  no.addEventListener('click', close);
  ov.addEventListener('click', function(e){ if (e.target === ov) close(); });
  si.addEventListener('click', function(){
    si.disabled = true; si.textContent = 'Autorizando…';
    api.patch('/accounts/consentimientos/', { body: { consiente_salud: true } }).then(function(r){
      close();
      if (r.ok) { toast('Consentimiento registrado.', 'success'); if (onAccept) onAccept(); }
      else { toast('No se pudo registrar el consentimiento.', 'error'); }
    });
  });
}
function tecLabel(t){ return t.nombre + (t.especialidad ? ' (' + t.especialidad + ')' : ''); }

  function fillSelect(el, items, labelFn){
    el.innerHTML = '<option value="">Selecciona…</option>';
    items.forEach(function (it){ var o = document.createElement('option'); o.value = it.id; o.textContent = labelFn(it); o.dataset.nombre = (it.nombre || ''); el.appendChild(o); });
    el.disabled = items.length === 0;
  }
  function resetSelection(){
    selectedBloque = null; selectedHi = null; btn.disabled = true;
    selBox.className = 'mv-selected-box empty'; selBox.textContent = 'Bloque seleccionado: ninguno';
  }

  // ---- Fila de dias proximos ----
  function dayDow(i, iso){
    if (i === 0) return 'Hoy';
    if (i === 1) return 'Mañana';
    var p = iso.split('-');
    return DAYS_ES[new Date(+p[0], +p[1] - 1, +p[2]).getDay()];
  }
  function buildDays(){
    if (!daysWrap) return;
    var base = new Date(); var html = '';
    for (var i = 0; i < 8; i++){
      var d = new Date(base.getFullYear(), base.getMonth(), base.getDate() + i);
      var iso = isoOf(d); var p = iso.split('-');
      html += '<button type="button" class="mv-day-chip" data-fecha="' + iso + '" style="animation-delay:' + (i * 0.045) + 's">' +
              '<span class="mv-day-dow">' + dayDow(i, iso) + '</span>' +
              '<span class="mv-day-num">' + parseInt(p[2], 10) + '</span></button>';
    }
    daysWrap.innerHTML = html;
  }
  function syncDayChips(){
    if (!daysWrap) return;
    daysWrap.querySelectorAll('.mv-day-chip').forEach(function (c){
      c.classList.toggle('active', c.getAttribute('data-fecha') === inpFecha.value);
    });
  }
  if (daysWrap) {
    daysWrap.addEventListener('click', function (e){
      var c = e.target.closest('.mv-day-chip'); if (!c) return;
      inpFecha.value = c.getAttribute('data-fecha');
      loadBloques();
    });
  }

  function loadBloques(){
    resetSelection();
    var s = selSuc.value, t = selTec.value, f = inpFecha.value;
    loadedFecha = f;
    syncDayChips();
    if (!s || !t || !f) { chips.innerHTML = '<span class="mv-empty">Selecciona sucursal, tecnólogo y fecha.</span>'; return; }
    if (f < todayStr()) { chips.innerHTML = '<span class="mv-empty">No se puede agendar en una fecha pasada.</span>'; return; }
    api.get('/appointments/bloques/?sucursal=' + s + '&fecha=' + f).then(function (r){
      loadedFecha = f; syncDayChips();
      if (!r.ok || !Array.isArray(r.data)) { chips.innerHTML = '<span class="mv-empty">No se pudieron cargar los bloques.</span>'; return; }
      var list = r.data.filter(function (b){ return String(b.tecnologo) === String(t); });
      if (!list.length) { chips.innerHTML = '<span class="mv-empty">No hay bloques disponibles para esa selección.</span>'; return; }
      chips.innerHTML = list.map(function (b){
        var hi = fmtHora(b.hora_inicio);
        var past = isPast(f, hi);
        return '<button type="button" class="mv-chip' + (past ? ' past' : '') + '" data-id="' + b.id + '" data-fecha="' + f + '" data-hi="' + hi + '" data-hf="' + fmtHora(b.hora_fin) + '"' + (past ? ' disabled title="Este horario ya pasó"' : '') + '>' + hi + '</button>';
      }).join('');
      tickPast();
    });
  }

  // Deshabilita en tiempo real los bloques de hoy que ya pasaron (cada 30 s)
  function tickPast(){
    var changed = false;
    chips.querySelectorAll('.mv-chip:not([disabled])').forEach(function (c){
      if (isPast(c.getAttribute('data-fecha'), c.getAttribute('data-hi'))) {
        c.disabled = true; c.classList.add('past'); c.title = 'Este horario ya pasó'; changed = true;
        if (c.classList.contains('active')) {
          c.classList.remove('active');
          selectedBloque = null; selectedHi = null; btn.disabled = true;
          selBox.className = 'mv-selected-box empty'; selBox.textContent = 'Bloque seleccionado: ninguno';
        }
      }
    });
    if (changed) toast('Algunos horarios ya pasaron y se deshabilitaron.', 'error');
  }
  setInterval(tickPast, 30000);

  chips.addEventListener('click', function (e){
    var c = e.target.closest('.mv-chip'); if (!c || c.disabled) return;
    if (inpFecha.value !== loadedFecha || c.getAttribute('data-fecha') !== inpFecha.value) {
      toast('La fecha cambió; recargando bloques…', 'error'); loadBloques(); return;
    }
    chips.querySelectorAll('.mv-chip').forEach(function (x){ x.classList.remove('active'); });
    c.classList.add('active');
    selectedBloque = c.getAttribute('data-id');
    selectedHi = c.getAttribute('data-hi');
    selBox.className = 'mv-selected-box';
    selBox.textContent = 'Bloque seleccionado: ' + inpFecha.value + ' · ' + selectedHi + ' – ' + c.getAttribute('data-hf');
    btn.disabled = false; setMsg('');
  });

  btn.addEventListener('click', function (){
    if (!auth.isAuthenticated()) { toast('Inicia sesión para continuar.', 'error'); window.location.href = '/login/?next=/citas/'; return; }
    if (!selectedBloque) return;
    if (inpFecha.value < todayStr()) { setMsg('No se puede agendar ni reagendar en una fecha pasada.', false); return; }
    if (selectedHi && isPast(inpFecha.value, selectedHi)) { setMsg('Ese horario ya pasó; elige uno vigente.', false); loadBloques(); return; }
    if (inpFecha.value !== loadedFecha) { setMsg('Los bloques no coinciden con la fecha seleccionada; recargando.', false); loadBloques(); return; }
    var modoReagendar = !!reagendarId;
    btn.disabled = true; btn.textContent = modoReagendar ? 'Reagendando…' : 'Reservando…';
    var prom = modoReagendar
      ? api.post('/appointments/citas/' + reagendarId + '/reagendar/', { body: { bloque: Number(selectedBloque) } })
      : api.post('/appointments/citas/', { body: { bloque: Number(selectedBloque) } });
    prom.then(function (r){
      btn.textContent = modoReagendar ? 'Confirmar reagenda' : 'Confirmar reserva';
      if (r.ok) {
        if (modoReagendar) { toast('¡Cita reagendada con éxito!', 'success'); setMsg('Tu cita fue movida al nuevo bloque.', true); setTimeout(function(){ window.location.href = '/mis-citas/'; }, 900); }
        else { toast('¡Cita reservada con éxito!', 'success'); setMsg('Cita agendada. Te esperamos.', true); loadBloques(); }
      } else {
          var code = r.data && (Array.isArray(r.data.code) ? r.data.code[0] : r.data.code);
          if (code === 'CONSENTIMIENTO_SALUD_REQUERIDO') {
            btn.disabled = false; btn.textContent = 'Confirmar reserva';
            showConsentSalud(function(){ btn.click(); });
          } else {
            var m = (r.data && (r.data.error || r.data.detail)) || 'No se pudo completar.';
            setMsg(m, false); btn.disabled = false;
          }
        }
    });
  });

  selSuc.addEventListener('change', function (){
    fillSelect(selTec, TEC.filter(function (t){ return String(t.sucursal) === selSuc.value; }), tecLabel);
    selTec.value = ''; inpFecha.value = ''; loadedFecha = null; loadBloques();
  });
  selTec.addEventListener('change', function (){
    if (!inpFecha.value) inpFecha.value = todayStr();
    loadBloques();
  });
  inpFecha.addEventListener('change', loadBloques);
  inpFecha.addEventListener('input', loadBloques);

  function precargarReagendar(){
    var card = document.querySelector('.mv-reserva-card');
    if (card) {
      var banner = document.createElement('div');
      banner.className = 'mv-selected-box'; banner.style.marginBottom = '1rem';
      banner.innerHTML = '<i class="bi bi-calendar-event"></i> Estás <strong>reagendando</strong> una cita. Elige el nuevo bloque y confirma.';
      card.parentNode.insertBefore(banner, card);
    }
    if (btn) btn.textContent = 'Confirmar reagenda';
    api.get('/appointments/citas/' + reagendarId + '/').then(function (r){
      if (!r.ok || !r.data) return;
      var c = r.data;
      var os = selSuc.querySelectorAll('option');
      for (var i = 0; i < os.length; i++) { if (os[i].dataset.nombre === c.sucursal_nombre) { selSuc.value = os[i].value; break; } }
      fillSelect(selTec, TEC.filter(function (t){ return String(t.sucursal) === selSuc.value; }), tecLabel);
      var ot = selTec.querySelectorAll('option');
      for (var j = 0; j < ot.length; j++) { if (ot[j].dataset.nombre === c.tecnologo_nombre) { selTec.value = ot[j].value; break; } }
      inpFecha.disabled = false; selTec.disabled = false;
      var fc = c.bloque_fecha || todayStr();
      inpFecha.value = (fc < todayStr()) ? todayStr() : fc;
      loadBloques();
    }).catch(function () {});
  }

  buildDays();
  Promise.all([api.get('/core/sucursales/'), api.get('/appointments/tecnologos/')]).then(function (res){
    var rs = res[0], rt = res[1];
    if (rs.ok && Array.isArray(rs.data)) fillSelect(selSuc, rs.data, function (s){ return s.nombre; });
    if (rt.ok && Array.isArray(rt.data)) TEC = rt.data;
    inpFecha.min = todayStr();
    if (reagendarId) precargarReagendar();
  });


// ---- Gate proactivo: consentimiento de salud antes de confirmar reserva ----
(function () {
  var gate = { ok: false };
  function armGate() {
    api.get('/accounts/consentimientos/').then(function (r) {
      if (!r.ok || !r.data) { gate.ok = true; return; }
      gate.ok = !!r.data.consiente_salud;
      if (gate.ok) return;
      var conf = document.getElementById('r-confirm');
      if (!conf) return;
      var banner = document.createElement('div');
      banner.className = 'mv-selected-box';
      banner.style.marginBottom = '1rem';
      banner.innerHTML = '<i class="bi bi-shield-exclamation"></i> Para agendar tu examen necesitas autorizar el tratamiento de tus datos de salud visual. Pulsa Confirmar reserva para autorizar.';
      if (conf.parentNode) conf.parentNode.insertBefore(banner, conf);
      (conf.parentNode || document).addEventListener('click', function (e) {
        if (gate.ok) return;
        if (e.target !== conf && !conf.contains(e.target)) return;
        e.stopPropagation();
        e.preventDefault();
        showConsentSalud(function () {
          gate.ok = true;
          if (banner.parentNode) banner.parentNode.removeChild(banner);
        });
      }, true);
    });
  }
  if (auth.isAuthenticated()) armGate();
})();
})();