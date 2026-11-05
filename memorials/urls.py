from django.urls import path

from . import views

app_name = "memorials"

urlpatterns = [
    path("", views.memorial_list, name="list"),
    path("new/", views.memorial_create, name="create"),
    path("<int:pk>/", views.memorial_detail, name="detail"),
    path("<int:pk>/edit/", views.memorial_update, name="update"),
    path("<int:pk>/status/", views.memorial_set_status, name="set_status"),
    path("<int:pk>/condolences/", views.condolence_create, name="condolence_create"),
    path("<int:pk>/donate/", views.donate, name="donate"),
    path("donations/<uuid:reference>/", views.donation_thanks, name="donation_thanks"),
    path("payfast/notify/", views.payfast_notify, name="payfast_notify"),
]
