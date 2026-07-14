from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization, ActivityLog, Wallet, WalletTransaction, SocialAccount, EmailVerificationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'active_role', 'is_verified', 'is_staff')
    list_filter = ('active_role', 'is_verified', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('MarketPlace', {'fields': ('phone', 'avatar', 'active_role', 'is_verified', 'phone_verified')}),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'inn', 'is_verified')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'tx_type', 'amount', 'description', 'created_at')


admin.site.register(SocialAccount)
admin.site.register(EmailVerificationCode)
admin.site.register(ActivityLog)
