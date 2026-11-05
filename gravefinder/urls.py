"""Root URL configuration for Grave Finder."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("memorials/", include("memorials.urls")),
    path("", include("cemeteries.urls")),
]
