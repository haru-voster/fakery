import random
import time
import requests

from decimal import Decimal
from decimal import Decimal
from django.utils import timezone
from .models import CryptoDeposit
from django.conf import settings as dj
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction as dbtx
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    SignupForm,
    CustomerLoginForm,
    KYCForm,
    SettingsForm,
    FundForm,
    WithdrawForm,
    TransferForm,
)
from .models import (
    Profile,
    Transaction,
    SupportMessage,
    CryptoDeposit,
    InvestmentPlan,
    InvestmentOrder,
)
from .notifications import notify_signup, notify_support


def signup(request):
    # Existing sessions should not create duplicate accounts.
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        expected = request.session.get("signup_challenge")
        form = SignupForm(request.POST, expected=expected)

        if form.is_valid():
            d = form.cleaned_data

            try:
                with dbtx.atomic():
                    user = get_user_model().objects.create_user(
                        username=d["username"].strip(),
                        email=d["email"].strip().lower(),
                        password=d["password1"],
                    )

                    ref = (
                        Profile.objects.filter(
                            referral_code=d["referral"].strip().upper()
                        ).first()
                        if d["referral"].strip()
                        else None
                    )

                    Profile.objects.create(
                        user=user,
                        phone=d["phone"],
                        country=d["country"],
                        referred_by=ref,
                    )

            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    "BlueRock account registration failed"
                )
                messages.error(
                    request,
                    "We could not create your account. Please check your "
                    "details or contact support if the problem continues.",
                )

            else:
                # A notification provider must never block account creation.
                try:
                    notify_signup(user)
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        "BlueRock signup notification failed"
                    )

                login(
                    request,
                    user,
                    backend="accounts.backends.EmailOrUsernameBackend",
                )

                request.session.pop("signup_challenge", None)
                messages.success(
                    request,
                    "Your account has been created successfully.",
                )

                return render(
                    request,
                    "accounts/signup_success.html",
                    {"redirect_seconds": 5},
                )

        # Rotate the security question after unsuccessful validation.
        a, b = random.randint(1, 9), random.randint(1, 9)
        request.session["signup_challenge"] = a + b
        form.fields["answer"].label = (
            f"Security question: What is {a} + {b}?"
        )
        form.data = form.data.copy()
        form.data["answer"] = ""

    else:
        a, b = random.randint(1, 9), random.randint(1, 9)
        request.session["signup_challenge"] = a + b
        form = SignupForm(expected=request.session["signup_challenge"])
        form.fields["answer"].label = (
            f"Security question: What is {a} + {b}?"
        )

    return render(request, "accounts/signup.html", {"form": form})


IN, OUT = ("deposit", "transfer_in"), ("withdrawal", "transfer_out")


def _totals(user):
    ok = Transaction.objects.filter(
        user=user,
        status="completed",
    )

    def total_for(kinds):
        return (
            ok.filter(kind__in=kinds).aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )

    return total_for(IN), total_for(OUT)



def _available(user):
    dep, wd = _totals(user)

    held = (
        Transaction.objects.filter(
            user=user,
            kind__in=OUT,
            status="pending",
        ).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )

    return dep - wd - held


def _investment_growth(user):
    """
    Calculate an illustrative 10% compound-growth projection
    for eligible confirmed deposits.

    This does not credit funds to the account ledger.
    """
    deposits = CryptoDeposit.objects.filter(
        user=user,
        status="confirmed",
        confirmed_at__isnull=False,
        ledger_transaction__isnull=False,
        ledger_transaction__status="completed",
    ).only("amount", "confirmed_at")

    principal_total = Decimal("0.00")
    value_total = Decimal("0.00")
    rate = Decimal("1.10")
    now = timezone.now()

    for deposit in deposits:
        completed_days = max(
            (now - deposit.confirmed_at).days,
            0,
        )

        principal = Decimal(str(deposit.amount))
        projected_value = principal * (rate ** completed_days)

        principal_total += principal
        value_total += projected_value

    principal_total = principal_total.quantize(Decimal("0.01"))
    value_total = value_total.quantize(Decimal("0.01"))

    return {
        "investment_growth": value_total - principal_total,
        "investment_value": value_total,
    }


class ThrottledLogin(LoginView):
    """Authenticate customers and send successful logins to the dashboard."""

    template_name = "accounts/login.html"
    authentication_form = CustomerLoginForm
    success_url = reverse_lazy("dashboard")
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Signed in successfully. Welcome back!",
        )
        return response

    def get_success_url(self):
        return str(self.success_url)

    def post(self, request, *a, **k):
        key = "lf:%s:%s" % (
            request.META.get("REMOTE_ADDR", ""),
            request.POST.get("username", "").lower(),
        )

        if cache.get(key, 0) >= 5:
            return render(
                request,
                self.template_name,
                {
                    "form": CustomerLoginForm(request),
                    "locked": True,
                },
                status=429,
            )

        resp = super().post(request, *a, **k)

        if request.user.is_authenticated:
            cache.delete(key)
        elif resp.status_code == 200:
            cache.set(key, cache.get(key, 0) + 1, 900)

        return resp


@login_required
def dashboard(request):
    # Staff-created accounts may not have a Profile yet.
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"phone": "", "country": "KE"},
    )

    if request.user.is_staff:
        users = get_user_model().objects.all().order_by("-date_joined")
        txs = Transaction.objects.select_related("user").all()[:100]

        pending_deposits = Transaction.objects.filter(
            kind="deposit",
            status="pending",
        )
        completed_deposits = Transaction.objects.filter(
            kind="deposit",
            status="completed",
        )

        pending_total = (
            pending_deposits.aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )
        completed_total = (
            completed_deposits.aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )

        return render(
            request,
            "accounts/admin_dashboard.html",
            {
                "page": "ov",
                "profile": profile,
                "users": users[:100],
                "txs": txs,
                "user_count": users.count(),
                "pending_count": pending_deposits.count(),
                "pending_total": pending_total,
                "completed_total": completed_total,
            },
        )


    dep, wd = _totals(request.user)
    growth = _investment_growth(request.user)

    return render(request, "accounts/dashboard.html", {
        "page": "ov",
        "profile": profile,
        "dep": dep,
        "wd": wd,
        "balance": dep - wd,
        "investment_growth": growth["investment_growth"],
        "investment_value": growth["investment_value"],
        "txs": Transaction.objects.filter(
            user=request.user
        )[:10],
    })



@login_required
def dashboard_status(request):
    """Return the signed-in customer's ledger totals for auto-refresh."""

    dep, wd = _totals(request.user)
    growth = _investment_growth(request.user)

    pending = list(
        CryptoDeposit.objects.filter(
            user=request.user,
            status="pending",
        )
        .order_by("-created")
        .values("id", "amount", "status", "note", "created")[:10]
    )

    latest = list(
        CryptoDeposit.objects.filter(user=request.user)
        .order_by("-created")
        .values("id", "status", "confirmed_at")[:10]
    )

    for item in pending:
        item["amount"] = str(item["amount"])
        item["created"] = (
            item["created"].isoformat() if item["created"] else None
        )

    for item in latest:
        item["confirmed_at"] = (
            item["confirmed_at"].isoformat()
            if item["confirmed_at"]
            else None
        )

    return JsonResponse({
        "deposits": str(dep),
        "withdrawals": str(wd),
        "balance": str(dep - wd),
        "investment_growth": str(growth["investment_growth"]),
        "investment_value": str(growth["investment_value"]),
        "pending_deposits": pending,
        "latest_deposits": latest,
        "server_time": timezone.now().isoformat(),
    })


@login_required
def settings_view(request):
    u, p = request.user, request.user.profile

    form = SettingsForm(
        request.POST or None,
        user=u,
        initial={"email": u.email, "phone": p.phone},
    )
    saved = False

    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        u.email = d["email"]
        p.phone = d["phone"]
        p.save(update_fields=["phone"])

        if d["new_password"]:
            u.set_password(d["new_password"])

        u.save()

        if d["new_password"]:
            update_session_auth_hash(request, u)
            send_mail(
                "Your password was changed",
                "If this wasn't you, reset your password immediately "
                "and contact support.",
                dj.DEFAULT_FROM_EMAIL,
                [u.email],
                fail_silently=True,
            )

        saved = True

    return render(
        request,
        "accounts/settings.html",
        {"page": "set", "form": form, "saved": saved},
    )


# ---------------------------------------------------------
# INVESTMENT PLANS
# Added without replacing your existing views.
# ---------------------------------------------------------

@login_required
def investment_plans(request):
    plans = InvestmentPlan.objects.filter(is_active=True)

    orders = (
        InvestmentOrder.objects.filter(user=request.user)
        .select_related("plan", "payment")
        .order_by("-created")[:20]
    )

    return render(
        request,
        "accounts/investment_plans.html",
        {
            "page": "plans",
            "plans": plans,
            "orders": orders,
        },
    )


@login_required
@require_POST
def buy_plan(request, plan_id):
    plan = InvestmentPlan.objects.filter(
        pk=plan_id,
        is_active=True,
    ).first()

    if not plan:
        messages.error(request, "This investment plan is unavailable.")
        return redirect("investment_plans")

    try:
        amount = Decimal(request.POST.get("amount", "").strip())
    except Exception:
        messages.error(request, "Enter a valid investment amount.")
        return redirect("investment_plans")

    if not amount.is_finite() or amount <= 0:
        messages.error(request, "Enter a valid investment amount.")
        return redirect("investment_plans")

    if amount < plan.min_amount or amount > plan.max_amount:
        messages.error(
            request,
            f"{plan.name} accepts amounts from "
            f"{plan.min_amount} to {plan.max_amount} USDT.",
        )
        return redirect("investment_plans")

    order = InvestmentOrder.objects.create(
        user=request.user,
        plan=plan,
        amount=amount,
        status="awaiting_payment",
    )

    messages.info(
        request,
        "Your order has been created. Complete payment using the "
        "deposit page and wait for blockchain verification.",
    )

    return redirect(f"{reverse('fund')}?order_id={order.pk}")


# ---------------------------------------------------------

# ---------------------------------------------------------

# ---------------------------------------------------------
# FUND ACCOUNT - TRON MAINNET (USDT TRC-20)
# Manual verification and administrator approval
# ---------------------------------------------------------

@login_required
def fund(request):
    """Accept USDT TRC-20 deposit submissions for manual review."""

    import logging
    import re

    from django import forms
    from django.db import IntegrityError

    logger = logging.getLogger(__name__)

    class TRC20DepositForm(forms.Form):
        amount = forms.DecimalField(
            label="Amount (USDT)",
            min_value=Decimal("1.00"),
            max_digits=12,
            decimal_places=2,
        )

        tx_hash = forms.CharField(
            label="TRON transaction ID (TxID)",
            min_length=64,
            max_length=64,
            widget=forms.TextInput(
                attrs={
                    "placeholder": "Enter your 64-character TRON TxID",
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
        )

        def clean_tx_hash(self):
            value = self.cleaned_data["tx_hash"].strip()

            if not re.fullmatch(r"[a-fA-F0-9]{64}", value):
                raise forms.ValidationError(
                    "Enter a valid 64-character TRON transaction ID "
                    "without the 0x prefix."
                )

            return value.lower()

    # Only the receiving address is required for manual verification.
    receiving_address = getattr(
        dj,
        "USDT_TRC20_RECEIVING_ADDRESS",
        "",
    ).strip()

    deposit_configured = bool(receiving_address)

    form = TRC20DepositForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        if not deposit_configured:
            messages.error(
                request,
                "USDT deposits are not configured. Please contact "
                "support. Do not send funds until the receiving "
                "address is displayed.",
            )

        else:
            try:
                # Save the deposit as pending. Do not credit the
                # user's balance at submission time.
                with dbtx.atomic():
                    deposit = CryptoDeposit.objects.create(
                        user=request.user,
                        amount=form.cleaned_data["amount"],
                        tx_hash=form.cleaned_data["tx_hash"],
                        status="pending",
                        note=(
                            "Awaiting manual verification of the "
                            "USDT TRC-20 transaction on TRON Mainnet."
                        ),
                    )

                # The current crypto.py records the pending review
                # note only; it does not verify blockchain data.
                from .crypto import verify_crypto_deposit

                verify_crypto_deposit(deposit.pk)

                messages.success(
                    request,
                    "Your deposit submission was received. It will "
                    "remain pending until an administrator verifies "
                    "the transaction and approves the deposit.",
                )

                return redirect("history")

            except IntegrityError:
                form.add_error(
                    "tx_hash",
                    "This transaction ID has already been submitted.",
                )

            except Exception:
                logger.exception(
                    "Error submitting TRC-20 deposit for user %s",
                    request.user.pk,
                )

                messages.error(
                    request,
                    "We could not submit your deposit right now. "
                    "Check your transaction history before trying "
                    "again, or contact support.",
                )

    return render(
        request,
        "accounts/fund.html",
        {
            "page": "fund",
            "form": form,
            "receiving_address": receiving_address,
            "deposit_configured": deposit_configured,
            "payment_network": "TRON Mainnet (TRC-20)",
        },
    )


@login_required
def withdraw(request):
    if request.user.profile.kyc_status != "approved":
        messages.error(
            request,
            "Verify your identity (KYC) before withdrawing.",
        )
        return redirect("kyc")

    form = WithdrawForm(
        request.POST or None,
        user=request.user,
        available=_available(request.user),
    )

    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data

        Transaction.objects.create(
            user=request.user,
            kind="withdrawal",
            amount=d["amount"],
            status="pending",
            reference=f"{d['method']}: {d['destination']}",
        )

        send_mail(
            "Withdrawal request received",
            f"We received your request to withdraw ${d['amount']} "
            f"via {d['method']}. If this wasn't you, reset your password now.",
            dj.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=True,
        )

        notify_support(
            request.user.username,
            request.user.profile.phone,
            f"withdrawal request ${d['amount']} via {d['method']}",
        )

        return redirect("history")

    return render(
        request,
        "accounts/withdraw.html",
        {
            "page": "wd",
            "form": form,
            "available": _available(request.user),
        },
    )


@login_required
def transfer(request):
    if request.user.profile.kyc_status != "approved":
        messages.error(
            request,
            "Verify your identity (KYC) before transferring.",
        )
        return redirect("kyc")

    with dbtx.atomic():
        Profile.objects.select_for_update().get(user=request.user)

        form = TransferForm(
            request.POST or None,
            user=request.user,
            available=_available(request.user),
        )

        if request.method == "POST" and form.is_valid():
            d = form.cleaned_data

            Transaction.objects.create(
                user=request.user,
                kind="transfer_out",
                amount=d["amount"],
                status="completed",
                reference=f"to {form.target.username}",
            )

            Transaction.objects.create(
                user=form.target,
                kind="transfer_in",
                amount=d["amount"],
                status="completed",
                reference=f"from {request.user.username}",
            )

            send_mail(
                "You received a transfer",
                f"{request.user.username} sent you ${d['amount']}.",
                dj.DEFAULT_FROM_EMAIL,
                [form.target.email],
                fail_silently=True,
            )

            return redirect("history")

    return render(
        request,
        "accounts/transfer.html",
        {"page": "tr", "form": form, "available": _available(request.user)},
    )


@login_required
def history(request):
    kind = request.GET.get("type", "")
    qs = Transaction.objects.filter(user=request.user)

    if kind in ("deposit", "withdrawal", "transfer_out", "transfer_in"):
        qs = qs.filter(kind=kind)

    crypto_deposits = (
        CryptoDeposit.objects.filter(user=request.user)[:100]
        if kind in ("", "deposit")
        else []
    )

    return render(
        request,
        "accounts/history.html",
        {
            "page": "tx",
            "txs": qs[:100],
            "kind": kind,
            "crypto_deposits": crypto_deposits,
        },
    )


@login_required
def kyc(request):
    form = KYCForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        doc = form.save(commit=False)
        doc.user = request.user
        doc.save()

        p = request.user.profile
        p.kyc_status = "pending"
        p.save(update_fields=["kyc_status"])

        return redirect("dashboard")

    return render(request, "accounts/kyc.html", {"form": form})


def prices(request):
    data = cache.get("prices")

    if data is None:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                timeout=8,
                params={
                    "ids": (
                        "bitcoin,ethereum,solana,ripple,avalanche-2,"
                        "shiba-inu,tether,aave"
                    ),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
            )
            r.raise_for_status()
            data = r.json()
            cache.set("prices", data, 60)

        except requests.RequestException:
            return JsonResponse(
                {"error": "price feed unavailable"},
                status=503,
            )

    return JsonResponse(data)


def home(request):
    return render(request, "accounts/home.html")


@require_POST
def support_message(request):
    now = time.time()

    if now - request.session.get("sm_t", 0) < 30:
        return JsonResponse(
            {"error": "Please wait a moment before sending another message."},
            status=429,
        )

    name = request.POST.get("name", "").strip()[:60]
    phone = request.POST.get("phone", "").strip()[:20]
    text = request.POST.get("message", "").strip()[:500]

    if not text or not name:
        return JsonResponse(
            {"error": "Name and message are required."},
            status=400,
        )

    SupportMessage.objects.create(
        name=name,
        phone=phone,
        message=text,
    )

    request.session["sm_t"] = now
    notify_support(name, phone, text)

    return JsonResponse({"ok": True})
# autosum
