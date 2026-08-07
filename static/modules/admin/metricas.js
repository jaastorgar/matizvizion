(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.me) return;
  var api = MV.api;
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  var charts = {};
  var PAGADAS = ['PAGADA', 'EN_PREPARACION', 'LISTO_PARA_RETIRO', 'ENVIADA', 'ENTREGADA'];
  function pad(n){ return n < 10 ? '0' + n : '' + n; }
  function iso(d){ return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()); }
  function fechaDe(s){ var m = String(s).slice(0,10).split('-'); return m[0] + '-' + m[1] + '-' + m[2]; }

  function destroy(){ Object.keys(charts).forEach(function (k){ if (charts[k]) { charts[k].destroy(); delete charts[k]; } }); }

  function render(ORD, CIT, PRO, DEV, desde, hasta){
    var ord = ORD.filter(function (o){ var f = fechaDe(o.creado_en); return f >= desde && f <= hasta; });
    var cit = CIT.filter(function (c){ return c.bloque_fecha >= desde && c.bloque_fecha <= hasta; });
    var ventas = ord.filter(function (o){ return PAGADAS.indexOf(o.estado) !== -1; });
    var total = ventas.reduce(function (s, o){ return s + Number(o.total || 0); }, 0);
    var ticket = ventas.length ? total / ventas.length : 0;
    var citCompl = cit.filter(function (c){ return c.estado === 'COMPLETADA'; }).length;
    var devPend = DEV.filter(function (d){ return d.estado === 'PENDIENTE'; }).length;
    var stockBajo = PRO.filter(function (p){ return p.stock_bajo === true; }).length;

    document.getElementById('bi-kpis').innerHTML =
      '<div class="mv-bi-kpi"><div class="n">' + money(total) + '</div><div class="l"><i class="bi bi-cash-coin"></i> Ventas totales</div></div>' +
      '<div class="mv-bi-kpi"><div class="n">' + ventas.length + '</div><div class="l"><i class="bi bi-bag-check"></i> Órdenes</div></div>' +
      '<div class="mv-bi-kpi"><div class="n">' + money(ticket) + '</div><div class="l"><i class="bi bi-receipt"></i> Ticket promedio</div></div>' +
      '<div class="mv-bi-kpi"><div class="n">' + citCompl + '</div><div class="l"><i class="bi bi-calendar2-check"></i> Citas completadas</div></div>' +
      '<div class="mv-bi-kpi"><div class="n">' + devPend + '</div><div class="l"><i class="bi bi-arrow-return-left"></i> Devoluciones</div></div>' +
      '<div class="mv-bi-kpi"><div class="n">' + stockBajo + '</div><div class="l"><i class="bi bi-exclamation-triangle"></i> Stock bajo</div></div>';

    destroy();
    // Ventas por dia
    var porDia = {};
    ventas.forEach(function (o){ var f = fechaDe(o.creado_en); porDia[f] = (porDia[f] || 0) + Number(o.total || 0); });
    var dias = Object.keys(porDia).sort();
    charts.ventas = new Chart(document.getElementById('ch-ventas'), {
      type: 'line',
      data: { labels: dias, datasets: [{ label: 'Ventas', data: dias.map(function (d){ return porDia[d]; }), borderColor: '#10B981', backgroundColor: 'rgba(16,185,129,.15)', fill: true, tension: .3 }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
    // Top productos
    var porProd = {};
    ventas.forEach(function (o){ (o.items || []).forEach(function (it){ porProd[it.producto_nombre] = (porProd[it.producto_nombre] || 0) + it.cantidad; }); });
    var top = Object.keys(porProd).map(function (k){ return { n: k, c: porProd[k] }; }).sort(function (a, b){ return b.c - a.c; }).slice(0, 5);
    charts.top = new Chart(document.getElementById('ch-top'), {
      type: 'bar',
      data: { labels: top.map(function (t){ return t.n; }), datasets: [{ label: 'Unidades', data: top.map(function (t){ return t.c; }), backgroundColor: '#065F46' }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
    // Ordenes por estado
    var porEstado = {};
    ord.forEach(function (o){ porEstado[o.estado] = (porEstado[o.estado] || 0) + 1; });
    charts.ordenes = new Chart(document.getElementById('ch-ordenes'), {
      type: 'doughnut',
      data: { labels: Object.keys(porEstado), datasets: [{ data: Object.keys(porEstado).map(function (k){ return porEstado[k]; }), backgroundColor: ['#10B981','#F59E0B','#3B82F6','#065F46','#DC2626','#6B7280','#8B5CF6'] }] },
      options: { responsive: true }
    });
    // Citas por estado
    var porCita = {};
    cit.forEach(function (c){ porCita[c.estado] = (porCita[c.estado] || 0) + 1; });
    charts.citas = new Chart(document.getElementById('ch-citas'), {
      type: 'doughnut',
      data: { labels: Object.keys(porCita), datasets: [{ data: Object.keys(porCita).map(function (k){ return porCita[k]; }), backgroundColor: ['#3B82F6','#10B981','#DC2626','#6B7280','#F59E0B'] }] },
      options: { responsive: true }
    });
  }

  function load(){
    var desde = document.getElementById('bi-desde').value;
    var hasta = document.getElementById('bi-hasta').value;
    Promise.all([api.get('/orders/ordenes/'), api.get('/appointments/citas/'), api.get('/store/productos/'), api.get('/orders/devoluciones/')]).then(function (res){
      var ORD = (res[0].ok && Array.isArray(res[0].data)) ? res[0].data : [];
      var CIT = (res[1].ok && Array.isArray(res[1].data)) ? res[1].data : [];
      var PRO = (res[2].ok && Array.isArray(res[2].data)) ? res[2].data : [];
      var DEV = (res[3].ok && Array.isArray(res[3].data)) ? res[3].data : [];
      render(ORD, CIT, PRO, DEV, desde, hasta);
    });
  }

  MV.me().then(function (u){
    if (!u || (u.role !== 'ADMIN' && !u.is_superuser)) { location.replace('/'); return; }
    var d = new Date();
    var desde = new Date(d.getFullYear(), d.getMonth(), d.getDate() - 30);
    document.getElementById('bi-desde').value = iso(desde);
    document.getElementById('bi-hasta').value = iso(d);
    document.getElementById('bi-apply').addEventListener('click', load);
    load();
  });
})();