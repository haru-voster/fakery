from django.core.management.base import BaseCommand
from accounts.models import CryptoDeposit
from accounts.crypto import verify_crypto_deposit

class Command(BaseCommand):
    help = "Check pending Ethereum ERC-20 USDT deposit submissions and credit confirmed transfers."
    def handle(self, *args, **options):
        ids = list(CryptoDeposit.objects.filter(status="pending").values_list("id", flat=True)[:500])
        for pk in ids:
            try:
                status = verify_crypto_deposit(pk)
                self.stdout.write(f"Deposit {pk}: {status}")
            except Exception as exc:
                self.stderr.write(f"Deposit {pk}: temporary verification error ({type(exc).__name__})")
