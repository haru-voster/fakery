import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django_countries.fields import CountryField
from django.db.models import Q as models_Q
from .models import KYCDocument
U = get_user_model()
class SignupForm(forms.Form):
    username = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone = forms.CharField(max_length=16, help_text="+254700000000")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
    country = CountryField(blank_label="Select your country").formfield()
    referral = forms.CharField(label="Referral ID (optional)", required=False, max_length=10)
    answer = forms.CharField(label="Security question")
    def __init__(self, *a, expected=None, **k):
        super().__init__(*a, **k); self.expected = expected
    def clean_username(self):
        v = self.cleaned_data["username"]
        if U.objects.filter(username__iexact=v).exists(): raise forms.ValidationError("Username taken.")
        return v
    def clean_email(self):
        v = self.cleaned_data["email"].lower()
        if U.objects.filter(email__iexact=v).exists(): raise forms.ValidationError("Email already registered.")
        return v
    def clean_phone(self):
        v = self.cleaned_data["phone"].replace(" ", "")
        if not re.fullmatch(r"\+\d{8,15}", v): raise forms.ValidationError("Use international format, e.g. +254700000000.")
        return v
    def clean_answer(self):
        try: ok = int(self.cleaned_data["answer"]) == self.expected
        except (ValueError, TypeError): ok = False
        if not ok: raise forms.ValidationError("Wrong answer.")
        return self.cleaned_data["answer"]
    def clean(self):
        d = super().clean()
        if d.get("password1") != d.get("password2"): self.add_error("password2", "Passwords do not match.")
        elif d.get("password1"): validate_password(d["password1"])
        return d
class KYCForm(forms.ModelForm):
    class Meta: model = KYCDocument; fields = ["id_type", "file"]
    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 5*1024*1024: raise forms.ValidationError("Max 5 MB.")
        if not f.name.lower().endswith((".jpg", ".jpeg", ".png", ".pdf")): raise forms.ValidationError("JPG, PNG or PDF only.")
        return f

class SettingsForm(forms.Form):
    email = forms.EmailField(); phone = forms.CharField(max_length=16)
    new_password = forms.CharField(required=False, widget=forms.PasswordInput, label="New password (leave blank to keep current)")
    def __init__(self, *a, user=None, **k):
        super().__init__(*a, **k); self.user = user
    def clean_email(self):
        v = self.cleaned_data["email"].lower()
        if U.objects.filter(email__iexact=v).exclude(pk=self.user.pk).exists(): raise forms.ValidationError("Email already in use.")
        return v
    def clean_phone(self):
        v = self.cleaned_data["phone"].replace(" ", "")
        if not re.fullmatch(r"\+\d{8,15}", v): raise forms.ValidationError("Use international format, e.g. +254700000000.")
        return v
    def clean_new_password(self):
        v = self.cleaned_data["new_password"]
        if v: validate_password(v, self.user)
        return v
class FundForm(forms.Form):
    kind = forms.ChoiceField(label="Type", choices=[("deposit", "Deposit")])
    method = forms.ChoiceField(choices=[(m, m) for m in ["M-Pesa", "Card", "Bank transfer", "Crypto wallet"]])
    amount = forms.DecimalField(label="Amount (USD)", min_value=1, max_digits=12, decimal_places=2)
    def __init__(self, *a, available=0, **k):
        super().__init__(*a, **k); self.available = available
    def clean(self):
        d = super().clean()
        if d.get("kind") == "withdrawal" and d.get("amount") and d["amount"] > self.available:
            raise forms.ValidationError("Insufficient available balance.")
        return d

class _PwForm(forms.Form):
    password = forms.CharField(label="Confirm with your password", widget=forms.PasswordInput)
    def __init__(self, *a, user=None, **k):
        super().__init__(*a, **k); self.user = user
    def clean_password(self):
        v = self.cleaned_data["password"]
        if not self.user.check_password(v): raise forms.ValidationError("Incorrect password.")
        return v
class WithdrawForm(_PwForm):
    method = forms.ChoiceField(choices=[(m, m) for m in ["USDT", "Bitcoin", "Ethereum", "BNB Bep20", "Bank transfer"]])
    destination = forms.CharField(label="Wallet address or account", max_length=120)
    amount = forms.DecimalField(label="Amount (USD, min $100)", min_value=100, max_digits=12, decimal_places=2)
    def __init__(self, *a, available=0, **k):
        super().__init__(*a, **k); self.available = available
    def clean(self):
        d = super().clean()
        if d.get("amount") and d["amount"] > self.available: raise forms.ValidationError("Insufficient available balance.")
        return d
class TransferForm(_PwForm):
    recipient = forms.CharField(label="Recipient username or email", max_length=150)
    amount = forms.DecimalField(label="Amount (USD)", min_value=1, max_digits=12, decimal_places=2)
    def __init__(self, *a, available=0, **k):
        super().__init__(*a, **k); self.available = available; self.target = None
    def clean_recipient(self):
        v = self.cleaned_data["recipient"].strip()
        t = U.objects.filter(is_active=True).filter(models_Q(username__iexact=v) | models_Q(email__iexact=v)).first()
        if not t or t == self.user: raise forms.ValidationError("Recipient not found.")
        self.target = t; return v
    def clean(self):
        d = super().clean()
        if d.get("amount") and d["amount"] > self.available: raise forms.ValidationError("Insufficient available balance.")
        return d
