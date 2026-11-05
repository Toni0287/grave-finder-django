"""Figures for the statistics dashboard, kept out of the views so they are easy to test."""

from django.db.models import Avg, Count, Q
from django.db.models.functions import ExtractYear

from .models import Cemetery, Grave


class DashboardStats:
    """Collects every number the dashboard shows in one place."""

    def __init__(self):
        self.graves = Grave.objects.active()
        self.cemeteries = Cemetery.objects.all()

    def totals(self):
        return {
            "graves": self.graves.count(),
            "cemeteries": self.cemeteries.count(),
            "public": self.cemeteries.public().count(),
            "private": self.cemeteries.private().count(),
            "average_age": round(self.graves.aggregate(a=Avg("age_at_death"))["a"] or 0),
        }

    def per_cemetery(self):
        """Each cemetery annotated with how many active graves it holds."""
        return self.cemeteries.annotate(
            grave_count=Count("graves", filter=Q(graves__deleted_at__isnull=True))
        ).order_by("-grave_count", "name")

    def burials_per_year(self):
        """List of ``{"year": 2015, "count": 84}`` in year order."""
        return list(
            self.graves.annotate(year=ExtractYear("date_of_death"))
            .values("year")
            .annotate(count=Count("id"))
            .order_by("year")
        )

    def plot_sizes(self):
        return list(self.graves.values("plot_size").annotate(count=Count("id")).order_by("plot_size"))
