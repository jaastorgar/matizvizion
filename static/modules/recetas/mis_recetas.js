(function () {
'use strict';
var MV = window.MV; if (!MV || !MV.api) return;
var api = MV.api, toast = MV.toast, esc = MV.escape || function (s) { return s; };
var list = document.getElementById('rec-list');
var form = document.getElementById('rec-form');
var fileInput = document.getElementById('rec-file');
var drop = document.getElementById('rec-drop');
var consentOk = true;

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
    '<div class="mv-rec-meta">' + esc(r.tipo_display || '') + ' · Subida ' + fmtFecha(r.creado_en) +
    (r.vigencia_hasta ? ' · Vigente hasta ' + fmtFecha(r.vigencia_hasta) : '') +
    (r.subido_por_nombre ? ' · Por ' + esc(r.subido_por_nombre) : '') + '</div>' +
    (r.detalle ? '<div class="mv-rec-det">' + esc(r.detalle) + '</div>' : '') + '</div>' +
    '<div class="mv-rec-side">' + badgeEstado(r) +
    '<a class="btn btn-outline-mv btn-sm" href="' + (r.archivo_url || '#') + '" target="_blank" rel="noopener"><i class="bi bi-download"></i> Ver</a>' +
    '<button type="button" class="btn btn-sm mv-rec-del" data-del="' + r.id + '" title="Eliminar"><i class="bi bi-trash"></i></button></div></div>';
}
function load() {
  list.innerHTML = '<div class="mv-empty">Cargando tus recetas…</div>';
  api.get('/recetas/').then(function (r) {
    var items = (r.ok && Array.isArray(r.data)) ? r.data : [];
    if (!items.length) {
      list.innerHTML = '<div class="mv-empty"><span class="ico"><i class="bi bi-file-earmark-medical"></i></span>Aún no subes recetas.<br>Usa el formulario de arriba para cargar la tuya.</div>';
      return;
    }
    list.innerHTML = items.map(card).join('');
  });
}
list.addEventListener('click', function (e) {
  var b = e.target.closest('button[data-del]'); if (!b) return;
  if (!confirm('¿Eliminar esta receta? Esta acción no se puede deshacer.')) return;
  api.delete('/recetas/' + b.getAttribute('data-del') + '/').then(function (r) {
    if (r.ok) { toast('Receta eliminada.', 'success'); load(); }
    else { toast('No se pudo eliminar.', 'error'); }
  });
});
drop.addEventListener('click', function () { fileInput.click(); });
['dragover', 'dragenter'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add('over'); }); });
['dragleave', 'drop'].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove('over'); }); });
drop.addEventListener('drop', function (e) {
  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
    fileInput.files = e.dataTransfer.files;
    syncName();
  }
});
fileInput.addEventListener('change', syncName);
function syncName() {
  var f = fileInput.files[0];
  document.getElementById('rec-filename').textContent = f ? (f.name + ' · ' + Math.round(f.size / 1024) + ' KB') : 'Ningún archivo elegido';
}
form.addEventListener('submit', function (e) {
  e.preventDefault();
  if (!consentOk) { toast('Primero autoriza el tratamiento de tus datos de salud.', 'error'); return; }
  var f = fileInput.files[0];
  if (!f) { toast('Adjunta el archivo de tu receta.', 'error'); return; }
  if (f.size > 10 * 1024 * 1024) { toast('El archivo supera 10 MB.', 'error'); return; }
  var btn = document.getElementById('rec-submit');
  btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Subiendo…';
  var rd = new FileReader();
  rd.onload = function () {
    api.post('/recetas/', { body: {
      archivo_base64: String(rd.result),
      archivo_nombre: f.name,
      tipo: document.getElementById('rec-tipo').value,
      nombre: document.getElementById('rec-nombre').value.trim(),
      detalle: document.getElementById('rec-detalle').value.trim(),
      vigencia_hasta: document.getElementById('rec-vigencia').value || null
    } }).then(function (r) {
      btn.disabled = false; btn.innerHTML = '<i class="bi bi-upload"></i> Subir receta';
      if (r.ok) { toast('Receta subida correctamente.', 'success'); form.reset(); syncName(); load(); }
      else {
        var m = r.data && (r.data.archivo || r.data.error || r.data.detail);
        toast(Array.isArray(m) ? m[0] : (m || 'No se pudo subir la receta.'), 'error');
      }
    });
  };
  rd.readAsDataURL(f);
});
api.get('/accounts/consentimientos/').then(function (r) {
  var box = document.getElementById('rec-consent');
  consentOk = !!(r.ok && r.data && r.data.consiente_salud);
  if (consentOk) { if (box) box.hidden = true; return; }
  if (box) {
    box.hidden = false;
    document.getElementById('rec-consent-btn').addEventListener('click', function () {
      api.patch('/accounts/consentimientos/', { body: { consiente_salud: true } }).then(function (r2) {
        if (r2.ok) { consentOk = true; box.hidden = true; toast('Consentimiento registrado.', 'success'); }
      });
    });
  }
});
load();
})();