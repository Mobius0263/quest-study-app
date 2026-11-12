from django.urls import path
from .views import (
    ModuleBatchRegenerateView,
    ModuleDetailView,
    ModuleProcessView,
    ModulePublishView,
    ModuleQuestionUpdateView,
    ModuleReviewView,
    ModuleView,
)

urlpatterns = [
    path("", ModuleView.as_view(), name="modules-list"),
    path("<int:pk>/", ModuleDetailView.as_view(), name="modules-detail"),
    path("<int:pk>/process/", ModuleProcessView.as_view(), name="modules-process"),
    path("<int:pk>/review/", ModuleReviewView.as_view(), name="modules-review"),
    path(
        "<int:pk>/questions/<int:question_id>/",
        ModuleQuestionUpdateView.as_view(),
        name="modules-question-update",
    ),
    path(
        "<int:pk>/batches/<int:batch_index>/regenerate/",
        ModuleBatchRegenerateView.as_view(),
        name="modules-batch-regenerate",
    ),
    path("<int:pk>/publish/", ModulePublishView.as_view(), name="modules-publish"),
]

