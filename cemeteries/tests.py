from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .forms import GraveForm, GraveSearchForm
from .models import Cemetery, Grave
from .stats import DashboardStats


def make_cemetery(name="Maitland Cemetery", type_="public", **extra):
    return Cemetery.objects.create(
        name=name, type=type_, latitude=-33.9, longitude=18.5, capacity=100, available_plots=25, **extra
    )


def make_grave(cemetery, first="Thandi", surname="Dlamini", number="G1", **extra):
    defaults = dict(
        date_of_death=date(2015, 6, 1), age_at_death=70, latitude=-33.9, longitude=18.5, section="A", plot="12"
    )
    defaults.update(extra)
    return Grave.objects.create(
        cemetery=cemetery, first_name=first, surname=surname, grave_number=number, **defaults
    )


class ModelTests(TestCase):
    def setUp(self):
        self.cemetery = make_cemetery()
        self.grave = make_grave(self.cemetery)

    def test_location_label(self):
        self.assertEqual(self.grave.location_label, "Section A, Plot 12, Grave G1")

    def test_occupancy_percent(self):
        self.assertEqual(self.cemetery.occupancy_percent, 75)
        self.assertEqual(Cemetery(capacity=0).occupancy_percent, 0)

    def test_soft_deleted_graves_are_not_active(self):
        from django.utils import timezone

        self.grave.deleted_at = timezone.now()
        self.grave.save()
        self.assertFalse(Grave.objects.active().exists())
        self.assertTrue(Grave.objects.exists())

    def test_map_marker(self):
        marker = self.grave.map_marker()
        self.assertEqual(marker["name"], "Thandi Dlamini")
        self.assertEqual(marker["url"], reverse("cemeteries:grave_detail", args=[self.grave.pk]))


class SearchFormTests(TestCase):
    def setUp(self):
        self.public = make_cemetery()
        self.private = make_cemetery("Constantia Memorial Gardens", "private")
        make_grave(self.public, "Thandi", "Dlamini", "G1", age_at_death=70)
        make_grave(self.public, "Sipho", "Ndlovu", "G2", age_at_death=30)
        make_grave(self.private, "Anna", "Botha", "G3", age_at_death=85, date_of_death=date(2020, 1, 5))

    def search(self, **data):
        form = GraveSearchForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        return list(form.filter(Grave.objects.active()).values_list("grave_number", flat=True))

    def test_partial_case_insensitive_name(self):
        self.assertEqual(self.search(surname="dlam"), ["G1"])

    def test_cemetery_type(self):
        self.assertEqual(self.search(cemetery_type="private"), ["G3"])

    def test_age_range(self):
        self.assertEqual(sorted(self.search(min_age=60, max_age=80)), ["G1"])

    def test_year_of_death(self):
        self.assertEqual(self.search(year_of_death=2020), ["G3"])

    def test_min_age_above_max_age_is_invalid(self):
        self.assertFalse(GraveSearchForm({"min_age": 80, "max_age": 20}).is_valid())

    def test_empty_form_has_no_filters(self):
        self.assertFalse(GraveSearchForm({}).has_filters())


class GraveFormTests(TestCase):
    def test_burial_before_death_is_rejected(self):
        cemetery = make_cemetery()
        form = GraveForm(
            {
                "cemetery": cemetery.pk,
                "first_name": "A",
                "surname": "B",
                "date_of_death": "2020-05-10",
                "date_of_burial": "2020-05-01",
                "grave_number": "X1",
                "plot_size": "Single",
                "latitude": -33.9,
                "longitude": 18.5,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("date_of_burial", form.errors)


class PublicViewTests(TestCase):
    def setUp(self):
        self.cemetery = make_cemetery()
        self.grave = make_grave(self.cemetery)

    def test_search_page_without_query(self):
        response = self.client.get(reverse("cemeteries:search"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["page"])

    def test_search_returns_matches(self):
        response = self.client.get(reverse("cemeteries:search"), {"surname": "Dlamini"})
        self.assertContains(response, "Thandi Dlamini")
        self.assertEqual(len(response.context["markers"]), 1)

    def test_search_no_matches(self):
        response = self.client.get(reverse("cemeteries:search"), {"surname": "Nobody"})
        self.assertContains(response, "No graves found")

    def test_grave_detail_and_print(self):
        for name in ("grave_detail", "grave_print"):
            response = self.client.get(reverse(f"cemeteries:{name}", args=[self.grave.pk]))
            self.assertContains(response, "Thandi Dlamini")

    def test_deleted_grave_is_404(self):
        from django.utils import timezone

        self.grave.deleted_at = timezone.now()
        self.grave.save()
        response = self.client.get(reverse("cemeteries:grave_detail", args=[self.grave.pk]))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_and_cemetery_list(self):
        self.assertContains(self.client.get(reverse("cemeteries:dashboard")), "Burials per year")
        self.assertContains(self.client.get(reverse("cemeteries:cemetery_list")), "Maitland Cemetery")


class StaffViewTests(TestCase):
    def setUp(self):
        self.cemetery = make_cemetery()
        self.grave = make_grave(self.cemetery)
        self.public = User.objects.create_user("pub", password="pw-12345-x")
        self.staff = User.objects.create_user("staff", password="pw-12345-x", role=User.Role.STAFF)

    def test_public_user_cannot_add_graves(self):
        self.client.force_login(self.public)
        response = self.client.get(reverse("cemeteries:grave_create"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_soft_delete(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("cemeteries:grave_delete", args=[self.grave.pk]))
        self.assertRedirects(response, reverse("cemeteries:search"))
        self.grave.refresh_from_db()
        self.assertIsNotNone(self.grave.deleted_at)

    def test_staff_can_edit(self):
        self.client.force_login(self.staff)
        url = reverse("cemeteries:grave_update", args=[self.grave.pk])
        data = {k: v for k, v in GraveForm(instance=self.grave).initial.items() if v is not None}
        data.update(first_name="Thandeka")
        response = self.client.post(url, data)
        self.assertRedirects(response, self.grave.get_absolute_url())
        self.grave.refresh_from_db()
        self.assertEqual(self.grave.first_name, "Thandeka")


class StatsAndSeedTests(TestCase):
    def test_seed_is_deterministic_and_stats_add_up(self):
        call_command("seed_graves", per_cemetery=5, stdout=StringIO())
        first = list(Grave.objects.order_by("grave_number").values_list("surname", flat=True))
        call_command("seed_graves", per_cemetery=5, reset=True, stdout=StringIO())
        second = list(Grave.objects.order_by("grave_number").values_list("surname", flat=True))
        self.assertEqual(first, second)

        totals = DashboardStats().totals()
        self.assertEqual(totals["graves"], 60)
        self.assertEqual(totals["cemeteries"], 12)
        self.assertEqual(totals["public"] + totals["private"], 12)
        self.assertEqual(sum(r["count"] for r in DashboardStats().burials_per_year()), 60)
