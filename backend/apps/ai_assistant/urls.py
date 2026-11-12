from django.urls import path
from .views import GenerateQuizView, RevisionPlanView

urlpatterns = [
    path("generate-quiz/", GenerateQuizView.as_view(), name="ai-generate-quiz"),
    path("revision-plan/", RevisionPlanView.as_view(), name="ai-revision-plan"),
]

