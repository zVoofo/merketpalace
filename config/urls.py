from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from catalog.views import home
from accounts.views import serve_stored_file

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('files/<path:file_id>/', serve_stored_file, name='stored_file'),
    path('accounts/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('listing/', include('listings.urls')),
    path('seller/', include('listings.seller_urls')),
    path('cart/', include('orders.cart_urls')),
    path('orders/', include('orders.urls')),
    path('messages/', include('chat.urls')),
    path('panel/', include('accounts.panel_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

# Медиа с диска (если когда-то использовался FileSystemStorage)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'MarketPlace — Админ'
admin.site.site_title = 'MarketPlace'
