(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, toast = MV.toast;
  var REG = {
    'Arica y Parinacota': ['Arica','Camarones','Putre','General Lagos'],
    'Tarapacá': ['Iquique','Alto Hospicio','Pozo Almonte','Camiña','Colchane','Huara','Pica'],
    'Antofagasta': ['Antofagasta','Mejillones','Sierra Gorda','Taltal','Calama','Ollagüe','San Pedro de Atacama','Tocopilla','María Elena'],
    'Atacama': ['Copiapó','Caldera','Tierra Amarilla','Chañaral','Diego de Almagro','Vallenar','Freirina','Huasco','Alto del Carmen'],
    'Coquimbo': ['La Serena','Coquimbo','Andacollo','La Higuera','Paiguano','Vicuña','Illapel','Canela','Los Vilos','Salamanca','Ovalle','Combarbalá','Monte Patria','Punitaqui','Río Hurtado'],
    'Valparaíso': ['Valparaíso','Casablanca','Concón','Juan Fernández','Puchuncaví','Quintero','Viña del Mar','Isla de Pascua','Los Andes','Calle Larga','Rinconada','San Esteban','La Ligua','Cabildo','Papudo','Petorca','Zapallar','Quillota','La Calera','Hijuelas','La Cruz','Nogales','San Antonio','Algarrobo','Cartagena','El Quisco','El Tabo','Santo Domingo','San Felipe','Catemu','Llaillay','Panquehue','Putaendo','Santa María','Quilpué','Limache','Olmué','Villa Alemana'],
    'Metropolitana': ['Santiago','Cerrillos','Cerro Navia','Conchalí','El Bosque','Estación Central','Huechuraba','Independencia','La Cisterna','La Florida','La Granja','La Pintana','La Reina','Las Condes','Lo Barnechea','Lo Espejo','Lo Prado','Macul','Maipú','Ñuñoa','Pedro Aguirre Cerda','Peñalolén','Providencia','Pudahuel','Quilicura','Quinta Normal','Recoleta','Renca','San Joaquín','San Miguel','San Ramón','Vitacura','Puente Alto','Pirque','San José de Maipo','Colina','Lampa','Tiltil','Paine','Buin','Calera de Tango','San Bernardo','El Monte','Isla de Maipo','María Pinto','Melipilla','Padre Hurtado','Peñaflor','Talagante','Curacaví','Alhué'],
    "O'Higgins": ['Rancagua','Codegua','Coinco','Coltauco','Doñihue','Graneros','Las Cabras','Machalí','Malloa','Mostazal','Olivar','Peumo','Pichidegua','Quinta de Tilcoco','Rengo','Requínoa','San Vicente','Pichilemu','La Estrella','Litueche','Marchihue','Navidad','Paredones','San Fernando','Chépica','Chimbarongo','Lolol','Nancagua','Palmilla','Peralillo','Placilla','Pumanque','Santa Cruz'],
    'Maule': ['Talca','Constitución','Curepto','Empedrado','Maule','Pelarco','Pencahue','Río Claro','San Clemente','San Rafael','Cauquenes','Chanco','Pelluhue','Curicó','Hualañé','Licantén','Molina','Rauco','Romeral','Sagrada Familia','Teno','Vichuquén','Linares','Colbún','Longaví','Parral','Retiro','San Javier','Villa Alegre','Yerbas Buenas'],
    'Ñuble': ['Chillán','Chillán Viejo','Bulnes','Cobquecura','Coelemu','Coihueco','El Carmen','Ninquihue','Ñiquén','Pemuco','Pinto','Portezuelo','Quillón','Quirihue','Ránquil','San Carlos','San Fabián','San Ignacio','San Nicolás','Treguaco','Yungay'],
    'Biobío': ['Concepción','Coronel','Chiguayante','Florida','Hualpén','Hualqui','Lota','Penco','San Pedro de la Paz','Santa Juana','Talcahuano','Tomé','Lebu','Arauco','Cañete','Contulmo','Curanilahue','Los Álamos','Tirúa','Los Ángeles','Antuco','Cabrero','Laja','Mulchén','Nacimiento','Negrete','Quilaco','Quilleco','San Rosendo','Santa Bárbara','Tucapel','Yumbel','Alto Biobío'],
    'La Araucanía': ['Temuco','Carahue','Cholchol','Cunco','Curarrehue','Freire','Gorbea','Lautaro','Loncoche','Melipeuco','Nueva Imperial','Padre Las Casas','Perquenco','Pitrufquén','Pucón','Saavedra','Teodoro Schmidt','Toltén','Vilcún','Villarrica','Angol','Collipulli','Curacautín','Ercilla','Lonquimay','Lumaco','Purén','Renaico','Traiguén','Victoria'],
    'Los Ríos': ['Valdivia','Corral','Lanco','Los Lagos','Máfil','Mariquina','Paillaco','Panguipulli','La Unión','Futrono','Lago Ranco','Río Bueno'],
    'Los Lagos': ['Puerto Montt','Calbuco','Cochamó','Fresia','Frutillar','Los Muermos','Llanquihue','Maullín','Puerto Varas','Ancud','Castro','Curaco de Vélez','Dalcahue','Puqueldón','Queilén','Quellón','Quemchi','Chonchi','Osorno','Puerto Octay','Purranque','Puyehue','Río Negro','San Juan de la Costa','San Pablo','Palena','Futaleufú','Chaitén','Hualaihué'],
    'Aysén': ['Coyhaique','Lago Verde','Aysén','Cisnes','Guaitecas','Cochrane',"O'Higgins",'Tortel','Chile Chico','Río Ibáñez'],
    'Magallanes': ['Punta Arenas','Laguna Blanca','Río Verde','San Gregorio','Cabo de Hornos','Antártica','Porvenir','Primavera','Timaukel','Natales','Torres del Paine']
  };
  var selReg = document.getElementById('md-region'), selCom = document.getElementById('md-comuna');
  Object.keys(REG).forEach(function (r){ var o = document.createElement('option'); o.value = r; o.textContent = r; selReg.appendChild(o); });
  function fillComunas(region, comuna){
    selCom.innerHTML = '<option value="">Selecciona…</option>';
    (REG[region] || []).forEach(function (c){ var o = document.createElement('option'); o.value = c; o.textContent = c; selCom.appendChild(o); });
    selCom.disabled = !region;
    if (comuna && REG[region] && REG[region].indexOf(comuna) !== -1) selCom.value = comuna;
  }
  selReg.addEventListener('change', function (){ fillComunas(selReg.value, null); });
  function err(msg){ var e = document.getElementById('md-err'); e.style.display = 'block'; e.innerHTML = msg; }

  var loaded = null;
  function paint(d){
    loaded = d;
    var dn = ((d.first_name || '') + ' ' + (d.last_name || '')).trim();
    document.getElementById('md-nombre').textContent = dn || d.email || '—';
    document.getElementById('md-email').textContent = d.email || '';
    document.getElementById('md-id-email').textContent = d.email || '—';
    document.getElementById('md-id-rut').textContent = d.rut || '—';
    document.getElementById('md-rut').innerHTML = '<i class="bi bi-shield-lock"></i> RUT: ' + (d.rut || '—');
    document.getElementById('md-first').value = d.first_name || '';
    document.getElementById('md-last').value = d.last_name || '';
    document.getElementById('md-telefono').value = d.telefono || '';
    document.getElementById('md-direccion').value = d.direccion || '';
    if (d.region) { selReg.value = d.region; fillComunas(d.region, d.comuna); }
  }

  MV.me().then(function (u){
    if (!u) { location.replace('/login/?next=/mis-datos/'); return; }
    if (u.role === 'VENDEDOR' || u.role === 'ADMIN') { location.replace('/panel/'); return; }
    document.getElementById('md-role').innerHTML = '<i class="bi bi-person-badge"></i> ' + (u.role === 'ADMIN' ? 'Administrador' : 'Cliente');
    api.get('/accounts/mi-perfil/').then(function (r){
      if (r.ok && r.data) paint(r.data);
    });
  });

  document.getElementById('md-discard').addEventListener('click', function (){ if (loaded) paint(loaded); });

  document.getElementById('md-form').addEventListener('submit', function (ev){
    ev.preventDefault();
    document.getElementById('md-err').style.display = 'none';
    var body = {
      first_name: document.getElementById('md-first').value.trim(),
      last_name: document.getElementById('md-last').value.trim(),
      telefono: document.getElementById('md-telefono').value.trim(),
      direccion: document.getElementById('md-direccion').value.trim(),
      region: selReg.value,
      comuna: selCom.value
    };
    var btn = document.getElementById('md-save'); btn.disabled = true;
    api.patch('/accounts/mi-perfil/', { body: body }).then(function (r){
      btn.disabled = false;
      if (r.ok) { toast('Datos guardados.', 'success'); paint(r.data); }
      else {
        var msgs = [];
        if (r.data) Object.keys(r.data).forEach(function (k){ var v = r.data[k]; msgs.push('<b>' + k + ':</b> ' + (Array.isArray(v) ? v.join(' ') : v)); });
        err(msgs.join('<br>') || 'No se pudo guardar.');
      }
    });
  });
// ---- Tarjeta de consentimientos (Ley 21.719) ----
(function(){
  var grid = document.querySelector('.mv-md-grid');
  if (!grid) return;
  var card = document.createElement('div');
  card.className = 'mv-md-card mv-consent-card';
  card.innerHTML =
    '<h3><i class="bi bi-shield-lock"></i> Consentimientos</h3>' +
    '<div class="mv-md-row"><span class="k">Datos de salud visual</span><span class="v" id="md-salud-status">—</span></div>' +
    '<div class="mv-md-row"><span class="k">Ofertas y promociones</span><span class="v"><div class="form-check form-switch mb-0"><input class="form-check-input" type="checkbox" role="switch" id="md-marketing"></div></span></div>' +
    '<div class="mv-md-note"><i class="bi bi-info-circle"></i> Revisa nuestros <a href="/terminos/" target="_blank" rel="noopener">términos</a> y <a href="/privacidad/" target="_blank" rel="noopener">política de privacidad</a>.</div>';
  grid.appendChild(card);
  api.get('/accounts/consentimientos/').then(function(r){
    if (!r.ok || !r.data) return;
    var d = r.data;
    var st = document.getElementById('md-salud-status');
    st.textContent = d.consiente_salud ? ('Autorizado' + (d.consiente_salud_en ? ' el ' + String(d.consiente_salud_en).slice(0,10) : '')) : 'No autorizado';
    var sw = document.getElementById('md-marketing');
    sw.checked = !!d.consiente_marketing;
    sw.addEventListener('change', function(){
      api.patch('/accounts/consentimientos/', { body: { consiente_marketing: sw.checked } }).then(function(rr){
        if (rr.ok) toast(rr.data.consiente_marketing ? 'Te enviaremos ofertas y promociones.' : 'Dejaste de recibir ofertas y promociones.', 'success');
        else { sw.checked = !sw.checked; toast('No se pudo actualizar.', 'error'); }
      });
    });
  });
})();
})();