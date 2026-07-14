from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.catalog_index, name='index'),
    path('preview/', views.search_preview, name='search_preview'),
    path('looking/', views.looking_board, name='looking'),
    path('looking/<int:pk>/respond/', views.respond_to_search, name='respond'),
    path('looking/<int:pk>/decline/', views.decline_search_offer, name='decline_offer'),
    path('search-request/', views.search_request_view, name='search_request'),
]
