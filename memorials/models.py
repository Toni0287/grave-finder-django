"""Memorial pages, condolences and donations to families."""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.urls import reverse

from cemeteries.models import Grave

CENTS = Decimal("0.01")


class MemorialQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Memorial.Status.ACTIVE)

    def visible_to(self, user):
        """Published memorials, plus the user's own drafts (admins see everything)."""
        if user.is_authenticated and user.is_site_admin:
            return self
        if user.is_authenticated:
            return self.filter(models.Q(status=Memorial.Status.ACTIVE) | models.Q(owner=user))
        return self.published()


class Memorial(models.Model):
    """An online memorial page for a loved one, optionally linked to a grave."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Published"
        ARCHIVED = "archived", "Archived"

    grave = models.ForeignKey(
        Grave, null=True, blank=True, on_delete=models.SET_NULL, related_name="memorials"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memorials"
    )
    full_name = models.CharField(max_length=200)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    tagline = models.CharField(max_length=200, blank=True, help_text="A short line shown under the name.")
    biography = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    donations_enabled = models.BooleanField(
        default=True, help_text="Let visitors donate to support the family."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MemorialQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("memorials:detail", args=[self.pk])

    def can_edit(self, user):
        return user.is_authenticated and (user == self.owner or user.is_site_admin)

    @property
    def is_published(self):
        return self.status == self.Status.ACTIVE

    def completed_donations(self):
        return self.donations.filter(status=Donation.Status.COMPLETED)

    def donation_total(self):
        return self.completed_donations().aggregate(total=Sum("amount"))["total"] or Decimal("0")


class Condolence(models.Model):
    """A message left on a memorial page by a visitor."""

    memorial = models.ForeignKey(Memorial, on_delete=models.CASCADE, related_name="condolences")
    author_name = models.CharField(max_length=100)
    message = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author_name} on {self.memorial}"


class Donation(models.Model):
    """Money given to support a family.

    The platform keeps ``DONATION_PLATFORM_FEE`` (5% by default) and the rest
    goes to the family.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    memorial = models.ForeignKey(Memorial, on_delete=models.CASCADE, related_name="donations")
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="donations",
    )
    donor_name = models.CharField(max_length=100)
    donor_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_anonymous = models.BooleanField(default=False)
    message = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    gateway_payment_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"R{self.amount} to {self.memorial} ({self.status})"

    @property
    def display_name(self):
        return "Anonymous" if self.is_anonymous else self.donor_name

    @property
    def platform_fee(self):
        return (self.amount * settings.DONATION_PLATFORM_FEE).quantize(CENTS, rounding=ROUND_HALF_UP)

    @property
    def family_amount(self):
        return self.amount - self.platform_fee

    def mark_completed(self, payment_id=""):
        """Record a successful payment and post the donor's message, if any."""
        from django.utils import timezone

        if self.status == self.Status.COMPLETED:
            return
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.gateway_payment_id = payment_id
        self.save(update_fields=["status", "completed_at", "gateway_payment_id"])
        if self.message:
            Condolence.objects.create(
                memorial=self.memorial, author_name=self.display_name, message=self.message
            )
