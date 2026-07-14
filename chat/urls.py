from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.conversation_list, name='index'),
    path('support/', views.support_chat, name='support'),
    path('start/<int:listing_id>/', views.conversation_start, name='start'),
    path('message/<int:pk>/edit/', views.message_edit, name='message_edit'),
    path('message/<int:pk>/delete/', views.message_delete, name='message_delete'),
    path('<int:pk>/', views.conversation_detail, name='detail'),
]
