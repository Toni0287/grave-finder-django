"""Create a published demo memorial with condolences and donations.

Run ``seed_graves`` first so there is a grave to link to.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from cemeteries.models import Grave
from memorials.models import Condolence, Donation, Memorial

BIOGRAPHY = """Thandi was a teacher in Maitland for more than thirty years. Former pupils still stop her family in the street to say she was the one who believed in them.

She loved her garden, Sunday lunches with all the grandchildren, and the choir at St Mark's, where she sang alto for four decades."""


class Command(BaseCommand):
    help = "Create a demo memorial page with condolences and donations."

    @transaction.atomic
    def handle(self, *args, **options):
        owner, created = User.objects.get_or_create(
            username="family-demo",
            defaults={"email": "family@example.com", "first_name": "Demo", "last_name": "Family"},
        )
        if created:
            owner.set_unusable_password()
            owner.save()

        grave = Grave.objects.active().filter(cemetery__name="Maitland Cemetery").first()
        memorial, created = Memorial.objects.get_or_create(
            owner=owner,
            full_name="Thandi Dlamini",
            defaults={
                "grave": grave,
                "tagline": "Teacher, gardener, alto, grandmother.",
                "biography": BIOGRAPHY,
                "status": Memorial.Status.ACTIVE,
                "death_date": grave.date_of_death if grave else None,
            },
        )
        if not created:
            self.stdout.write("Demo memorial already exists.")
            return

        for name, message in [
            ("Sipho Ndlovu", "Mrs Dlamini taught me to read. I owe her more than I can say."),
            ("The St Mark's choir", "We will miss your voice every Sunday. Rest in peace, sister."),
        ]:
            Condolence.objects.create(memorial=memorial, author_name=name, message=message)

        for name, amount, anonymous in [
            ("Naziema Adams", "500", False),
            ("Pieter Botha", "250", False),
            ("A friend", "1000", True),
        ]:
            donation = Donation.objects.create(
                memorial=memorial,
                donor_name=name,
                donor_email="donor@example.com",
                amount=Decimal(amount),
                is_anonymous=anonymous,
            )
            donation.mark_completed(payment_id="DEMO")

        self.stdout.write(self.style.SUCCESS(f"Created memorial #{memorial.pk} for {memorial.full_name}"))
