
from django.contrib import admin
from django.urls import path , include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import landing_view

urlpatterns = [
    path("", landing_view, name="landing"),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('child/', include('child_interface.urls')),
    path("ai/", include("ai_module.urls")),
     path("parent/", include(("parent_portal.urls", "parent_portal"), namespace="parent_portal")),
    path("specialist/", include("specialist_portal.urls")),
    path("reports/", include("reports.urls")),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
