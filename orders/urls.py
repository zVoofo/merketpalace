from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='list'),
    path('<int:pk>/', views.order_detail, name='detail'),
    path('<int:pk>/ship/', views.order_ship, name='ship'),
    path('<int:pk>/complete/', views.order_complete, name='complete'),
    path('checkout/', views.checkout_view, name='checkout'),
]
