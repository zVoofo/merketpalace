from django.contrib import admin
from .models import Category, Brand, Attribute, CarMake, CarModel, SearchQuery, SearchRequest


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'sort_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(Attribute)
admin.site.register(CarMake)
admin.site.register(CarModel)
admin.site.register(SearchQuery)
admin.site.register(SearchRequest)
