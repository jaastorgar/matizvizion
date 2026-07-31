(function () {
  'use strict';
  var MV = window.MV; if (!MV || !MV.api) { console.error('administracion.js: MV no disponible'); return; }
  var api = MV.api, auth = MV.auth, esc = MV.escape;
  var money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format;
  var charts = {};

  function destroyCharts() {
    Object.keys(charts).forEach(function (k) { if (charts[k]) { charts[k].destroy(); delete charts[k]; } });
  }

  function renderKpis(k) {
    var grid = document.getElementById('kpis-grid');
    var cards = [
      { label: 'Ventas totales', value: money(k.ventas_totales) },
      { label: 'Nº de órdenes', value: k.num_ordenes },
      { label: 'Ticket promedio', value: money(k.ticket_promedio) },
      { label: 'Citas completadas', value: k.citas_completadas },
      { label: 'Clientes nuevos', value: k.clientes_nuevos },
      { label: 'Clientes invitados', value: k.clientes_invitados },
      { label: 'Productos bajo stock', value: k.productos_bajo_stock },
    ];
    grid.innerHTML = cards.map(function (c) {
      return '<div class="mv-kpi-card"><div class="mv-kpi-value">' + esc(String(c.value)) + '</div><div class="mv-kpi-label">' + esc(c.label) + '</div></div>';
    }).join('');
  }

  function renderCharts(data) {
    destroyCharts();
    // Ventas por día (línea)
    var vd = data.ventas_por_dia || [];
    charts.ventas = new Chart(document.getElementById('chart-ventas'), {
      type: 'line',
      data: {
        labels: vd.map(function (v) { return v.dia; }),
        datasets: [{ label: 'Ventas ($)', data: vd.map(function (v) { return v.total; }), borderColor: '#10B981', backgroundColor: 'rgba(16,185,129,.15)', fill: true, tension: .3 }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
    // Top productos (barras)
    var tp = data.top_productos || [];
    charts.top = new Chart(document.getElementById('chart-top'), {
      type: 'bar',
      data: {
        labels: tp.map(function (t) { return t.nombre; }),
        datasets: [{ label: 'Cantidad vendida', data: tp.map(function (t) { return t.cantidad; }), backgroundColor: '#065F46' }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
    // Órdenes por estado (doughnut)
    var oe = data.ordenes_por_estado || [];
    charts.ordenes = new Chart(document.getElementById('chart-ordenes'), {
      type: 'doughnut',
      data: {
        labels: oe.map(function (o) { return o.estado; }),
        datasets: [{ data: oe.map(function (o) { return o.n; }), backgroundColor: ['#10B981', '#F59E0B', '#3B82F6', '#065F46', '#DC2626', '#6B7280', '#8B5CF6', '#EF4444'] }]
      },
      options: { responsive: true }
    });
    // Citas por estado (doughnut)
    var ce = data.citas_por_estado || [];
    charts.citas = new Chart(document.getElementById('chart-citas'), {
      type: 'doughnut',
      data: {
        labels: ce.map(function (c) { return c.estado; }),
        datasets: [{ data: ce.map(function (c) { return c.n; }), backgroundColor: ['#3B82F6', '#10B981', '#DC2626', '#6B7280', '#F59E0B'] }]
      },
      options: { responsive: true }
    });
  }

  function load() {
    var desde = document.getElementById('kpis-desde').value;
    var hasta = document.getElementById('kpis-hasta').value;
    var qs = '';
    if (desde) qs += 'desde=' + desde + '&';
    if (hasta) qs += 'hasta=' + hasta;
    api.get('/admin/kpis/' + (qs ? '?' + qs : '')).then(function (r) {
      if (!r.ok || !r.data) {
        document.getElementById('kpis-grid').innerHTML = '<div class="text-danger">No se pudieron cargar los KPIs. Verifica que seas ADMIN.</div>';
        return;
      }
      renderKpis(r.data.kpis);
      renderCharts(r.data);
    });
  }

  document.getElementById('kpis-apply').addEventListener('click', load);

  if (!auth.isAuthenticated()) { window.location.href = '/login/?next=/administracion/'; return; }
  api.get('/accounts/me/').then(function (r) {
    if (!r.ok || !r.data || (r.data.role !== 'ADMIN' && !r.data.is_superuser)) {
      document.getElementById('kpis-grid').innerHTML = '<div class="text-danger">⛔ Acceso denegado. Solo administradores.</div>';
      return;
    }
    load();
  });
})();