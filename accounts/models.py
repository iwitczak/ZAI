import hashlib
import secrets

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

from ZAI import settings

class User(AbstractUser):
    pass

class AccessToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_tokens"
    )

    token_hash = models.CharField(max_length=64, unique=True) # 64 = sha-256 hash length
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def hash(token: str):
        """Return the SHA-256 hex digest of the provided token."""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def generate_token(cls, user):
        """Generate a new random token."""
        token = secrets.token_urlsafe(32)
        cls.objects.create(
            user=user,
            token_hash=cls.hash(token),
            expires_at=timezone.now() + settings.TOKEN_TTL
        )
        return token, int(settings.TOKEN_TTL.total_seconds())

    @classmethod
    def get_valid_token(cls, token: str):
        """Return the AccessToken instance if the provided token is valid, otherwise return None."""
        return (
            AccessToken.objects.select_related("user")
            .filter(
                token_hash=cls.hash(token),
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )
    
