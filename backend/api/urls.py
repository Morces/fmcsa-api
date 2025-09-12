from rest_framework.routers import DefaultRouter
from .views import DriverViewSet, TruckViewSet, TripViewSet, LogSheetViewSet

router = DefaultRouter()
router.register(r"drivers", DriverViewSet)
router.register(r"trucks", TruckViewSet)
router.register(r"trips", TripViewSet)
router.register(r"logs", LogSheetViewSet)

urlpatterns = router.urls
