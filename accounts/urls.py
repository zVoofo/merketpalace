from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('notifications/read/', views.notifications_read, name='notifications_read'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('social/<str:provider>/', views.social_login, name='social_login'),
]
