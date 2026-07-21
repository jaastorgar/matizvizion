from django.urls import path

from .views import WebpayCreateView, WebpayReturnView


app_name = 'payments'


urlpatterns = [
    path(
        'webpay/create/',
        WebpayCreateView.as_view(),
        name='webpay-create'
    ),
    path(
        'webpay/return/',
        WebpayReturnView.as_view(),
        name='webpay-return'
    ),
]