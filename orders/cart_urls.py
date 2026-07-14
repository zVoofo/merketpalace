from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_view, name='cart'),
    path('add/', views.cart_add, name='cart_add'),
    path('update/', views.cart_update, name='cart_update'),
    path('remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
]
