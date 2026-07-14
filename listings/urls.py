from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('create/', views.listing_create, name='create'),
    path('<int:pk>/edit/', views.listing_edit, name='edit'),
    path('<slug:slug>/review/', views.review_create, name='review'),
    path('<slug:slug>/', views.listing_detail, name='detail'),
]
