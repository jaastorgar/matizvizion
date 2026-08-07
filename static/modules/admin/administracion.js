(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api, toast = MV.toast, esc = MV.escape;
  var side = document.getElementById('ad-side'), title = document.getElementById('ad-title');
  var body = document.getElementById('ad-body'), btnNew = document.getElementById('ad-new');
  var modal = document.getElementById('ad-modal'), modalCard = document.getElementById('ad-modal-card');
  var current = null, cacheOpts = {};

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

  var ENT = [
    { key: 'opticas', label: 'Mis Ópticas', icon: 'bi-shop' },
    { key: 'resumen', label: 'Resumen', icon: 'bi-speedometer2' },
    { key: 'productos', label: 'Productos', icon: 'bi-box-seam', ep: '/admin/productos/',
      cols: [['nombre','Nombre'],['sku','SKU'],['precio','Precio'],['stock','Stock'],['color','Color'],['activo','Activo']],
      fields: [ {n:'nombre',l:'Nombre',t:'text'}, {n:'categoria',l:'Categoría',t:'select',src:'/admin/categorias/'},
        {n:'precio',l:'Precio',t:'number'}, {n:'stock',l:'Stock',t:'number'}, {n:'stock_minimo',l:'Stock mínimo',t:'number'},
        {n:'activo',l:'Activo',t:'check'}, {n:'destacado',l:'Destacado',t:'check'}, {n:'grupo',l:'Grupo (colores)',t:'text'}, {n:'color',l:'Color',t:'text'}, {n:'descripcion',l:'Descripción',t:'text'}, {n:'imagen',l:'Imagen del producto',t:'file'} ] },
    { key: 'categorias', label: 'Categorías', icon: 'bi-tags', ep: '/admin/categorias/',
      cols: [['nombre','Nombre'],['slug','Slug'],['orden','Orden']],
      fields: [ {n:'nombre',l:'Nombre',t:'text'}, {n:'orden',l:'Orden',t:'number'}, {n:'grupo',l:'Grupo (colores)',t:'text'}, {n:'color',l:'Color',t:'text'}, {n:'descripcion',l:'Descripción',t:'text'} ] },
    { key: 'tecnologos', label: 'Tecnólogos', icon: 'bi-person-badge', ep: '/admin/tecnologos/',
      cols: [['nombre','Nombre'],['especialidad','Especialidad'],['sucursal','Sucursal'],['activo','Activo']],
      fields: [ {n:'nombre',l:'Nombre',t:'text'}, {n:'rut',l:'RUT',t:'text'}, {n:'especialidad',l:'Especialidad',t:'text'},
        {n:'sucursal',l:'Sucursal',t:'select',src:'/admin/sucursales/'}, {n:'activo',l:'Activo',t:'check'} ] },
    { key: 'bloques', label: 'Bloques horarios', icon: 'bi-calendar-week', ep: '/admin/bloques/',
      cols: [['tecnologo','Tecnólogo'],['fecha','Fecha'],['hora_inicio','Inicio'],['hora_fin','Fin'],['disponible','Disponible']],
      fields: [ {n:'tecnologo',l:'Tecnólogo',t:'select',src:'/admin/tecnologos/'}, {n:'fecha',l:'Fecha',t:'date'},
        {n:'hora_inicio',l:'Hora inicio',t:'time'}, {n:'hora_fin',l:'Hora fin',t:'time'}, {n:'disponible',l:'Disponible',t:'check'} ] },
    { key: 'sucursales', label: 'Sucursales', icon: 'bi-geo-alt', ep: '/admin/sucursales/',
      cols: [['nombre','Nombre'],['direccion','Dirección']],
      fields: [ {n:'nombre',l:'Nombre',t:'text'}, {n:'direccion',l:'Dirección',t:'text'} ] },
    { key: 'usuarios', label: 'Usuarios', icon: 'bi-people', ep: '/admin/usuarios/',
      delMsg: '¿Eliminar este usuario? Se eliminarán también sus pedidos, citas y devoluciones asociadas. Esta acción no se puede deshacer.',
      cols: [['email','Email'],['first_name','Nombre'],['role','Rol'],['is_active','Activo']],
      fields: [ {n:'email',l:'Correo',t:'text'}, {n:'password',l:'Contraseña',t:'password'},
        {n:'first_name',l:'Nombre',t:'text'}, {n:'last_name',l:'Apellido',t:'text'},
        {n:'role',l:'Rol',t:'choice',opts:[['CLIENTE','Cliente'],['VENDEDOR','Vendedor'],['ADMIN','Admin']]},
        {n:'is_active',l:'Activo',t:'check'},
        {n:'rut',l:'RUT (cliente)',t:'text'}, {n:'telefono',l:'Teléfono',t:'text'},
        {n:'direccion',l:'Dirección',t:'text'}, {n:'region',l:'Región',t:'region'}, {n:'comuna',l:'Comuna',t:'comuna'} ] }
  ];

  function optLabel(src, id){ var o = (cacheOpts[src] || []).filter(function (x){ return String(x.id) === String(id); })[0]; return o ? (o.nombre || o.email || id) : id; }
  function loadOpts(src){ if (cacheOpts[src]) return Promise.resolve(cacheOpts[src]); return api.get(src).then(function (r){ cacheOpts[src] = (r.ok && Array.isArray(r.data)) ? r.data : []; return cacheOpts[src]; }); }

  function buildSide(){
    side.innerHTML = ENT.map(function (e){ return '<button data-ent="' + e.key + '"><i class="bi ' + e.icon + '"></i> ' + e.label + '</button>'; }).join('');
    side.querySelectorAll('button').forEach(function (b){ b.addEventListener('click', function (){ go(b.getAttribute('data-ent')); }); });
  }
  function go(key){
    current = ENT.filter(function (e){ return e.key === key; })[0];
    side.querySelectorAll('button').forEach(function (b){ b.classList.toggle('active', b.getAttribute('data-ent') === key); });
    title.textContent = current.label;
    btnNew.hidden = !!current.noCreate || !current.ep;
    if (key === 'opticas') renderOpticas();
    else if (key === 'resumen') renderResumen();
    else preload().then(renderList);
  }
  function preload(){
    var srcs = (current.fields || []).filter(function (f){ return f.src; }).map(function (f){ return f.src; });
    return Promise.all(srcs.map(loadOpts));
  }

  function renderOpticas(){
    api.get('/core/sucursales/').then(function (r){
      var list = (r.ok && Array.isArray(r.data)) ? r.data : [];
      if (!list.length) { body.innerHTML = '<div class="mv-empty">No hay ópticas registradas.</div>'; return; }
      body.innerHTML = '<div class="mv-ad-stats">' + list.map(function (s){
        return '<div class="mv-ad-stat" style="cursor:pointer;" data-opt="' + s.id + '">' +
          '<div class="n" style="font-size:1.1rem;"><i class="bi bi-shop" style="color:var(--green-dark);"></i> ' + esc(s.nombre) + '</div>' +
          '<div class="l">' + esc(s.direccion || '') + '</div>' +
          '<div class="l" style="margin-top:.4rem;color:var(--green-dark);font-weight:700;">Ver detalle <i class="bi bi-arrow-right"></i></div>' +
          '</div>';
      }).join('') + '</div>';
      body.querySelectorAll('[data-opt]').forEach(function (c){ c.addEventListener('click', function (){ openOptica(c.getAttribute('data-opt'), list); }); });
    });
  }

  function openOptica(id, list){
    var suc = (list || []).filter(function (s){ return String(s.id) === String(id); })[0] || {};
    Promise.all([
      api.get('/appointments/tecnologos/'),
      api.get('/appointments/bloques/?sucursal=' + id),
      api.get('/appointments/citas/')
    ]).then(function (res){
      var TEC = (res[0].ok && Array.isArray(res[0].data)) ? res[0].data : [];
      var BLO = (res[1].ok && Array.isArray(res[1].data)) ? res[1].data : [];
      var CIT = (res[2].ok && Array.isArray(res[2].data)) ? res[2].data : [];
      var tecIds = {};
      var tecs = TEC.filter(function (t){ return String(t.sucursal) === String(id); });
      tecs.forEach(function (t){ tecIds[t.id] = true; });
      var citas = CIT.filter(function (c){ return tecIds[c.tecnologo]; });
      var d = new Date(); var hoy = d.getFullYear() + '-' + (d.getMonth()+1<10?'0':'') + (d.getMonth()+1) + '-' + (d.getDate()<10?'0':'') + d.getDate();
      var citasHoy = citas.filter(function (c){ return c.bloque_fecha === hoy && (c.estado==='AGENDADA'||c.estado==='CONFIRMADA'); });
      var html = '<button class="btn btn-outline-mv btn-sm" data-back style="margin-bottom:1rem;"><i class="bi bi-arrow-left"></i> Volver a Mis Ópticas</button>';
      html += '<h3 style="font-family:var(--font-head);font-weight:800;color:var(--lead-dark);margin:0 0 .2rem;"><i class="bi bi-shop" style="color:var(--green-dark);"></i> ' + esc(suc.nombre || 'Óptica') + '</h3>';
      html += '<div class="l" style="color:var(--lead-muted,#6B7280);margin-bottom:1rem;">' + esc(suc.direccion || '') + '</div>';
      html += '<div class="mv-ad-stats" style="margin-bottom:1.2rem;">' +
        '<div class="mv-ad-stat"><div class="n">' + tecs.filter(function(t){return t.activo;}).length + '</div><div class="l">Tecnólogos activos</div></div>' +
        '<div class="mv-ad-stat"><div class="n">' + BLO.length + '</div><div class="l">Bloques disponibles</div></div>' +
        '<div class="mv-ad-stat"><div class="n">' + citasHoy.length + '</div><div class="l">Citas hoy</div></div>' +
        '<div class="mv-ad-stat"><div class="n">' + citas.length + '</div><div class="l">Citas totales</div></div>' +
        '</div>';
      html += '<div style="font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--lead-muted,#6B7280);margin:0 0 .5rem;">Equipo</div>';
      if (tecs.length) {
        html += '<table class="mv-ad-table"><thead><tr><th>Nombre</th><th>Especialidad</th><th>Activo</th></tr></thead><tbody>' +
          tecs.map(function (t){ return '<tr><td>' + esc(t.nombre) + '</td><td>' + esc(t.especialidad) + '</td><td>' + (t.activo ? 'Sí' : 'No') + '</td></tr>'; }).join('') +
          '</tbody></table>';
      } else html += '<div class="mv-empty">Sin tecnólogos en esta óptica.</div>';
      html += '<div style="font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--lead-muted,#6B7280);margin:1.2rem 0 .5rem;">Próximos bloques</div>';
      if (BLO.length) {
        html += '<table class="mv-ad-table"><thead><tr><th>Tecnólogo</th><th>Fecha</th><th>Hora</th></tr></thead><tbody>' +
          BLO.slice(0, 8).map(function (b){ return '<tr><td>' + esc(optLabel('/admin/tecnologos/', b.tecnologo)) + '</td><td>' + esc(b.fecha) + '</td><td>' + esc(String(b.hora_inicio).slice(0,5)) + '–' + esc(String(b.hora_fin).slice(0,5)) + '</td></tr>'; }).join('') +
          '</tbody></table>';
      } else html += '<div class="mv-empty">Sin bloques disponibles próximos.</div>';
      body.innerHTML = html;
      var bk = body.querySelector('[data-back]'); if (bk) bk.addEventListener('click', function (){ renderOpticas(); });
    });
  }

  function cellVal(row, n){
    var f = (current.fields || []).filter(function (x){ return x.n === n; })[0];
    var v = row[n];
    if (f && f.src) return esc(optLabel(f.src, v));
    if (typeof v === 'boolean') return v ? 'Sí' : 'No';
    return esc(v == null ? '—' : v);
  }
  function renderList(){
    api.get(current.ep).then(function (r){
      if (!r.ok) { body.innerHTML = '<div class="mv-empty">No se pudo cargar (revisa que /api/admin/ esté registrado y que seas ADMIN).</div>'; return; }
      var list = Array.isArray(r.data) ? r.data : [];
      if (!list.length) { body.innerHTML = '<div class="mv-empty">Sin registros.</div>'; return; }
      var head = current.cols.map(function (c){ return '<th>' + c[1] + '</th>'; }).join('') + '<th></th>';
      var rows = list.map(function (row){
        var tds = current.cols.map(function (c){ return '<td>' + cellVal(row, c[0]) + '</td>'; }).join('');
        return '<tr>' + tds + '<td class="mv-ad-actions"><button class="edit" data-id="' + row.id + '"><i class="bi bi-pencil"></i></button>' +
          (current.noCreate ? '' : '<button class="del" data-id="' + row.id + '"><i class="bi bi-trash"></i></button>') + '</td></tr>';
      }).join('');
      body.innerHTML = '<table class="mv-ad-table"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table>';
      body.querySelectorAll('.edit').forEach(function (b){ b.addEventListener('click', function (){ openModal(list.filter(function (x){ return String(x.id) === b.getAttribute('data-id'); })[0]); }); });
      body.querySelectorAll('.del').forEach(function (b){ b.addEventListener('click', function (){
        confirmBox(current.delMsg || '¿Eliminar este registro?').then(function (ok){
          if (!ok) return;
          api['delete'](current.ep + b.getAttribute('data-id') + '/').then(function (r){ if (r.ok) { toast('Eliminado.', 'success'); renderList(); } else toast('No se pudo eliminar.', 'error'); });
        });
      }); });
    });
  }
  function renderResumen(){
    Promise.all([api.get('/orders/operaciones/'), api.get('/orders/devoluciones/'), api.get('/appointments/citas/'), api.get('/store/productos/')]).then(function (res){
      var ORD = (res[0].ok && Array.isArray(res[0].data)) ? res[0].data : [];
      var DEV = (res[1].ok && Array.isArray(res[1].data)) ? res[1].data : [];
      var CIT = (res[2].ok && Array.isArray(res[2].data)) ? res[2].data : [];
      var PRO = (res[3].ok && Array.isArray(res[3].data)) ? res[3].data : [];
      var d = new Date(); var hoy = d.getFullYear() + '-' + (d.getMonth()+1<10?'0':'') + (d.getMonth()+1) + '-' + (d.getDate()<10?'0':'') + d.getDate();
      body.innerHTML = '<div class="mv-ad-stats">' +
        '<div class="mv-ad-stat"><div class="n">' + ORD.filter(function (o){ return ['PAGADA','EN_PREPARACION','LISTO_PARA_RETIRO','ENVIADA'].indexOf(o.estado) !== -1; }).length + '</div><div class="l">Pedidos activos</div></div>' +
        '<div class="mv-ad-stat"><div class="n">' + DEV.filter(function (x){ return x.estado === 'PENDIENTE'; }).length + '</div><div class="l">Devoluciones</div></div>' +
        '<div class="mv-ad-stat"><div class="n">' + CIT.filter(function (c){ return c.bloque_fecha === hoy; }).length + '</div><div class="l">Citas hoy</div></div>' +
        '<div class="mv-ad-stat"><div class="n">' + PRO.filter(function (p){ return p.stock_bajo === true; }).length + '</div><div class="l">Stock bajo</div></div>' +
        '</div>';
    });
  }

  function openModal(obj){
    var isEdit = !!obj;
    var html = '<h3>' + (isEdit ? 'Editar' : 'Nuevo') + ' ' + current.label + '</h3>';
    (current.fields || []).forEach(function (f){
      var v = obj ? obj[f.n] : '';
      html += '<div class="mv-ad-field"><label>' + f.l + '</label>';
      if (f.t === 'select') {
        html += '<select data-f="' + f.n + '"><option value="">—</option>' + (cacheOpts[f.src] || []).map(function (o){ return '<option value="' + o.id + '"' + (String(v) === String(o.id) ? ' selected' : '') + '>' + esc(o.nombre || o.email || o.id) + '</option>'; }).join('') + '</select>';
      } else if (f.t === 'choice') {
        html += '<select data-f="' + f.n + '">' + f.opts.map(function (o){ return '<option value="' + o[0] + '"' + (v === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select>';
      } else if (f.t === 'check') {
        html += '<input type="checkbox" data-f="' + f.n + '"' + (v ? ' checked' : '') + ' style="width:auto;" />';
      } else if (f.t === 'password') {
        html += '<input type="password" data-f="' + f.n + '" placeholder="' + (isEdit ? 'Dejar en blanco para no cambiar' : 'Mínimo 8 caracteres') + '" />';
      } else if (f.t === 'region') {
        html += '<select data-f="' + f.n + '"><option value="">—</option></select>';
      } else if (f.t === 'comuna') {
        html += '<select data-f="' + f.n + '" disabled><option value="">—</option></select>';
      } else if (f.t === 'file') {
        html += '<input type="file" accept="image/*" data-f="' + f.n + '" />';
        if (obj && obj.imagen_url) html += '<div style="margin-top:.5rem;"><img src="' + obj.imagen_url + '" style="max-width:96px;border-radius:10px;border:1px solid var(--border-color);" /></div>';
      } else if (f.t === 'text') {
        html += '<textarea data-f="' + f.n + '" rows="2">' + esc(v || '') + '</textarea>';
      } else {
        html += '<input type="' + f.t + '" data-f="' + f.n + '" value="' + esc(v == null ? '' : v) + '" />';
      }
      html += '</div>';
    });
    html += '<div class="mv-ad-foot"><button class="btn btn-outline-mv btn-sm" id="ad-cancel">Cancelar</button><button class="btn btn-cta" id="ad-save">Guardar</button></div>';
    modalCard.innerHTML = html;

    // Cascada Region -> Comuna (usuarios cliente)
    var regSel = modalCard.querySelector('[data-f="region"]');
    var comSel = modalCard.querySelector('[data-f="comuna"]');
    if (regSel && comSel) {
      regSel.innerHTML = '<option value="">—</option>' + Object.keys(REG).map(function (r){ return '<option value="' + r + '">' + r + '</option>'; }).join('');
      var fillCom = function (){
        comSel.innerHTML = '<option value="">—</option>' + (REG[regSel.value] || []).map(function (c){ return '<option value="' + c + '">' + c + '</option>'; }).join('');
        comSel.disabled = !regSel.value;
      };
      regSel.addEventListener('change', fillCom);
      if (obj && obj.region) { regSel.value = obj.region; fillCom(); if (obj.comuna) comSel.value = obj.comuna; }
    }

    modal.classList.add('open');
    modalCard.querySelector('#ad-cancel').addEventListener('click', closeModal);
    modalCard.querySelector('#ad-save').addEventListener('click', function (){
      var payload = {};
      (current.fields || []).forEach(function (f){
        var el = modalCard.querySelector('[data-f="' + f.n + '"]');
        if (!el) return;
        var val = (f.t === 'check') ? el.checked : el.value;
        if (f.t === 'number') val = val === '' ? null : Number(val);
        if (f.t === 'select' && val === '') val = null;
        payload[f.n] = val;
      });
      var fileFields = (current.fields || []).filter(function (f){ return f.t === 'file'; });
      Promise.all(fileFields.map(function (f){
        return new Promise(function (res){
          var el = modalCard.querySelector('[data-f="' + f.n + '"]');
          if (el && el.files && el.files[0]) {
            var fr = new FileReader();
            fr.onload = function (){ res([f.n, fr.result]); };
            fr.readAsDataURL(el.files[0]);
          } else res([f.n, null]);
        });
      })).then(function (pairs){
        pairs.forEach(function (pr){ if (pr[1]) payload[pr[0]] = pr[1]; });
        var prom = isEdit ? api.patch(current.ep + obj.id + '/', { body: payload }) : api.post(current.ep, { body: payload });
        prom.then(function (r){ if (r.ok) { toast('Guardado.', 'success'); closeModal(); renderList(); } else { toast((r.data && JSON.stringify(r.data)) || 'Error al guardar.', 'error'); } });
      });
    });
  }
  
  // Modal de confirmacion propio (reemplaza el confirm() nativo)
  function confirmBox(message) {
    return new Promise(function (resolve) {
      var ov = document.createElement('div');
      ov.className = 'mv-ad-modal open'; ov.style.zIndex = 2100;
      ov.innerHTML = '<div class="mv-ad-modal-card" style="max-width:430px;">' +
        '<h3 style="font-family:var(--font-head);font-weight:800;color:var(--lead-dark);margin:0 0 .6rem;">Confirmar acción</h3>' +
        '<p style="color:var(--lead-muted,#6B7280);margin:0 0 1.1rem;font-size:.92rem;">' + message + '</p>' +
        '<div class="mv-ad-foot"><button class="btn btn-outline-mv btn-sm" id="cf-no">Cancelar</button>' +
        '<button class="btn" id="cf-yes" style="background:var(--danger,#dc2626);color:#fff;">Sí, eliminar</button></div></div>';
      document.body.appendChild(ov);
      function done(v){ if (ov.parentNode) ov.parentNode.removeChild(ov); resolve(v); }
      ov.querySelector('#cf-no').addEventListener('click', function (){ done(false); });
      ov.querySelector('#cf-yes').addEventListener('click', function (){ done(true); });
      ov.addEventListener('click', function (e){ if (e.target === ov) done(false); });
    });
  }
  function closeModal(){ modal.classList.remove('open'); }
  modal.addEventListener('click', function (e){ if (e.target === modal) closeModal(); });
  btnNew.addEventListener('click', function (){ openModal(null); });

  MV.me().then(function (u){
    if (!u || (u.role !== 'ADMIN' && !u.is_superuser)) { location.replace('/'); return; }
    buildSide(); go('opticas');
  });
})();