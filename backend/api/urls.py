from rest_framework.routers import DefaultRouter
from .views import DriverViewSet, TruckViewSet, TripViewSet, LogSheetViewSet, get_logged_in_user
from django.urls import path


router = DefaultRouter()
router.register(r"drivers", DriverViewSet)
router.register(r"trucks", TruckViewSet)
router.register(r"trips", TripViewSet)
router.register(r"logs", LogSheetViewSet)

urlpatterns = [
    path("auth/me/", get_logged_in_user, name="get_logged_in_user"),
]

urlpatterns += router.urls
