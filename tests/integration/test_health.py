from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class HealthCheckIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("status", res.data)
        self.assertIn("services", res.data)
        self.assertIn("database", res.data["services"])
        self.assertEqual(res.data["services"]["database"]["status"], "up")
