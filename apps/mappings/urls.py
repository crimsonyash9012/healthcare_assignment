from rest_framework.routers import DefaultRouter
from apps.mappings.views import MappingViewSet

app_name = 'mappings'

router = DefaultRouter()
router.register(r'', MappingViewSet, basename='mapping')

urlpatterns = router.urls
