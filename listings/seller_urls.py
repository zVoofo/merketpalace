from django.urls import path
from . import views

app_name = 'seller'

urlpatterns = [
    path('', views.seller_dashboard, name='dashboard'),
    path('listings/', views.seller_listings, name='listings'),
    path('requests/', views.seller_looking_requests, name='requests'),
    path('reviews/', views.seller_reviews, name='reviews'),
]
