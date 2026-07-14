from django.contrib import admin
from .models import Listing, ListingImage, ListingCarCompat, Review, ModerationQueue


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'price', 'quantity', 'status', 'views_count')
    list_filter = ('status', 'type', 'category')
    search_fields = ('title', 'sku')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ListingImageInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('listing', 'reviewer', 'rating', 'status')


@admin.register(ModerationQueue)
class ModerationQueueAdmin(admin.ModelAdmin):
    list_display = ('listing', 'status', 'created_at')
