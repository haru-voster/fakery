from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

class EmailOrUsernameBackend(ModelBackend):
    """Authenticate active users by username OR email, case-insensitively."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(get_user_model().USERNAME_FIELD)
        if not identifier or password is None:
            return None
        User = get_user_model()
        user = User.objects.filter(
            Q(username__iexact=identifier.strip()) | Q(email__iexact=identifier.strip())
        ).order_by("pk").first()
        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
