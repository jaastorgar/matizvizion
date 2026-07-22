from django.shortcuts import render
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
    """
    Página de retorno de Webpay. Transbank redirige aqui el navegador del
    usuario con token_ws (por GET o POST). Solo renderiza la pagina; el
    commit real lo hace return.js contra /api/payments/webpay/return/.
    """
    token_ws = request.GET.get('token_ws') or request.POST.get('token_ws') or ''
    return render(request, 'modules/payments/return.html', {'token_ws': token_ws})