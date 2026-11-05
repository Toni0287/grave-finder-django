from django.contrib import admin

from .models import Condolence, Donation, Memorial


class CondolenceInline(admin.TabularInline):
    model = Condolence
    extra = 0


@admin.register(Memorial)
class MemorialAdmin(admin.ModelAdmin):
    list_display = ("full_name", "owner", "status", "grave", "created_at")
    list_filter = ("status", "donations_enabled")
    search_fields = ("full_name", "owner__username")
    raw_id_fields = ("grave",)
    inlines = [CondolenceInline]


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("memorial", "donor_name", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("donor_name", "donor_email", "memorial__full_name")
    readonly_fields = ("reference", "gateway_payment_id", "completed_at")
