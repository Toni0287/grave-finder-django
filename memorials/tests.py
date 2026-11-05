from collections import OrderedDict
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User

from .models import Condolence, Donation, Memorial
from .payments import PayFastGateway


class MemorialTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw-12345-x")
        self.other = User.objects.create_user("other", password="pw-12345-x")
        self.admin = User.objects.create_user("boss", password="pw-12345-x", role=User.Role.ADMIN)
        self.published = Memorial.objects.create(
            owner=self.owner, full_name="Thandi Dlamini", status=Memorial.Status.ACTIVE
        )
        self.draft = Memorial.objects.create(owner=self.owner, full_name="Draft Person")


class VisibilityTests(MemorialTestBase):
    def test_anonymous_sees_only_published(self):
        self.assertEqual(self.client.get(reverse("memorials:detail", args=[self.published.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("memorials:detail", args=[self.draft.pk])).status_code, 404)

    def test_owner_and_admin_see_draft(self):
        for user in (self.owner, self.admin):
            self.client.force_login(user)
            response = self.client.get(reverse("memorials:detail", args=[self.draft.pk]))
            self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_see_or_edit_draft(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("memorials:detail", args=[self.draft.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("memorials:update", args=[self.draft.pk])).status_code, 403)

    def test_list_shows_published_only(self):
        response = self.client.get(reverse("memorials:list"))
        self.assertContains(response, "Thandi Dlamini")
        self.assertNotContains(response, "Draft Person")


class MemorialEditingTests(MemorialTestBase):
    def test_create_requires_login(self):
        response = self.client.get(reverse("memorials:create"))
        self.assertEqual(response.status_code, 302)

    def test_create_starts_as_draft_owned_by_user(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("memorials:create"), {"full_name": "New Memorial", "donations_enabled": "on"}
        )
        memorial = Memorial.objects.get(full_name="New Memorial")
        self.assertRedirects(response, memorial.get_absolute_url())
        self.assertEqual(memorial.owner, self.other)
        self.assertEqual(memorial.status, Memorial.Status.DRAFT)

    def test_death_before_birth_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("memorials:create"),
            {"full_name": "X", "birth_date": "2000-01-01", "death_date": "1990-01-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Memorial.objects.filter(full_name="X").exists())

    def test_owner_can_publish(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("memorials:set_status", args=[self.draft.pk]), {"status": "active"})
        self.draft.refresh_from_db()
        self.assertTrue(self.draft.is_published)

    def test_other_user_cannot_publish(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("memorials:set_status", args=[self.draft.pk]), {"status": "active"})
        self.assertEqual(response.status_code, 403)


class CondolenceTests(MemorialTestBase):
    def test_anyone_can_leave_condolence_on_published(self):
        self.client.post(
            reverse("memorials:condolence_create", args=[self.published.pk]),
            {"author_name": "Sipho", "message": "Rest well."},
        )
        self.assertEqual(self.published.condolences.count(), 1)

    def test_no_condolences_on_drafts(self):
        response = self.client.post(
            reverse("memorials:condolence_create", args=[self.draft.pk]),
            {"author_name": "Sipho", "message": "Rest well."},
        )
        self.assertEqual(response.status_code, 404)


class DonationModelTests(MemorialTestBase):
    def test_fee_split(self):
        donation = Donation(memorial=self.published, amount=Decimal("250.00"))
        self.assertEqual(donation.platform_fee, Decimal("12.50"))
        self.assertEqual(donation.family_amount, Decimal("237.50"))

    def test_fee_rounds_to_cents(self):
        donation = Donation(memorial=self.published, amount=Decimal("33.33"))
        self.assertEqual(donation.platform_fee, Decimal("1.67"))

    def test_mark_completed_posts_message_once(self):
        donation = Donation.objects.create(
            memorial=self.published, donor_name="Anna", donor_email="a@example.com",
            amount=Decimal("100"), message="Thinking of you", is_anonymous=True,
        )
        donation.mark_completed("PF1")
        donation.mark_completed("PF1")
        self.assertEqual(Condolence.objects.filter(author_name="Anonymous").count(), 1)
        self.assertEqual(self.published.donation_total(), Decimal("100"))


@override_settings(PAYFAST_MODE="demo")
class DemoDonationViewTests(MemorialTestBase):
    def test_demo_donation_completes(self):
        response = self.client.post(
            reverse("memorials:donate", args=[self.published.pk]),
            {"amount": "250", "donor_name": "Anna", "donor_email": "a@example.com"},
        )
        donation = Donation.objects.get()
        self.assertRedirects(response, reverse("memorials:donation_thanks", args=[donation.reference]))
        self.assertEqual(donation.status, Donation.Status.COMPLETED)

    def test_minimum_amount(self):
        response = self.client.post(
            reverse("memorials:donate", args=[self.published.pk]),
            {"amount": "5", "donor_name": "Anna", "donor_email": "a@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Donation.objects.exists())

    def test_cannot_donate_to_draft_or_disabled(self):
        self.published.donations_enabled = False
        self.published.save()
        for memorial in (self.draft, self.published):
            response = self.client.get(reverse("memorials:donate", args=[memorial.pk]))
            self.assertEqual(response.status_code, 404)


@override_settings(PAYFAST_MODE="sandbox", PAYFAST_PASSPHRASE="secret")
class PayFastTests(MemorialTestBase):
    def setUp(self):
        super().setUp()
        self.gateway = PayFastGateway()

    def test_signature_is_stable_and_uses_passphrase(self):
        fields = OrderedDict([("merchant_id", "10000100"), ("amount", "100.00"), ("item_name", "A & B")])
        self.assertEqual(self.gateway.signature(fields), self.gateway.signature(dict(fields)))
        self.assertNotEqual(self.gateway.signature(fields), PayFastGateway(passphrase="").signature(fields))

    def test_sandbox_donation_renders_payfast_form(self):
        response = self.client.post(
            reverse("memorials:donate", args=[self.published.pk]),
            {"amount": "100", "donor_name": "Anna", "donor_email": "a@example.com"},
        )
        self.assertContains(response, "sandbox.payfast.co.za/eng/process")
        self.assertEqual(Donation.objects.get().status, Donation.Status.PENDING)

    def _itn(self, donation, **overrides):
        data = OrderedDict(
            [
                ("m_payment_id", str(donation.reference)),
                ("pf_payment_id", "123"),
                ("payment_status", "COMPLETE"),
                ("amount_gross", f"{donation.amount:.2f}"),
            ]
        )
        data.update(overrides)
        data["signature"] = self.gateway.signature(data)
        return data

    def test_valid_itn_completes_donation(self):
        donation = Donation.objects.create(
            memorial=self.published, donor_name="A", donor_email="a@example.com", amount=Decimal("100")
        )
        response = self.client.post(reverse("memorials:payfast_notify"), self._itn(donation))
        self.assertEqual(response.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.COMPLETED)
        self.assertEqual(donation.gateway_payment_id, "123")

    def test_tampered_itn_rejected(self):
        donation = Donation.objects.create(
            memorial=self.published, donor_name="A", donor_email="a@example.com", amount=Decimal("100")
        )
        data = self._itn(donation)
        data["amount_gross"] = "1.00"
        response = self.client.post(reverse("memorials:payfast_notify"), data)
        self.assertEqual(response.status_code, 400)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.PENDING)

    def test_wrong_amount_rejected_even_when_signed(self):
        donation = Donation.objects.create(
            memorial=self.published, donor_name="A", donor_email="a@example.com", amount=Decimal("100")
        )
        response = self.client.post(reverse("memorials:payfast_notify"), self._itn(donation, amount_gross="1.00"))
        self.assertEqual(response.status_code, 400)
