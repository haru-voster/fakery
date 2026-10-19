from django.contrib.auth import views as av
from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/status/", views.dashboard_status, name="dashboard_status"),
    path("dashboard/settings/", views.settings_view, name="settings"),
    path("dashboard/fund/", views.fund, name="fund"),
    path("dashboard/withdraw/", views.withdraw, name="withdraw"),
    path("dashboard/transfer/", views.transfer, name="transfer"),
    path("dashboard/history/", views.history, name="history"),
    path("support/message/", views.support_message, name="support"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.ThrottledLogin.as_view(), name="login"),
    path("password-reset/", av.PasswordResetView.as_view(template_name="accounts/pw_reset.html", email_template_name="accounts/pw_reset_email.txt",
         subject_template_name="accounts/pw_reset_subject.txt", extra_email_context={"brand": "BlueRock Group Investiments"}), name="password_reset"),
    path("password-reset/sent/", av.PasswordResetDoneView.as_view(template_name="accounts/pw_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", av.PasswordResetConfirmView.as_view(template_name="accounts/pw_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", av.PasswordResetCompleteView.as_view(template_name="accounts/pw_reset_complete.html"), name="password_reset_complete"),
    path("logout/", av.LogoutView.as_view(), name="logout"),
    path("kyc/", views.kyc, name="kyc"),
    path("prices/", views.prices, name="prices"),
]
