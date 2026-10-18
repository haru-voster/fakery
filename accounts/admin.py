from django.contrib import admin
from .models import Profile, KYCDocument, Transaction, SupportMessage, CryptoDeposit

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


@admin.register(CryptoDeposit)
class CryptoDepositAdmin(admin.ModelAdmin):
    list_display = ("created", "user", "amount", "tx_hash", "status", "confirmed_at")
    list_filter = ("status", "created")
    search_fields = ("user__username", "user__email", "tx_hash")
    readonly_fields = ("created", "confirmed_at", "ledger_transaction", "note")
    ordering = ("-created",)
