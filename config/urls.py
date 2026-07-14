from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from catalog.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
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
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

admin.site.site_header = 'MarketPlace — Админ'
admin.site.site_title = 'MarketPlace'
