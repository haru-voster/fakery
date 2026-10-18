from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_alter_transaction_kind_alter_transaction_reference"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="CryptoDeposit", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
        ("tx_hash", models.CharField(max_length=66, unique=True)),
        ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("failed", "Failed")], default="pending", max_length=12)),
        ("note", models.CharField(blank=True, max_length=240)),
        ("created", models.DateTimeField(auto_now_add=True)),
        ("confirmed_at", models.DateTimeField(blank=True, null=True)),
        ("ledger_transaction", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="crypto_deposit", to="accounts.transaction")),
        ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="crypto_deposits", to=settings.AUTH_USER_MODEL)),
    ], options={"ordering": ["-created"]})]
