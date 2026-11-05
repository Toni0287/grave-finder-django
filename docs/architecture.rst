Architecture
============

Grave Finder is a server-rendered Django application made of three apps.

``accounts``
   A custom ``User`` model with a ``role`` field: *public* (families and
   visitors), *staff* (cemetery staff who manage grave records) and *admin*.
   Sign-up always creates public users; roles are changed in the admin site.

``cemeteries``
   ``Cemetery`` and ``Grave`` models, the search page, grave detail page with
   a Leaflet map and turn-by-turn directions (OSRM via Leaflet Routing
   Machine), a printable record, the cemetery list and the statistics
   dashboard. Graves are soft-deleted (``deleted_at``) so nothing is ever lost.

``memorials``
   ``Memorial`` pages (draft → published → archived), ``Condolence`` messages
   and ``Donation`` records. Payments go through ``PayFastGateway``; card
   details never touch this server.

Request flow
------------

.. code-block:: text

   Browser ──► Django URLconf ──► view ──► form / service class ──► ORM ──► SQLite
                                      └──► template (Bootstrap 5 + Leaflet)

Donation flow
-------------

1. Donor fills in the donation form; a ``Donation`` is saved as *pending*.
2. ``PAYFAST_MODE=demo``: the donation is completed immediately.
   ``sandbox`` / ``live``: the donor is sent to PayFast with a signed form.
3. PayFast calls ``/memorials/payfast/notify/``. The view checks the
   signature and the amount, then marks the donation *completed*.
4. If the donor left a message it is posted as a condolence.

The platform keeps ``DONATION_PLATFORM_FEE`` (5%); the rest goes to the family.

Design choices
--------------

* **Service classes** (``DashboardStats``, ``PayFastGateway``) keep business
  logic out of views so it can be unit tested on its own.
* **QuerySet methods** (``Grave.objects.active()``,
  ``Memorial.objects.visible_to(user)``) put access rules in one place.
* **Semantic HTML and Bootstrap** for accessible, responsive pages; maps
  degrade to a Google Maps link when location access is refused.
