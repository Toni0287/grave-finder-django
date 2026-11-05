from django.urls import path

from . import views

app_name = "cemeteries"

urlpatterns = [
    path("", views.search, name="search"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("cemeteries/", views.cemetery_list, name="cemetery_list"),
    path("graves/new/", views.grave_create, name="grave_create"),
    path("graves/<int:pk>/", views.grave_detail, name="grave_detail"),
    path("graves/<int:pk>/print/", views.grave_print, name="grave_print"),
    path("graves/<int:pk>/edit/", views.grave_update, name="grave_update"),
    path("graves/<int:pk>/delete/", views.grave_delete, name="grave_delete"),
]
