from django.contrib import admin
from django.contrib.staticfiles.views import serve as static_serve
from django.urls import include, path

from invite.views import media

urlpatterns = [
    path("admin/", admin.site.urls),
    # shortcut: Django serves static/media itself (no nginx/whitenoise), fine for one party; put a CDN/nginx in front if traffic grows
    path("static/<path:path>", static_serve, {"insecure": True}),
    path("media/<path:path>", media),
    path("", include("invite.urls")),
]
