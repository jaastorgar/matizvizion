(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('reserva.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape;
  var selSuc = document.getElementById('r-sucursal'), selTec = document.getElementById('r-tecnologo');
  var inpFecha = document.getElementById('r-fecha'), chips = document.getElementById('r-chips');
  var selBox = document.getElementById('r-selected'), btn = document.getElementById('r-confirm'), msg = document.getElementById('r-msg');
  var TEC = [], selectedBloque = null, loadedFecha = null;
  var reagendarId = new URLSearchParams(location.search).get('reagendar');
  console.log('[reserva] modo inicial =', reagendarId ? ('REAGENDAR cita ' + reagendarId) : 'CREAR');

  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function todayStr(){ var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
  function fmtHora(h){ return String(h).slice(0,5); }
  function setMsg(t, ok){ msg.textContent = t || ''; msg.className = 'text-center mt-2 mb-0 ' + (ok ? 'text-cta' : 'text-danger'); }
  function tecLabel(t){ return t.nombre + (t.especialidad ? ' (' + t.especialidad + ')' : ''); }
  function fillSelect(el, items, labelFn){
    el.innerHTML = '<option value="">Selecciona…</option>';
    items.forEach(function (it){ var o = document.createElement('option'); o.value = it.id; o.textContent = labelFn(it); o.dataset.nombre = (it.nombre || ''); el.appendChild(o); });
    el.disabled = items.length === 0;
  }
  function resetSelection(){
    selectedBloque = null; btn.disabled = true;
    selBox.className = 'mv-selected-box empty'; selBox.textContent = 'Bloque seleccionado: ninguno';
  }
  function loadBloques(){
    resetSelection();
    var s = selSuc.value, t = selTec.value, f = inpFecha.value;
    loadedFecha = f;
    if (!s || !t || !f) { chips.innerHTML = '<span class="mv-empty">Selecciona sucursal, tecnólogo y fecha.</span>'; return; }
    if (f < todayStr()) { chips.innerHTML = '<span class="mv-empty">No se puede agendar en una fecha pasada.</span>'; return; }
    api.get('/appointments/bloques/?sucursal=' + s + '&fecha=' + f).then(function (r){
      loadedFecha = f;
      if (!r.ok || !Array.isArray(r.data)) { chips.innerHTML = '<span class="mv-empty">No se pudieron cargar los bloques.</span>'; return; }
      var list = r.data.filter(function (b){ return String(b.tecnologo) === String(t); });
      if (!list.length) { chips.innerHTML = '<span class="mv-empty">No hay bloques disponibles para esa selección.</span>'; return; }
      chips.innerHTML = list.map(function (b){
        return '<button type="button" class="mv-chip" data-id="' + b.id + '" data-fecha="' + f + '" data-hi="' + fmtHora(b.hora_inicio) + '" data-hf="' + fmtHora(b.hora_fin) + '">' + fmtHora(b.hora_inicio) + '</button>';
      }).join('');
    });
  }
  chips.addEventListener('click', function (e){
    var c = e.target.closest('.mv-chip'); if (!c) return;
    // Doble seguro: si el input no coincide con la fecha de los chips cargados,
    // recargo y NO selecciono (evita mandar un id de otra fecha).
    if (inpFecha.value !== loadedFecha || c.getAttribute('data-fecha') !== inpFecha.value) {
      toast('La fecha cambió; recargando bloques…', 'error');
      loadBloques();
      return;
    }
    chips.querySelectorAll('.mv-chip').forEach(function (x){ x.classList.remove('active'); });
    c.classList.add('active');
    selectedBloque = c.getAttribute('data-id');
    selBox.className = 'mv-selected-box';
    selBox.textContent = 'Bloque seleccionado: ' + inpFecha.value + ' · ' + c.getAttribute('data-hi') + ' – ' + c.getAttribute('data-hf');
    btn.disabled = false; setMsg('');
  });
  btn.addEventListener('click', function (){
    if (!auth.isAuthenticated()) { toast('Inicia sesión para continuar.', 'error'); window.location.href = '/login/?next=/citas/'; return; }
    if (!selectedBloque) return;
    // Validaciones finales antes de enviar
    if (inpFecha.value < todayStr()) { setMsg('No se puede agendar ni reagendar en una fecha pasada.', false); return; }
    if (inpFecha.value !== loadedFecha) { setMsg('Los bloques no coinciden con la fecha seleccionada; recargando.', false); loadBloques(); return; }
    var modoReagendar = !!reagendarId;
    console.log('[reserva] CONFIRMAR modo =', modoReagendar ? ('reagendar ' + reagendarId) : 'crear', '| bloque =', selectedBloque, '| fecha =', inpFecha.value);
    btn.disabled = true; btn.textContent = modoReagendar ? 'Reagendando…' : 'Reservando…';
    var prom = modoReagendar
      ? api.post('/appointments/citas/' + reagendarId + '/reagendar/', { body: { bloque: Number(selectedBloque) } })
      : api.post('/appointments/citas/', { body: { bloque: Number(selectedBloque) } });
    prom.then(function (r){
      btn.textContent = modoReagendar ? 'Confirmar reagenda' : 'Confirmar Reserva';
      if (r.ok) {
        if (modoReagendar) { toast('¡Cita reagendada con éxito!', 'success'); setMsg('Tu cita fue movida al nuevo bloque.', true); setTimeout(function(){ window.location.href = '/mis-citas/'; }, 900); }
        else { toast('¡Cita reservada con éxito!', 'success'); setMsg('Cita agendada. Te esperamos.', true); loadBloques(); }
      } else {
        var m = (r.data && (r.data.error || r.data.detail)) || 'No se pudo completar.';
        setMsg(m, false); btn.disabled = false;
      }
    });
  });
  selSuc.addEventListener('change', function (){
    fillSelect(selTec, TEC.filter(function (t){ return String(t.sucursal) === selSuc.value; }), tecLabel);
    selTec.value = ''; inpFecha.value = ''; loadedFecha = null; loadBloques();
  });
  selTec.addEventListener('change', function (){ inpFecha.value = todayStr(); loadBloques(); });
  // Escuchamos 'input' Y 'change' para que el date nunca quede desincronizado
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
      // La fecha precargada nunca puede ser pasada; si lo fuera, cae a hoy
      var fc = c.bloque_fecha || todayStr();
      inpFecha.value = (fc < todayStr()) ? todayStr() : fc;
      loadBloques();
    }).catch(function () {});
  }

  Promise.all([api.get('/core/sucursales/'), api.get('/appointments/tecnologos/')]).then(function (res){
    var rs = res[0], rt = res[1];
    if (rs.ok && Array.isArray(rs.data)) fillSelect(selSuc, rs.data, function (s){ return s.nombre; });
    if (rt.ok && Array.isArray(rt.data)) TEC = rt.data;
    inpFecha.min = todayStr();
    if (reagendarId) precargarReagendar();
  });
})();