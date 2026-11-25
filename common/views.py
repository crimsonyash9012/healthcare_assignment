import time
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema


class HealthCheckView(APIView):
    """
    Health check endpoint reporting system status, database/PgBouncer connectivity,
    and query response latency.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: dict},
        description="Check database and application operational health."
    )
    def get(self, request):
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {}
        }

        # Check PostgreSQL / PgBouncer connectivity
        db_start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    db_latency_ms = round((time.perf_counter() - db_start) * 1000, 2)
                    health_status["services"]["database"] = {
                        "status": "up",
                        "latency_ms": db_latency_ms,
                        "vendor": connection.vendor
                    }
                else:
                    health_status["status"] = "degraded"
                    health_status["services"]["database"] = {
                        "status": "unexpected_result"
                    }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["services"]["database"] = {
                "status": "down",
                "error": str(e)
            }

        http_status = status.HTTP_200_OK if health_status["status"] != "unhealthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=http_status)
