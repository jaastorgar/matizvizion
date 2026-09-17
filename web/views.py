from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

def home(request):
    return render(request, 'modules/web/home.html')

def login_page(request):
    return render(request, 'modules/auth/login.html')

def register_page(request):
    return render(request, 'modules/auth/register.html')

def catalogo(request):
    return render(request, 'modules/store/catalogo.html')

def carrito(request):
    return render(request, 'modules/orders/cart.html')

def checkout(request):
    return render(request, 'modules/orders/checkout.html')

@csrf_exempt
def pago_retorno(request):
    token_ws = request.GET.get('token_ws') or request.POST.get('token_ws') or ''
    return render(request, 'modules/payments/return.html', {'token_ws': token_ws})

def reserva(request):
    return render(request, 'modules/appointments/reserva.html')

def dashboard(request):
    return render(request, 'modules/admin/dashboard.html')

def perfil(request):
    # Compatibilidad: /perfil/ ahora redirige a la pagina propia de datos
    return redirect('web:mis_datos')

def seguimiento(request):
    return render(request, 'modules/orders/seguimiento.html')

def seguir(request):
    return render(request, 'modules/orders/seguir.html')

def mis_compras(request):
    return render(request, 'modules/orders/mis_compras.html')

def mis_citas(request):
    return render(request, 'modules/appointments/mis_citas.html')

def mis_datos(request):
    return render(request, 'modules/auth/mis_datos.html')

def recuperar(request):
    return render(request, 'modules/auth/recuperar.html')

def reset_password(request):
    return render(request, 'modules/auth/reset_password.html')

def administracion(request):
    # Sin blindaje server-side: el login es por JWT (stateless), asi que en una
    # vista de template request.user seria anonimo (no hay sesion de Django).
    # El blindaje REAL lo hacen administracion.js (via /api/accounts/me/ con
    # Bearer) y el endpoint /api/admin/kpis/ (IsAdminUserCustom). Mismo patron
    # que /panel/. Servir el template siempre evita el redirect falso a /login/.
    return render(request, 'modules/admin/administracion.html')

def inicio(request):
    return render(request, 'modules/admin/inicio.html')
def mi_perfil(request):
    from django.shortcuts import render
    return render(request, 'modules/admin/perfil_staff.html')

def metricas(request):
    return render(request, 'modules/admin/metricas.html')

def terminos(request):
    return render(request, 'modules/web/terminos.html')


def privacidad(request):
    return render(request, 'modules/web/privacidad.html')