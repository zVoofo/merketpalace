from django.urls import path
from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.panel_dashboard, name='dashboard'),
    path('moderation/', views.panel_moderation, name='moderation'),
    path('moderation/<int:pk>/approve/', views.panel_approve, name='approve'),
    path('moderation/<int:pk>/reject/', views.panel_reject, name='reject'),
    path('users/', views.panel_users, name='users'),
    path('users/<int:pk>/verify/', views.panel_verify_user, name='verify_user'),
]
