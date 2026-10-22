import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django_countries.fields import CountryField


def new_code():
    return secrets.token_hex(4).upper()


class Profile(models.Model):
    KYC = [
        ("none", "Not submitted"),
        ("pending", "Pending review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=20)
    country = CountryField()
    referral_code = models.CharField(
        max_length=10,
        unique=True,
        default=new_code,
    )
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    kyc_status = models.CharField(
        max_length=10,
        choices=KYC,
        default="none",
    )

    def __str__(self):
        return self.user.username


class KYCDocument(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    id_type = models.CharField(
        max_length=20,
        choices=[
            ("national_id", "National ID"),
            ("passport", "Passport"),
            ("license", "Driving licence"),
        ],
    )
    file = models.FileField(upload_to="kyc/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.id_type}"


class Transaction(models.Model):
    """Ledger entries for confirmed financial transactions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )
    kind = models.CharField(
        max_length=14,
        choices=[
            ("deposit", "Deposit"),
            ("withdrawal", "Withdrawal"),
            ("transfer_out", "Transfer sent"),
            ("transfer_in", "Transfer received"),
        ],
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    reference = models.CharField(max_length=160, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.username} - {self.kind} - {self.amount}"


class SupportMessage(models.Model):
    name = models.CharField(max_length=60)
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Support message from {self.name}"


class CryptoDeposit(models.Model):
    """Customer-submitted USDT TRC-20 deposit awaiting verification."""

    NETWORK = "TRON_MAINNET_TRC20"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="crypto_deposits",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    # TRON transaction IDs are normally 64 hexadecimal characters.
    tx_hash = models.CharField(max_length=66, unique=True)
       

    status = models.CharField(
        max_length=12,
        choices=[
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    note = models.CharField(max_length=240, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    ledger_transaction = models.OneToOneField(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="crypto_deposit",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.username}: {self.amount} USDT TRC-20"


class InvestmentPlan(models.Model):
    name = models.CharField(max_length=80, unique=True)
    min_amount = models.DecimalField(max_digits=14, decimal_places=2)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["min_amount", "name"]

    def clean(self):
        if self.min_amount < 0:
            raise ValidationError({
                "min_amount": "The minimum amount cannot be negative."
            })

        if self.max_amount < self.min_amount:
            raise ValidationError({
                "max_amount": "The maximum must be at least the minimum."
            })

    def __str__(self):
        return self.name


class InvestmentOrder(models.Model):
    STATUS = [
        ("awaiting_payment", "Awaiting payment"),
        ("pending_verification", "Pending verification"),
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("payment_failed", "Payment failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investment_orders",
    )
    plan = models.ForeignKey(
        InvestmentPlan,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=24,
        choices=STATUS,
        default="awaiting_payment",
    )
    payment = models.OneToOneField(
        CryptoDeposit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="investment_order",
    )
    created = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({
                "amount": "The investment amount must be greater than zero."
            })

        if self.plan_id:
            if not (
                self.plan.min_amount
                <= self.amount
                <= self.plan.max_amount
            ):
                raise ValidationError({
                    "amount": (
                        "The amount must be within the selected plan's "
                        "minimum and maximum limits."
                    )
                })

    def __str__(self):
        return (
            f"{self.user.username} - {self.plan.name} "
            f"- {self.amount} USDT"
        )