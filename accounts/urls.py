from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cabinet/', views.cabinet_view, name='cabinet'),
    path('profile/', views.profile_view, name='profile'),
    path('my-requests/', views.my_requests_view, name='my_requests'),
    path('user/<str:username>/', views.public_profile_view, name='public_profile'),
    path('notifications/read/', views.notifications_read, name='notifications_read'),
    path('notifications/<int:pk>/open/', views.notification_open, name='notification_open'),
    path('notifications/<int:pk>/delete/', views.notifications_delete, name='notifications_delete'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('social/vk/callback/', views.vk_callback, name='vk_callback'),
    path('social/<str:provider>/', views.social_login, name='social_login'),
]
