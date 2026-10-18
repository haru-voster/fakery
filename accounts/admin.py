from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import Profile, KYCDocument, Transaction, SupportMessage

@admin.register(Profile)
class P(admin.ModelAdmin):
    list_display = ("user", "phone", "country", "kyc_status")
    list_filter = ("kyc_status", "country")
    search_fields = ("user__username", "user__email", "phone")

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("created", "user", "kind", "amount", "status", "reference")
    list_filter = ("kind", "status", "created")
    search_fields = ("user__username", "user__email", "reference")
    list_select_related = ("user",)
    date_hierarchy = "created"
    ordering = ("-created",)
    actions = ("mark_completed", "mark_failed")

    @admin.action(description="Mark selected transactions completed (verify payment first)")
    def mark_completed(self, request, queryset):
        queryset.update(status="completed")

    @admin.action(description="Mark selected transactions failed")
    def mark_failed(self, request, queryset):
        queryset.update(status="failed")

admin.site.register(KYCDocument)

@admin.register(SupportMessage)
class SM(admin.ModelAdmin):
    list_display = ("name", "phone", "created", "handled")
    list_filter = ("handled",)
    search_fields = ("name", "phone", "message")


# Make registered customer accounts visible and searchable in Django Admin.
User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, DjangoUserAdmin)
