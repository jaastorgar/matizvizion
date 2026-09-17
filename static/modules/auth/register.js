(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) return;
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
  var selReg = document.getElementById('reg-region'), selCom = document.getElementById('reg-comuna');
  Object.keys(REG).forEach(function (r){ var o = document.createElement('option'); o.value = r; o.textContent = r; selReg.appendChild(o); });
  selReg.addEventListener('change', function (){
    selCom.innerHTML = '<option value="">Selecciona…</option>';
    (REG[selReg.value] || []).forEach(function (c){ var o = document.createElement('option'); o.value = c; o.textContent = c; selCom.appendChild(o); });
    selCom.disabled = !selReg.value;
  });

  function err(msg){ var e = document.getElementById('reg-err'); e.style.display = 'block'; e.innerHTML = msg; }
  document.getElementById('reg-form').addEventListener('submit', function (ev){
    ev.preventDefault();
    document.getElementById('reg-err').style.display = 'none';
    var data = {
      email: document.getElementById('reg-email').value.trim(),
      password: document.getElementById('reg-pass').value,
      first_name: document.getElementById('reg-nombre').value.trim(),
      last_name: document.getElementById('reg-apellido').value.trim(),
      rut: document.getElementById('reg-rut').value.trim(),
      telefono: document.getElementById('reg-telefono').value.trim(),
      direccion: document.getElementById('reg-direccion').value.trim(),
      region: selReg.value,
      comuna: selCom.value
    };
  if (!document.getElementById('reg-terminos').checked) { err('Debes aceptar los términos y la política de privacidad para registrarte.'); return; }
  if (!data.email || !data.rut || !data.telefono || !data.direccion || !data.region || !data.comuna) { err('Completa todos los campos obligatorios (*).'); return; }
    if (data.password !== document.getElementById('reg-pass2').value) { err('Las contraseñas no coinciden.'); return; }
    data.acepta_terminos = document.getElementById('reg-terminos').checked;
data.consiente_salud = document.getElementById('reg-salud').checked;
data.consiente_marketing = document.getElementById('reg-marketing').checked;
api.post('/accounts/register/', { body: data }).then(function (r){
      if (r.ok) { toast('¡Cuenta creada! Inicia sesión.', 'success'); setTimeout(function(){ location.href = '/login/'; }, 700); }
      else {
        var msgs = [];
        if (r.data) Object.keys(r.data).forEach(function (k){ var v = r.data[k]; msgs.push('<b>' + k + ':</b> ' + (Array.isArray(v) ? v.join(' ') : v)); });
        err(msgs.join('<br>') || 'No se pudo registrar.');
      }
    });
  });
})();