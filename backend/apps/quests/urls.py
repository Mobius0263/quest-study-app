from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestViewSet

router = DefaultRouter()
router.register(r"", QuestViewSet, basename="quest")

urlpatterns = [
    path("", include(router.urls)),
]

