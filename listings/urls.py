from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('create/', views.listing_create, name='create'),
    path('<int:pk>/edit/', views.listing_edit, name='edit'),
    path('<int:pk>/unpublish/', views.listing_unpublish, name='unpublish'),
    path('<int:pk>/republish/', views.listing_republish, name='republish'),
    path('<int:pk>/delete/', views.listing_delete, name='delete'),
    path('<slug:slug>/review/', views.review_create, name='review'),
    path('<slug:slug>/', views.listing_detail, name='detail'),
]
