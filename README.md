# Grave Finder (Django)

Find a loved one's grave in Cape Town cemeteries, get directions to the exact plot, and keep a memorial page where friends can leave condolences and donate to support the family.

This is a rebuild of the original vanilla JS + Express Grave Finder. It uses Django, Bootstrap 5, unit tests, Docker and Sphinx docs, following the practices from the Stellenbosch AI & Software Engineering bootcamp (Level 2).

## Features

| Area | What it does |
| --- | --- |
| **Search** | Partial, case-insensitive name search; filter by cemetery, public/private, age range and year of death; results paginated and pinned on a map; breakdown by cemetery |
| **Grave page** | Full burial details, Leaflet map, directions from your location (OSRM), Google Maps fallback, printable record, share button |
| **Cemeteries** | Map of all 12 cemeteries with capacity bars |
| **Dashboard** | Totals, burials per year chart, plot sizes, records and capacity per cemetery |
| **Memorials** | Create a memorial (optionally linked to a grave), keep it as a draft, publish, edit; visitors leave condolences |
| **Donations** | Preset or custom amounts (R10 minimum), anonymous option, message posted to the memorial; 5% platform fee shown up front; PayFast hosted checkout (demo, sandbox or live) |
| **Accounts** | Sign up / log in; roles: public, cemetery staff (add, edit, soft-delete graves), admin |

## Quick start (WSL / Linux)

```bash
cd ~/grave-finder-django
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_graves        # 12 cemeteries, 1,200 graves
python manage.py seed_memorials     # one demo memorial with donations
python manage.py createsuperuser    # for /admin and staff features
python manage.py runserver
```

Open http://127.0.0.1:8000.

To make someone cemetery staff, open **Admin → Users**, pick the user and set **Role** to *Cemetery staff*.

## Run with Docker

```bash
docker compose up --build
```

The container migrates, seeds demo data and serves the app with gunicorn on port 8000. The SQLite database lives in the `gravefinder_data` volume.

## Tests

```bash
python manage.py test
```

49 tests cover models, search filters, permissions, staff editing, soft deletes, memorial visibility, the donation fee split, PayFast signatures and ITN handling, and the seed command.

## Documentation

```bash
pip install -r requirements-dev.txt
sphinx-build -b html docs docs/_build
```

See `docs/architecture.rst` for how the apps fit together.

## Configuration

Copy `.env.example` and set the values as environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | dev key | **Must** be set in production |
| `DJANGO_DEBUG` | `true` | Set `false` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Comma separated |
| `PAYFAST_MODE` | `demo` | `demo` completes donations instantly, `sandbox` / `live` use PayFast |
| `PAYFAST_MERCHANT_ID` / `_KEY` / `_PASSPHRASE` | PayFast sandbox test merchant | Your PayFast credentials |
| `DONATION_PLATFORM_FEE` | `0.05` | Share kept by the platform |

## Project layout

```
accounts/      custom User model with roles, sign-up, profile
cemeteries/    Cemetery + Grave models, search, maps, dashboard, seed_graves command
memorials/     Memorial, Condolence, Donation, PayFastGateway, seed_memorials command
templates/     Bootstrap templates (semantic HTML)
static/        site.css, maps.js (Leaflet helpers)
docs/          Sphinx documentation
```

## What changed from the original app

* Express + raw SQL → Django ORM with migrations, forms and the admin site.
* JWT auth → Django sessions with CSRF protection and role checks on every staff action.
* Card numbers were typed into our own form → PayFast hosted checkout; we never see card details.
* In-browser state → server-side pagination and validation.
* No tests → 49 unit and integration tests.
* Separate `memorial-platform` folder → one app sharing the same users and grave records.
