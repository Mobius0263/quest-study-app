"""
URL configuration for core project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/quests/", include("apps.quests.urls")),
    path("api/quizzes/", include("apps.quizzes.urls")),
    path("api/progress/", include("apps.gamification.urls")),
    path("api/ai/", include("apps.ai_assistant.urls")),
    path("api/modules/", include("apps.ai_assistant.modules_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
