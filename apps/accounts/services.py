from typing import Dict, Any, Tuple
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from common.exceptions import ValidationError, ApplicationError


class AccountService:
    """Service layer handling user authentication, registration, and session token lifecycle."""

    @staticmethod
    @transaction.atomic
    def register_user(email: str, name: str, password: str) -> Tuple[User, Dict[str, str]]:
        """Registers a new user and returns JWT tokens."""
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.", code="USER_ALREADY_EXISTS")

        user = User.objects.create_user(email=email, name=name, password=password)
        refresh = RefreshToken.for_user(user)

        tokens = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
        return user, tokens

    @staticmethod
    def blacklist_token(refresh_token_str: str) -> None:
        """Revokes a refresh token by adding it to the blacklist table."""
        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
        except Exception as e:
            raise ValidationError(f"Invalid or already revoked token: {str(e)}", code="INVALID_TOKEN")
