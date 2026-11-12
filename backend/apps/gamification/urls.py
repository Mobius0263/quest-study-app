from django.urls import path
from .views import StudentProgressMeView, TeacherProgressView

urlpatterns = [
    path("me/", StudentProgressMeView.as_view(), name="progress-me"),
    path("", TeacherProgressView.as_view(), name="progress-teacher"),
]

