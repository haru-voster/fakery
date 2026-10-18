from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate active users by case-insensitive username or email.

    Prefer username matches first, then fall back to email. This avoids a
    collision between one person's username and another person's email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get(get_user_model().USERNAME_FIELD)
        if not identifier or password is None:
            return None
        identifier = identifier.strip()
        User = get_user_model()
        user = User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": identifier}).first()
        if user is None and hasattr(User, "email"):
            user = User.objects.filter(email__iexact=identifier).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
