"""User model for Grave Finder."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A site user with a role.

    * ``public``  - families and visitors; can create memorials and donate.
    * ``staff``   - cemetery staff; can add and edit grave records.
    * ``admin``   - full access to everything, including other users' memorials.
    """

    class Role(models.TextChoices):
        PUBLIC = "public", "Public"
        STAFF = "staff", "Cemetery staff"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PUBLIC)

    @property
    def is_cemetery_staff(self):
        """True for staff and admins, who may manage grave records."""
        return self.role in (self.Role.STAFF, self.Role.ADMIN) or self.is_superuser

    @property
    def is_site_admin(self):
        """True for admins and Django superusers."""
        return self.role == self.Role.ADMIN or self.is_superuser

    def save(self, *args, **kwargs):
        """Give staff and admins access to the Django admin site."""
        if self.role in (self.Role.STAFF, self.Role.ADMIN):
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
