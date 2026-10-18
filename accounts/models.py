import secrets
from django.conf import settings
from django.db import models
from django_countries.fields import CountryField
def new_code(): return secrets.token_hex(4).upper()
class Profile(models.Model):
    KYC = [("none","Not submitted"),("pending","Pending review"),("approved","Approved"),("rejected","Rejected")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20)
    country = CountryField()
    referral_code = models.CharField(max_length=10, unique=True, default=new_code)
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)  # recorded only; no payout logic
    kyc_status = models.CharField(max_length=10, choices=KYC, default="none")
    def __str__(self): return self.user.username
class KYCDocument(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    id_type = models.CharField(max_length=20, choices=[("national_id","National ID"),("passport","Passport"),("license","Driving licence")])
    file = models.FileField(upload_to="kyc/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
class Transaction(models.Model):
    """Ledger entries are created by staff in the admin after a real payment is confirmed."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=14, choices=[("deposit","Deposit"),("withdrawal","Withdrawal"),("transfer_out","Transfer sent"),("transfer_in","Transfer received")])
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=[("pending","Pending"),("completed","Completed"),("failed","Failed")], default="pending")
    reference = models.CharField(max_length=160, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created"]
class SupportMessage(models.Model):
    name = models.CharField(max_length=60)
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(max_length=500)
    created = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)
    class Meta: ordering = ["-created"]


class CryptoDeposit(models.Model):
    """Customer-submitted ERC-20 USDT transfer awaiting on-chain verification."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="crypto_deposits")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    tx_hash = models.CharField(max_length=66, unique=True)
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("failed", "Failed")], default="pending")
    note = models.CharField(max_length=240, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    ledger_transaction = models.OneToOneField(Transaction, null=True, blank=True, on_delete=models.PROTECT, related_name="crypto_deposit")

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.username}: {self.amount} USDT ({self.status})"
