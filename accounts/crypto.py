import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import requests
from .models import CryptoDeposit, Transaction

log = logging.getLogger(__name__)
# Official Tether USD (USDT) token contract on Ethereum mainnet; 6 decimal places.
USDT_CONTRACT = "0xdac17f958d2ee523a2206206994597c13d831ec7"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def _rpc(method, params):
    url = settings.ETHEREUM_RPC_URL
    if not url:
        raise RuntimeError("ETHEREUM_RPC_URL is not configured")
    response = requests.post(url, json={"jsonrpc":"2.0", "id":1, "method":method, "params":params}, timeout=15)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error") or "result" not in payload:
        raise RuntimeError("Ethereum RPC returned an error")
    return payload["result"]

def verify_crypto_deposit(deposit_id):
    """Verify token contract, recipient, amount, successful receipt and confirmations; credit once."""
    with transaction.atomic():
        dep = CryptoDeposit.objects.select_for_update().select_related("user").get(pk=deposit_id)
        if dep.status in ("confirmed", "failed"):
            return dep.status
        wallet = settings.USDT_ERC20_RECEIVING_ADDRESS.lower().strip()
        if not wallet or not settings.ETHEREUM_RPC_URL:
            return "pending"
        if len(wallet) != 42 or not wallet.startswith("0x"):
            dep.note = "Receiving wallet address is not configured correctly."
            dep.save(update_fields=["note"]); return "pending"
        receipt = _rpc("eth_getTransactionReceipt", [dep.tx_hash])
        if receipt is None:
            dep.note = "Waiting for the transaction to appear on Ethereum."
            dep.save(update_fields=["note"]); return "pending"
        if int(receipt.get("status", "0x0"), 16) != 1:
            dep.status = "failed"; dep.note = "The Ethereum transaction failed."
            dep.save(update_fields=["status", "note"]); return "failed"
        matching = []
        for log_entry in receipt.get("logs", []):
            topics = log_entry.get("topics", [])
            if log_entry.get("address", "").lower() != USDT_CONTRACT or len(topics) < 3:
                continue
            if topics[0].lower() != TRANSFER_TOPIC:
                continue
            recipient = "0x" + topics[2][-40:].lower()
            if recipient != wallet:
                continue
            raw = int(log_entry.get("data", "0x0"), 16)
            matching.append((Decimal(raw) / Decimal(10**6), log_entry.get("logIndex", "0x0")))
        if not matching:
            dep.status = "failed"; dep.note = "No incoming Ethereum-mainnet USDT transfer to the configured wallet was found in this transaction."
            dep.save(update_fields=["status", "note"]); return "failed"
        expected = dep.amount.quantize(Decimal("0.01"))
        amount_match = next((x for x in matching if x[0] == expected), None)
        if amount_match is None:
            dep.status = "failed"; dep.note = "The verified USDT amount does not match the submitted deposit amount."
            dep.save(update_fields=["status", "note"]); return "failed"
        latest_hex = _rpc("eth_blockNumber", [])
        latest = int(latest_hex, 16); block = int(receipt["blockNumber"], 16)
        confirmations = max(0, latest - block + 1)
        required = max(1, int(settings.USDT_ERC20_CONFIRMATIONS))
        if confirmations < required:
            dep.note = f"Ethereum confirmations: {confirmations}/{required}."
            dep.save(update_fields=["note"]); return "pending"
        # Locking the deposit and its unique ledger link prevents duplicate credits on retries.
        ledger = Transaction.objects.create(user=dep.user, kind="deposit", amount=expected, status="completed",
            reference=f"USDT ERC20 Ethereum: {dep.tx_hash}")
        dep.status = "confirmed"; dep.note = f"Confirmed with {confirmations} Ethereum confirmations."
        dep.confirmed_at = timezone.now(); dep.ledger_transaction = ledger
        dep.save(update_fields=["status", "note", "confirmed_at", "ledger_transaction"])
        return "confirmed"
