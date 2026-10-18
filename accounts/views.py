import random, time, requests
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.conf import settings as dj
from django.db import transaction as dbtx, IntegrityError
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from .forms import SignupForm, KYCForm, SettingsForm, FundForm, WithdrawForm, TransferForm
from .models import Profile, Transaction, SupportMessage
from .notifications import notify_signup, notify_support
def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST, expected=request.session.get("cap"))
        if form.is_valid():
            d = form.cleaned_data
            try:
                with dbtx.atomic():
                    User = get_user_model()
                    user = User.objects.create_user(
                        username=d["username"].strip(),
                        email=d["email"].strip().lower(),
                        password=d["password1"],
                    )
                    ref = Profile.objects.filter(referral_code=d["referral"].strip().upper()).first() if d["referral"] else None
                    Profile.objects.create(user=user, phone=d["phone"], country=d["country"], referred_by=ref)
            except IntegrityError:
                form.add_error(None, "We could not create the account because the username or email is already registered. Please try logging in or use different details.")
            else:
                # Notifications must never undo account creation.
                try:
                    notify_signup(user)
                except Exception:
                    pass
                messages.success(request, "Your account was created successfully. You can now sign in.")
                return render(request, "accounts/signup.html", {
                    "success": True,
                    "created_username": user.username,
                })
    else:
        form = SignupForm()
    a, b = random.randint(1, 9), random.randint(1, 9)
    request.session["cap"] = a + b
    form.fields["answer"].label = f"Security question: What is {a} + {b}?"
    return render(request, "accounts/signup.html", {"form": form})

IN, OUT = ("deposit", "transfer_in"), ("withdrawal", "transfer_out")
def _totals(user):
    ok = Transaction.objects.filter(user=user, status="completed")
    s = lambda ks: ok.filter(kind__in=ks).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    return s(IN), s(OUT)
def _available(user):
    dep, wd = _totals(user)
    held = Transaction.objects.filter(user=user, kind__in=OUT, status="pending").aggregate(t=Sum("amount"))["t"] or Decimal("0")
    return dep - wd - held
class ThrottledLogin(LoginView):
    """Locks a username+IP pair for 15 minutes after 5 failed attempts."""
    template_name = "accounts/login.html"
    def post(self, request, *a, **k):
        key = "lf:%s:%s" % (request.META.get("REMOTE_ADDR", ""), request.POST.get("username", "").lower())
        if cache.get(key, 0) >= 5:
            return render(request, self.template_name, {"form": AuthenticationForm(request), "locked": True}, status=429)
        resp = super().post(request, *a, **k)
        if request.user.is_authenticated:
            cache.delete(key)
        elif resp.status_code == 200:
            cache.set(key, cache.get(key, 0) + 1, 900)
        return resp
@login_required
def dashboard(request):
    # Staff-created accounts may not have a Profile yet; create a safe default.
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"phone": "", "country": "KE"})

    # Staff users get an overview of all accounts and payment records.
    # Only transactions explicitly marked completed count toward customer balances.
    if request.user.is_staff:
        users = get_user_model().objects.all().order_by("-date_joined")
        txs = Transaction.objects.select_related("user").all()[:100]
        pending_deposits = Transaction.objects.filter(kind="deposit", status="pending")
        completed_deposits = Transaction.objects.filter(kind="deposit", status="completed")
        pending_total = pending_deposits.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        completed_total = completed_deposits.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        return render(request, "accounts/admin_dashboard.html", {
            "page": "ov", "profile": profile, "users": users[:100], "txs": txs,
            "user_count": users.count(), "pending_count": pending_deposits.count(),
            "pending_total": pending_total, "completed_total": completed_total,
        })

    dep, wd = _totals(request.user)
    return render(request, "accounts/dashboard.html", {"page": "ov", "profile": profile, "dep": dep, "wd": wd,
        "balance": dep - wd, "txs": Transaction.objects.filter(user=request.user)[:10]})
@login_required
def settings_view(request):
    u, p = request.user, request.user.profile
    form = SettingsForm(request.POST or None, user=u, initial={"email": u.email, "phone": p.phone})
    saved = False
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data; u.email = d["email"]; p.phone = d["phone"]; p.save(update_fields=["phone"])
        if d["new_password"]: u.set_password(d["new_password"])
        u.save()
        if d["new_password"]:
            update_session_auth_hash(request, u)
            send_mail("Your password was changed", "If this wasn't you, reset your password immediately and contact support.", dj.DEFAULT_FROM_EMAIL, [u.email], fail_silently=True)
        saved = True
    return render(request, "accounts/settings.html", {"page": "set", "form": form, "saved": saved})
@login_required
def fund(request):
    form = FundForm(request.POST or None, available=0)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        Transaction.objects.create(user=request.user, kind="deposit", amount=d["amount"], status="pending", reference=d["method"])
        notify_support(request.user.username, request.user.profile.phone, f"deposit request ${d['amount']} via {d['method']}")
        return redirect("history")
    return render(request, "accounts/fund.html", {"page": "fund", "form": form})
@login_required
def withdraw(request):
    if request.user.profile.kyc_status != "approved":
        messages.error(request, "Verify your identity (KYC) before withdrawing."); return redirect("kyc")
    form = WithdrawForm(request.POST or None, user=request.user, available=_available(request.user))
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        Transaction.objects.create(user=request.user, kind="withdrawal", amount=d["amount"], status="pending",
                                   reference=f"{d['method']}: {d['destination']}")
        send_mail("Withdrawal request received", f"We received your request to withdraw ${d['amount']} via {d['method']}. If this wasn't you, reset your password now.",
                  dj.DEFAULT_FROM_EMAIL, [request.user.email], fail_silently=True)
        notify_support(request.user.username, request.user.profile.phone, f"withdrawal request ${d['amount']} via {d['method']}")
        return redirect("history")
    return render(request, "accounts/withdraw.html", {"page": "wd", "form": form, "available": _available(request.user)})
@login_required
def transfer(request):
    if request.user.profile.kyc_status != "approved":
        messages.error(request, "Verify your identity (KYC) before transferring."); return redirect("kyc")
    with dbtx.atomic():
        Profile.objects.select_for_update().get(user=request.user)  # serialise concurrent spends
        form = TransferForm(request.POST or None, user=request.user, available=_available(request.user))
        if request.method == "POST" and form.is_valid():
            d = form.cleaned_data
            Transaction.objects.create(user=request.user, kind="transfer_out", amount=d["amount"], status="completed", reference=f"to {form.target.username}")
            Transaction.objects.create(user=form.target, kind="transfer_in", amount=d["amount"], status="completed", reference=f"from {request.user.username}")
            send_mail("You received a transfer", f"{request.user.username} sent you ${d['amount']}.", dj.DEFAULT_FROM_EMAIL, [form.target.email], fail_silently=True)
            return redirect("history")
    return render(request, "accounts/transfer.html", {"page": "tr", "form": form, "available": _available(request.user)})
@login_required
def history(request):
    kind = request.GET.get("type", ""); qs = Transaction.objects.filter(user=request.user)
    if kind in ("deposit", "withdrawal", "transfer_out", "transfer_in"): qs = qs.filter(kind=kind)
    return render(request, "accounts/history.html", {"page": "tx", "txs": qs[:100], "kind": kind})
@login_required
def kyc(request):
    form = KYCForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        doc = form.save(commit=False); doc.user = request.user; doc.save()
        p = request.user.profile; p.kyc_status = "pending"; p.save(update_fields=["kyc_status"])
        return redirect("dashboard")
    return render(request, "accounts/kyc.html", {"form": form})
def prices(request):
    data = cache.get("prices")
    if data is None:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price", timeout=8,
                params={"ids": "bitcoin,ethereum,solana,ripple,avalanche-2,shiba-inu,tether,aave", "vs_currencies": "usd", "include_24hr_change": "true"})
            r.raise_for_status(); data = r.json(); cache.set("prices", data, 60)
        except requests.RequestException:
            return JsonResponse({"error": "price feed unavailable"}, status=503)
    return JsonResponse(data)
def home(request):
    return render(request, "accounts/home.html")
@require_POST
def support_message(request):
    now = time.time()
    if now - request.session.get("sm_t", 0) < 30:
        return JsonResponse({"error": "Please wait a moment before sending another message."}, status=429)
    name = request.POST.get("name", "").strip()[:60]; phone = request.POST.get("phone", "").strip()[:20]
    text = request.POST.get("message", "").strip()[:500]
    if not text or not name: return JsonResponse({"error": "Name and message are required."}, status=400)
    SupportMessage.objects.create(name=name, phone=phone, message=text)
    request.session["sm_t"] = now
    notify_support(name, phone, text)
    return JsonResponse({"ok": True})
