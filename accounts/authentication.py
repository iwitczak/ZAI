from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import AccessToken


class BearerTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if len(parts) != 2 or parts[0].lower() != b"bearer":
            return None
        try:
            token = parts[1].decode()
        except UnicodeError:
            raise AuthenticationFailed("Invalid token.")

        try:
            token = AccessToken.objects.select_related("user").get(
                token_hash=AccessToken.hash(token),
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
        except AccessToken.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")

        if not token.user.is_active:
            raise AuthenticationFailed("Invalid token.")
        return (token.user, token)

    # def authenticate_header(self, request):
    #     return "Bearer"