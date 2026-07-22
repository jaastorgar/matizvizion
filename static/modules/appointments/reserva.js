/* Óptica Matiz Visión — reserva.js (Fase 11) */
(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('reserva.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, toast = MV.toast, esc = MV.escape;
  var selSuc = document.getElementById('r-sucursal'), selTec = document.getElementById('r-tecnologo');
  var inpFecha = document.getElementById('r-fecha'), chips = document.getElementById('r-chips');
  var selBox = document.getElementById('r-selected'), btn = document.getElementById('r-confirm'), msg = document.getElementById('r-msg');
  var TEC = [], selectedBloque = null;

  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function todayStr(){ var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
  function fmtHora(h){ return String(h).slice(0,5); }
  function setMsg(t, ok){ msg.textContent = t || ''; msg.className = 'text-center mt-2 mb-0 ' + (ok ? 'text-cta' : 'text-danger'); }

  function fillSelect(el, items, labelFn){
    el.innerHTML = '<option value="">Selecciona…</option>';
    items.forEach(function (it){ var o = document.createElement('option'); o.value = it.id; o.textContent = labelFn(it); el.appendChild(o); });
    el.disabled = items.length === 0;
  }

  function loadBloques(){
    selectedBloque = null; btn.disabled = true;
    selBox.className = 'mv-selected-box empty'; selBox.textContent = 'Bloque seleccionado: ninguno';
    var s = selSuc.value, t = selTec.value, f = inpFecha.value;
    if (!s || !t || !f) { chips.innerHTML = '<span class="mv-empty">Selecciona sucursal, tecnólogo y fecha.</span>'; return; }
    api.get('/appointments/bloques/?sucursal=' + s + '&fecha=' + f).then(function (r){
      if (!r.ok || !Array.isArray(r.data)) { chips.innerHTML = '<span class="mv-empty">No se pudieron cargar los bloques.</span>'; return; }
      var list = r.data.filter(function (b){ return String(b.tecnologo) === String(t); });
      if (!list.length) { chips.innerHTML = '<span class="mv-empty">No hay bloques disponibles para esa selección.</span>'; return; }
      chips.innerHTML = list.map(function (b){ return '<button type="button" class="mv-chip" data-id="' + b.id + '" data-hi="' + fmtHora(b.hora_inicio) + '" data-hf="' + fmtHora(b.hora_fin) + '">' + fmtHora(b.hora_inicio) + '</button>'; }).join('');
    });
  }

  chips.addEventListener('click', function (e){
    var c = e.target.closest('.mv-chip'); if (!c) return;
    chips.querySelectorAll('.mv-chip').forEach(function (x){ x.classList.remove('active'); });
    c.classList.add('active');
    selectedBloque = c.getAttribute('data-id');
    selBox.className = 'mv-selected-box';
    selBox.textContent = 'Bloque seleccionado: ' + inpFecha.value + ' · ' + c.getAttribute('data-hi') + ' – ' + c.getAttribute('data-hf');
    btn.disabled = false; setMsg('');
  });

  btn.addEventListener('click', function (){
    if (!auth.isAuthenticated()) { toast('Inicia sesión para reservar.', 'error'); window.location.href = '/login/?next=/citas/'; return; }
    if (!selectedBloque) return;
    btn.disabled = true; btn.textContent = 'Reservando…';
    api.post('/appointments/citas/', { body: { bloque: Number(selectedBloque) } }).then(function (r){
      btn.textContent = 'Confirmar Reserva';
      if (r.ok) { toast('¡Cita reservada con éxito!', 'success'); setMsg('Cita agendada. Te esperamos.', true); loadBloques(); }
      else { var m = (r.data && (r.data.error || r.data.detail)) || 'No se pudo reservar.'; setMsg(m, false); btn.disabled = false; }
    });
  });

  selSuc.addEventListener('change', function (){
    fillSelect(selTec, TEC.filter(function (t){ return String(t.sucursal) === selSuc.value; }), function (t){ return t.nombre + (t.especialidad ? ' (' + t.especialidad + ')' : ''); });
    selTec.value = ''; inpFecha.value = ''; loadBloques();
  });
  selTec.addEventListener('change', function (){ inpFecha.value = todayStr(); loadBloques(); });
  inpFecha.addEventListener('change', loadBloques);

  Promise.all([api.get('/core/sucursales/'), api.get('/appointments/tecnologos/')]).then(function (res){
    var rs = res[0], rt = res[1];
    if (rs.ok && Array.isArray(rs.data)) fillSelect(selSuc, rs.data, function (s){ return s.nombre; });
    if (rt.ok && Array.isArray(rt.data)) TEC = rt.data;
    inpFecha.min = todayStr();
  });
})();