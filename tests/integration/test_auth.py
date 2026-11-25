from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User


class AuthIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_flow(self):
        payload = {
            "name": "Dr. Sarah Connor",
            "email": "sarah@cyberdyne.com",
            "password": "SecurePassword123!"
        }
        response = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["user"]["email"], "sarah@cyberdyne.com")
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])

    def test_login_and_token_refresh(self):
        User.objects.create_user(
            email="login.test@example.com",
            name="Login User",
            password="TestPassword123!"
        )

        login_res = self.client.post(
            "/api/auth/login/",
            {"email": "login.test@example.com", "password": "TestPassword123!"},
            format="json"
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        access = login_res.data["data"]["access"]
        refresh = login_res.data["data"]["refresh"]

        # Access protected endpoint with Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_res = self.client.get("/api/auth/me/")
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["data"]["email"], "login.test@example.com")

        # Refresh token
        refresh_res = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        new_access = refresh_res.data["access"]
        new_refresh = refresh_res.data.get("refresh", refresh)
        self.assertIsNotNone(new_access)

        # Logout & blacklist rotated active token
        logout_res = self.client.post("/api/auth/logout/", {"refresh": new_refresh}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Re-using blacklisted refresh token must fail
        reuse_res = self.client.post("/api/auth/token/refresh/", {"refresh": new_refresh}, format="json")
        self.assertEqual(reuse_res.status_code, status.HTTP_401_UNAUTHORIZED)
