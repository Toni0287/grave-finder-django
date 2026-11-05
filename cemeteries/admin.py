from django.contrib import admin

from .models import Cemetery, Grave


@admin.register(Cemetery)
class CemeteryAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "capacity", "available_plots")
    list_filter = ("type",)
    search_fields = ("name", "address")


@admin.register(Grave)
class GraveAdmin(admin.ModelAdmin):
    list_display = ("surname", "first_name", "cemetery", "grave_number", "date_of_death", "deleted_at")
    list_filter = ("cemetery__type", "cemetery", "plot_size")
    search_fields = ("first_name", "surname", "grave_number")
    date_hierarchy = "date_of_death"
    list_select_related = ("cemetery",)
