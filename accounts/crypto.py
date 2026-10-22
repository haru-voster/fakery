
import logging

from django.db import transaction

from .models import CryptoDeposit

log = logging.getLogger(__name__)


def verify_crypto_deposit(deposit_id):
    """
    Manual-review workflow for USDT TRC-20 deposits.

    This function does not contact Ethereum or TRON APIs and does
    not credit a user's account automatically. An administrator
    must verify the transaction on TRONSCAN before confirming it
    through Django Admin.
    """
    with transaction.atomic():
        deposit = (
            CryptoDeposit.objects
            .select_for_update()
            .get(pk=deposit_id)
        )

        # Do not modify deposits already reviewed.
        if deposit.status in ("confirmed", "failed"):
            return deposit.status

        deposit.note = (
            "Awaiting manual verification of the USDT TRC-20 "
            "transaction on TRON Mainnet by an administrator."
        )

        deposit.save(update_fields=["note"])

        log.info(
            "TRC-20 deposit %s is awaiting manual verification.",
            deposit.pk,
        )

        return "pending"
