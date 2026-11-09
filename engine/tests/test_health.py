from rest_framework.test import APITestCase
import pytest

class HealthCheckTests(APITestCase):
    def test_health_returns_200(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_returns_ok_status(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_rejects_post(self):
        response = self.client.post("/api/health/")
        self.assertEqual(response.status_code, 405)