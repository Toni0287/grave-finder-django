"""Load the 12 Cape Town cemeteries and generate demo grave records.

The generator uses a fixed random seed, so every run creates the same data.

Usage::

    python manage.py seed_graves            # 100 graves per cemetery
    python manage.py seed_graves --per-cemetery 20
    python manage.py seed_graves --reset    # delete graves first
"""

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from cemeteries.models import Cemetery, Grave

CEMETERIES = [
    ("Maitland Cemetery", "public", "Voortrekker Road, Maitland, Cape Town, 7405", -33.91592, 18.52805, 5000, 420, "Historic public cemetery established in 1884"),
    ("Woltemade Cemetery", "public", "Koeberg Road, Goodwood, Cape Town, 7460", -33.914, 18.540, 6000, 580, "Large public cemetery serving the northern suburbs, established 1886"),
    ("Plumstead Cemetery", "public", "Victoria Road, Plumstead, Cape Town, 7800", -34.0139, 18.4746, 3000, 210, "Public cemetery in the southern suburbs"),
    ("Mowbray Cemetery", "public", "10 Browning Road, Observatory, Cape Town, 7925", -33.9413, 18.4710, 2500, 180, "Historic public cemetery near Groote Schuur Hospital"),
    ("Somerset West Public Cemetery", "public", "Van Riebeeck Street, Somerset West, 7130", -34.0856, 18.8493, 2000, 320, "Public cemetery serving Somerset West and surrounds"),
    ("Eerste River Cemetery", "public", "Spine Road, Eerste River, Cape Town, 7100", -34.0048, 18.6189, 3500, 460, "Public cemetery in the Cape Flats area"),
    ("Gardens of Peace Memorial Park", "private", "Bottelary Road, Kraaifontein, Cape Town, 7570", -33.8587, 18.7089, 4000, 220, "Private memorial park with beautiful landscaping"),
    ("Welmoed Memorial Park", "private", "Welmoed Road, Kuils River, Cape Town, 7580", -33.9789, 18.6912, 3000, 175, "Peaceful private memorial park"),
    ("Meadowridge Memorial Park", "private", "Main Road, Meadowridge, Cape Town, 7800", -34.0289, 18.4856, 2500, 190, "Private park with scenic mountain views"),
    ("Durbanville Memorial Park", "private", "Wellington Road, Durbanville, Cape Town, 7550", -33.8342, 18.6523, 3500, 310, "Modern private memorial park in wine country"),
    ("Constantia Memorial Gardens", "private", "Constantia Main Road, Constantia, Cape Town, 7806", -34.0178, 18.4289, 2000, 145, "Exclusive private memorial gardens"),
    ("Bellville Memorial Estate", "private", "De La Rey Road, Bellville, Cape Town, 7530", -33.8892, 18.6287, 3000, 267, "Private memorial estate with chapel facilities"),
]

FIRST_NAMES = [
    "Sipho", "Thabo", "Mandla", "Bongani", "Lungelo", "Sibusiso", "Nkosinathi", "Sandile", "Andile",
    "Siyabonga", "Nhlanhla", "Ayanda", "Xolani", "Vuyani", "Johannes", "Pieter", "Johan", "Marius",
    "David", "Mohammed", "Hassan", "Yusuf", "Abdullah", "Michael", "Robert", "George", "William",
    "James", "Peter", "John", "Tshepo", "Kagiso", "Mpho", "Kabelo", "Zolani", "Nokuthula", "Thandi",
    "Zanele", "Nomcebo", "Lindiwe", "Busisiwe", "Nomvula", "Nozipho", "Zinhle", "Nthabiseng",
    "Vuyiswa", "Maria", "Anna", "Jennifer", "Linda", "Margaret", "Patricia", "Fatima", "Aisha",
    "Naziema", "Gadija", "Mariam", "Sarah", "Elizabeth", "Grace", "Sibongile", "Nomsa", "Precious",
]
SURNAMES = [
    "Dlamini", "Ndlovu", "Khumalo", "Mthembu", "Nkosi", "Shabalala", "Sithole", "Gumede", "Ngcobo",
    "Mkhize", "Van der Merwe", "De Bruyn", "Botha", "Pretorius", "Muller", "Nel", "Jacobs",
    "September", "Hendricks", "October", "Williams", "Adams", "February", "Christians", "Davids",
    "Isaacs", "Phillips", "Petersen", "Abrahams", "Smith", "Jones", "Brown", "Jansen", "Paulsen",
    "Samuels", "Johnson", "Thomas", "Martin", "Zulu", "Mathebula", "Mazibuko", "Mbatha", "Cele",
    "Buthelezi", "Ntuli", "Toni",
]
SECTIONS = ["A", "B", "C", "D", "E"]


class Command(BaseCommand):
    help = "Create the Cape Town cemeteries and deterministic demo grave records."

    def add_arguments(self, parser):
        parser.add_argument("--per-cemetery", type=int, default=100)
        parser.add_argument("--reset", action="store_true", help="Delete existing graves first.")

    @transaction.atomic
    def handle(self, *args, per_cemetery, reset, **options):
        cemeteries = [self.upsert_cemetery(row) for row in CEMETERIES]
        self.stdout.write(f"Cemeteries: {len(cemeteries)} ready")

        if reset:
            Grave.objects.all().delete()
        if Grave.objects.exists():
            self.stdout.write("Graves already exist; use --reset to regenerate.")
            return

        rng = random.Random(42)
        graves = []
        for ci, cemetery in enumerate(cemeteries):
            for gi in range(per_cemetery):
                graves.append(self.make_grave(rng, cemetery, ci * per_cemetery + gi + 1))
        Grave.objects.bulk_create(graves)
        self.stdout.write(self.style.SUCCESS(f"Graves: {len(graves)} created"))

    @staticmethod
    def upsert_cemetery(row):
        name, type_, address, lat, lng, capacity, available, description = row
        cemetery, _ = Cemetery.objects.update_or_create(
            name=name,
            defaults={
                "type": type_,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "capacity": capacity,
                "available_plots": available,
                "description": description,
            },
        )
        return cemetery

    @staticmethod
    def make_grave(rng, cemetery, number):
        age = rng.randint(18, 95)
        death = date(2010, 1, 1) + timedelta(days=rng.randint(0, 365 * 15))
        return Grave(
            cemetery=cemetery,
            first_name=rng.choice(FIRST_NAMES),
            surname=rng.choice(SURNAMES),
            age_at_death=age,
            birth_year=death.year - age,
            date_of_death=death,
            date_of_burial=death + timedelta(days=rng.randint(3, 14)),
            section=rng.choice(SECTIONS),
            plot=str(rng.randint(1, 250)),
            grave_number=f"G{number:05d}",
            plot_size=rng.choice(Grave.PlotSize.values),
            # Spread graves a few hundred metres around the cemetery entrance.
            latitude=cemetery.latitude + rng.uniform(-0.0015, 0.0015),
            longitude=cemetery.longitude + rng.uniform(-0.0015, 0.0015),
        )
