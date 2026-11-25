from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from apps.accounts.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    LogoutSerializer
)
from apps.accounts.services import AccountService


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserRegistrationSerializer,
        responses={201: inline_serializer(
            name='RegisterResponse',
            fields={
                'user': UserSerializer(),
                'tokens': inline_serializer(
                    name='TokenBundle',
                    fields={'access': serializers.CharField(), 'refresh': serializers.CharField()}
                )
            }
        )},
        description="Register a new healthcare provider / user account."
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tokens = AccountService.register_user(
            email=serializer.validated_data['email'],
            name=serializer.validated_data['name'],
            password=serializer.validated_data['password']
        )
        return Response(
            {
                "success": True,
                "data": {
                    "user": UserSerializer(user).data,
                    "tokens": tokens,
                }
            },
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=UserLoginSerializer,
        description="Authenticate with email and password to receive JWT access and refresh tokens."
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "success": True,
                "data": serializer.validated_data
            },
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        description="Revoke and blacklist the refresh token to conclude the session."
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"success": True, "message": "Successfully logged out. Refresh token has been blacklisted."},
            status=status.HTTP_200_OK
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        description="Retrieve the profile of the currently authenticated user."
    )
    def get(self, request):
        return Response(
            {
                "success": True,
                "data": UserSerializer(request.user).data
            },
            status=status.HTTP_200_OK
        )
