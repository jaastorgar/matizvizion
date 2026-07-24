(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, toast = MV.toast, esc = MV.escape;
  function fecha(iso){ if(!iso) return '—'; var s=String(iso); var m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/); if(m){ return new Date(+m[1],+m[2]-1,+m[3]).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); } try{ return new Date(s).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'}); }catch(e){ return s; } }
  function hora(h){ return String(h || '').slice(0, 5); }
  var TXT = { AGENDADA:'Agendada', CONFIRMADA:'Confirmada', COMPLETADA:'Completada', NO_ASISTIO:'No asistió', CANCELADA:'Cancelada' };
  function load(){
    var box = document.getElementById('mcit-list');
    api.get('/appointments/citas/').then(function (r){
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      if (!list.length) { box.innerHTML = '<div class="mv-empty"><span class="ico"><i class="bi bi-heart-pulse"></i></span>No tienes citas agendadas.<br><a class="btn btn-cta btn-sm mt-3" href="/citas/">Agendar una cita</a></div>'; return; }
      box.innerHTML = list.map(function (c){
        var editable = (c.estado === 'AGENDADA' || c.estado === 'CONFIRMADA');
        var acc = editable
          ? '<button class="btn btn-cta btn-sm" data-reag="' + c.id + '"><i class="bi bi-calendar-event"></i> Reagendar</button>' +
            '<button class="btn btn-outline-mv btn-sm" data-cancel="' + c.id + '"><i class="bi bi-x-lg"></i> Cancelar</button>'
          : '';
        return '<div class="mv-cita-row"><div><div class="mv-cita-when">' + fecha(c.bloque_fecha) + ' · ' + hora(c.bloque_hora_inicio) + '</div><div class="mv-cita-meta">' + esc(c.tecnologo_nombre || '') + ' · ' + esc(c.sucursal_nombre || '') + '</div></div><div class="d-flex align-items-center gap-2"><span class="mv-badge ' + c.estado + '">' + esc(TXT[c.estado] || c.estado) + '</span>' + acc + '</div></div>';
      }).join('');
    });
  }
  document.getElementById('mcit-list').addEventListener('click', function (e){
    var rg = e.target.closest('button[data-reag]');
    if (rg) { window.location.href = '/citas/?reagendar=' + rg.getAttribute('data-reag'); return; }
    var b = e.target.closest('button[data-cancel]'); if (!b) return;
    if (!confirm('¿Cancelar esta cita? El bloque volverá a quedar disponible.')) return;
    var id = b.getAttribute('data-cancel'); b.disabled = true;
    api.post('/appointments/citas/' + id + '/cancelar/').then(function (r){
      if (r.ok) { toast('Cita cancelada.', 'success'); load(); }
      else { toast((r.data && r.data.error) || 'No se pudo cancelar.', 'error'); b.disabled = false; }
    });
  });
  MV.me().then(function (u){
    if (!u) { location.replace('/login/?next=/mis-citas/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/panel/'); return; }
    load();
  });
})();