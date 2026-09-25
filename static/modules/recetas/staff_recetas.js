(function () {
'use strict';
var MV = window.MV; if (!MV || !MV.api) return;
var api = MV.api, toast = MV.toast, esc = MV.escape || function (s) { return s; };
var list = document.getElementById('rs-list');
var qInput = document.getElementById('rs-q');
var qInfo = document.getElementById('rs-qinfo');
var currentQ = '';

function fmtFecha(iso) { if (!iso) return '—'; var d = new Date(iso); return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' }); }
function badgeEstado(r) {
  if (r.estado === 'VIGENTE') return '<span class="mv-rec-badge ok">Vigente</span>';
  if (r.estado === 'VENCIDA') return '<span class="mv-rec-badge bad">Vencida</span>';
  return '<span class="mv-rec-badge mut">Sin fecha</span>';
}
function card(r) {
  var nom = r.nombre || (r.archivo_url ? decodeURIComponent(r.archivo_url.split('/').pop()) : ('Receta #' + r.id));
  return '<div class="mv-rec-card">' +
    '<div class="mv-rec-ico"><i class="bi bi-file-earmark-medical"></i></div>' +
    '<div class="mv-rec-info"><div class="mv-rec-nom">' + esc(nom) + '</div>' +
    '<div class="mv-rec-meta"><strong>' + esc(r.cliente_nombre || '') + '</strong> · ' + esc(r.cliente_email || '') + '<br>' +
    esc(r.tipo_display || '') + ' · Subida ' + fmtFecha(r.creado_en) + ' por ' + esc(r.subido_por_nombre || '—') +
    (r.vigencia_hasta ? ' · Vigente hasta ' + fmtFecha(r.vigencia_hasta) : '') + '</div>' +
    (r.detalle ? '<div class="mv-rec-det">' + esc(r.detalle) + '</div>' : '') + '</div>' +
    '<div class="mv-rec-side">' + badgeEstado(r) +
    '<a class="btn btn-outline-mv btn-sm" href="' + (r.archivo_url || '#') + '" target="_blank" rel="noopener"><i class="bi bi-download"></i> Ver</a>' +
    '<button type="button" class="btn btn-sm mv-rec-del" data-del="' + r.id + '" title="Eliminar"><i class="bi bi-trash"></i></button></div></div>';
}
function load() {
  list.innerHTML = '<div class="mv-empty">Cargando…</div>';
  var url = '/recetas/' + (currentQ ? ('?q=' + encodeURIComponent(currentQ)) : '');
  api.get(url).then(function (r) {
    var items = (r.ok && Array.isArray(r.data)) ? r.data : [];
    qInfo.textContent = currentQ ? ('Resultados para "' + currentQ + '": ' + items.length) : ('Mostrando todas las recetas: ' + items.length);
    if (!items.length) { list.innerHTML = '<div class="mv-empty">No hay recetas que coincidan.</div>'; return; }
    list.innerHTML = items.map(card).join('');
  });
}
document.getElementById('rs-search').addEventListener('click', function () { currentQ = qInput.value.trim(); load(); });
qInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') { currentQ = qInput.value.trim(); load(); } });
list.addEventListener('click', function (e) {
  var b = e.target.closest('button[data-del]'); if (!b) return;
  if (!confirm('¿Eliminar esta receta del cliente? Esta acción no se puede deshacer.')) return;
  api.delete('/recetas/' + b.getAttribute('data-del') + '/').then(function (r) {
    if (r.ok) { toast('Receta eliminada.', 'success'); load(); }
    else { toast('No se pudo eliminar.', 'error'); }
  });
});
document.getElementById('rs-form').addEventListener('submit', function (e) {
  e.preventDefault();
  var email = document.getElementById('rs-email').value.trim();
  var f = document.getElementById('rs-file').files[0];
  if (!email) { toast('Indica el correo del cliente.', 'error'); return; }
  if (!f) { toast('Adjunta el archivo de la receta.', 'error'); return; }
  if (f.size > 10 * 1024 * 1024) { toast('El archivo supera 10 MB.', 'error'); return; }
  var btn = document.getElementById('rs-submit');
  btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Subiendo…';
  api.get('/recetas/buscar-cliente/?q=' + encodeURIComponent(email)).then(function (rc) {
    if (!rc.ok) {
      btn.disabled = false; btn.innerHTML = '<i class="bi bi-upload"></i> Subir receta';
      toast((rc.data && rc.data.error) || 'Cliente no encontrado.', 'error');
      return;
    }
    var rd = new FileReader();
    rd.onload = function () {
      api.post('/recetas/', { body: {
        cliente: rc.data.id,
        archivo_base64: String(rd.result),
        archivo_nombre: f.name,
        tipo: document.getElementById('rs-tipo').value,
        nombre: document.getElementById('rs-nombre').value.trim(),
        detalle: document.getElementById('rs-detalle').value.trim(),
        vigencia_hasta: document.getElementById('rs-vigencia').value || null
      } }).then(function (r) {
        btn.disabled = false; btn.innerHTML = '<i class="bi bi-upload"></i> Subir receta';
        if (r.ok) { toast('Receta subida para ' + rc.data.nombre + '.', 'success'); document.getElementById('rs-form').reset(); load(); }
        else {
          var m = r.data && (r.data.archivo || r.data.error || r.data.detail);
          toast(Array.isArray(m) ? m[0] : (m || 'No se pudo subir.'), 'error');
        }
      });
    };
    rd.readAsDataURL(f);
  });
});
load();
})();