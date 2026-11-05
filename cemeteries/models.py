"""Cemetery and grave records."""

from django.db import models
from django.urls import reverse


class CemeteryQuerySet(models.QuerySet):
    def public(self):
        return self.filter(type=Cemetery.Type.PUBLIC)

    def private(self):
        return self.filter(type=Cemetery.Type.PRIVATE)


class Cemetery(models.Model):
    """A cemetery or memorial park with a GPS location for its entrance."""

    class Type(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    name = models.CharField(max_length=150, unique=True)
    type = models.CharField(max_length=10, choices=Type.choices)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    capacity = models.PositiveIntegerField(default=0)
    available_plots = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    objects = CemeteryQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cemeteries"

    def __str__(self):
        return self.name

    @property
    def occupancy_percent(self):
        """Share of the cemetery's capacity already in use (0-100)."""
        if not self.capacity:
            return 0
        used = self.capacity - self.available_plots
        return round(used / self.capacity * 100)


class GraveQuerySet(models.QuerySet):
    def active(self):
        """Graves that have not been soft-deleted."""
        return self.filter(deleted_at__isnull=True)


class Grave(models.Model):
    """A single burial record.

    Records are soft-deleted (``deleted_at`` is set) rather than removed, so
    there is always an audit trail, as POPIA record-keeping expects.
    """

    class PlotSize(models.TextChoices):
        SINGLE = "Single", "Single"
        DOUBLE = "Double", "Double"

    cemetery = models.ForeignKey(Cemetery, on_delete=models.PROTECT, related_name="graves")
    first_name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    date_of_death = models.DateField()
    date_of_burial = models.DateField(null=True, blank=True)
    age_at_death = models.PositiveIntegerField(null=True, blank=True)
    section = models.CharField(max_length=20, blank=True)
    plot = models.CharField(max_length=20, blank=True)
    grave_number = models.CharField(max_length=30, unique=True)
    plot_size = models.CharField(max_length=10, choices=PlotSize.choices, default=PlotSize.SINGLE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = GraveQuerySet.as_manager()

    class Meta:
        ordering = ["surname", "first_name"]
        indexes = [
            models.Index(fields=["surname", "first_name"]),
            models.Index(fields=["date_of_death"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.grave_number})"

    def get_absolute_url(self):
        return reverse("cemeteries:grave_detail", args=[self.pk])

    @property
    def full_name(self):
        return f"{self.first_name} {self.surname}"

    @property
    def location_label(self):
        """Human readable location inside the cemetery, e.g. 'Section A, Plot 12'."""
        parts = []
        if self.section:
            parts.append(f"Section {self.section}")
        if self.plot:
            parts.append(f"Plot {self.plot}")
        parts.append(f"Grave {self.grave_number}")
        return ", ".join(parts)

    def map_marker(self):
        """Data the map JavaScript needs to draw this grave."""
        return {
            "id": self.pk,
            "name": self.full_name,
            "lat": self.latitude,
            "lng": self.longitude,
            "cemetery": self.cemetery.name,
            "location": self.location_label,
            "url": self.get_absolute_url(),
        }
