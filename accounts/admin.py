
from decimal import Decimal

from django.contrib import admin, messages
from django.db import transaction as dbtx
from django.utils import timezone

from .models import (
    Profile,
    KYCDocument,
    Transaction,
    SupportMessage,
    CryptoDeposit,
)


@admin.register(Profile)
class P(admin.ModelAdmin):
    list_display = ("user", "phone", "country", "kyc_status")
    list_filter = ("kyc_status", "country")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "created", "user", "kind", "amount", "status", "reference"
    )
    list_filter = ("kind", "status", "created")
    search_fields = ("user__username", "user__email", "reference")
    list_select_related = ("user",)
    date_hierarchy = "created"
    ordering = ("-created",)
    actions = ("mark_completed", "mark_failed")

    @admin.action(description="Mark selected transactions completed")
    def mark_completed(self, request, queryset):
        # Ledger transactions should only be completed after the
        # underlying payment or transfer has been verified.
        updated = queryset.filter(status="pending").update(
            status="completed"
        )
        self.message_user(
            request,
            f"{updated} pending transaction(s) marked completed.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Mark selected transactions failed")
    def mark_failed(self, request, queryset):
        updated = queryset.filter(status="pending").update(status="failed")
        self.message_user(
            request,
            f"{updated} pending transaction(s) marked failed.",
            level=messages.WARNING,
        )


admin.site.register(KYCDocument)


@admin.register(SupportMessage)
class SM(admin.ModelAdmin):
    list_display = ("name", "phone", "created", "handled")
    list_filter = ("handled",)
    search_fields = ("name", "phone", "message")


@admin.register(CryptoDeposit)
class CryptoDepositAdmin(admin.ModelAdmin):
    list_display = (
        "created",
        "user",
        "amount",
        "tx_hash",
        "status",
        "confirmed_at",
    )
    list_filter = ("status", "created")
    search_fields = ("user__username", "user__email", "tx_hash")
    readonly_fields = (
        "created",
        "confirmed_at",
        "ledger_transaction",
    )
    ordering = ("-created",)
    actions = ("confirm_verified_trc20_deposits", "mark_deposits_failed")

    @admin.action(
        description="Confirm selected TRC-20 deposits (verify on TRONSCAN first)"
    )
    def confirm_verified_trc20_deposits(self, request, queryset):
        confirmed_count = 0
        skipped_count = 0

        for selected in queryset:
            try:
                with dbtx.atomic():
                    # Lock the deposit to prevent simultaneous approvals.
                    deposit = (
                        CryptoDeposit.objects
                        .select_for_update()
                        .get(pk=selected.pk)
                    )

                    # Never credit an already-confirmed deposit.
                    if (
                        deposit.status != "pending"
                        or deposit.ledger_transaction_id is not None
                    ):
                        skipped_count += 1
                        continue

                    # IMPORTANT:
                    # Before selecting this action, verify the TxID on
                    # TRONSCAN. Confirm successful execution, official
                    # USDT TRC-20 contract, your receiving address,
                    # and the actual transferred amount.
                    ledger_tx = Transaction.objects.create(
                        user=deposit.user,
                        kind="deposit",
                        amount=deposit.amount,
                        status="completed",
                        reference=f"TRC-20 USDT deposit: {deposit.tx_hash}",
                    )

                    deposit.status = "confirmed"
                    deposit.confirmed_at = timezone.now()
                    deposit.ledger_transaction = ledger_tx
                    deposit.note = "Manually verified by an administrator."
                    deposit.save(
                        update_fields=[
                            "status",
                            "confirmed_at",
                            "ledger_transaction",
                            "note",
                        ]
                    )

                    confirmed_count += 1

            except Exception:
                skipped_count += 1
                self.message_user(
                    request,
                    f"Could not approve deposit ID {selected.pk}. "
                    "Check the server logs.",
                    level=messages.ERROR,
                )

        if confirmed_count:
            self.message_user(
                request,
                f"{confirmed_count} deposit(s) confirmed and credited.",
                level=messages.SUCCESS,
            )

        if skipped_count:
            self.message_user(
                request,
                f"{skipped_count} deposit(s) skipped or could not be approved.",
                level=messages.WARNING,
            )

    @admin.action(description="Mark selected pending deposits failed")
    def mark_deposits_failed(self, request, queryset):
        updated = queryset.filter(status="pending").update(
            status="failed",
            note="Marked failed by an administrator.",
        )
        self.message_user(
            request,
            f"{updated} pending deposit(s) marked failed.",
            level=messages.WARNING,
        )
