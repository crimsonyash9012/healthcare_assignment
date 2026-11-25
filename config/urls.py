from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from common.views import HealthCheckView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Health Check
    path('api/health/', HealthCheckView.as_view(), name='health-check'),

    # OpenAPI Schema & Interactive Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Application Domain Endpoints
    path('api/auth/', include('apps.accounts.urls', namespace='accounts')),
    path('api/patients/', include('apps.patients.urls', namespace='patients')),
    path('api/doctors/', include('apps.doctors.urls', namespace='doctors')),
    path('api/mappings/', include('apps.mappings.urls', namespace='mappings')),
]
