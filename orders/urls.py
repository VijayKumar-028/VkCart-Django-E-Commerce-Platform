from django.urls import path

from . import views

urlpatterns=[
    path('place_order/', views.place_order, name='place_order'),
    path('payments/', views.payments, name='payments'),
    path('order_complete/', views.order_complete, name='order_complete'),
    path(
    'create-paypal-order/',
    views.create_paypal_order,
    name='create_paypal_order'
),
path(
    'capture-paypal-order/',
    views.capture_paypal_order,
    name='capture_paypal_order'
),
]