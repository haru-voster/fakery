from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
class EmailOrUsernameBackend(ModelBackend):
    """Log in with either username or email."""
    def authenticate(self, request, username=None, password=None, **kw):
        if not username or not password: return None
        u = get_user_model().objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).first()
        if u and u.check_password(password) and self.user_can_authenticate(u): return u
