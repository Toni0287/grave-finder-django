"""PayFast payment gateway.

Card details are never collected by Grave Finder. In ``sandbox`` and ``live``
mode the donor is sent to PayFast's hosted payment page and PayFast tells us
the result through an ITN (Instant Transaction Notification) call. In
``demo`` mode no money moves and donations complete immediately, which is
handy for presentations and tests.
"""

import hashlib
from urllib.parse import quote_plus

from django.conf import settings

# Field order PayFast uses when it builds its own signature.
CHECKOUT_FIELD_ORDER = [
    "merchant_id", "merchant_key", "return_url", "cancel_url", "notify_url",
    "name_first", "email_address", "m_payment_id", "amount", "item_name",
]


class PayFastGateway:
    """Builds PayFast checkout forms and checks ITN signatures."""

    HOSTS = {"sandbox": "sandbox.payfast.co.za", "live": "www.payfast.co.za"}

    def __init__(self, mode=None, merchant_id=None, merchant_key=None, passphrase=None):
        self.mode = mode or settings.PAYFAST_MODE
        self.merchant_id = merchant_id or settings.PAYFAST_MERCHANT_ID
        self.merchant_key = merchant_key or settings.PAYFAST_MERCHANT_KEY
        self.passphrase = settings.PAYFAST_PASSPHRASE if passphrase is None else passphrase

    @property
    def is_demo(self):
        return self.mode == "demo"

    @property
    def process_url(self):
        return f"https://{self.HOSTS.get(self.mode, self.HOSTS['sandbox'])}/eng/process"

    def signature(self, fields):
        """MD5 signature over the non-empty fields, in the order given."""
        pairs = [
            f"{key}={quote_plus(str(value).strip())}"
            for key, value in fields.items()
            if key != "signature" and value not in ("", None)
        ]
        if self.passphrase:
            pairs.append(f"passphrase={quote_plus(self.passphrase.strip())}")
        return hashlib.md5("&".join(pairs).encode()).hexdigest()

    def checkout_fields(self, donation, return_url, cancel_url, notify_url):
        """The hidden form fields that send the donor to PayFast."""
        values = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": return_url,
            "cancel_url": cancel_url,
            "notify_url": notify_url,
            "name_first": donation.donor_name,
            "email_address": donation.donor_email,
            "m_payment_id": str(donation.reference),
            "amount": f"{donation.amount:.2f}",
            "item_name": f"Donation in memory of {donation.memorial.full_name}"[:100],
        }
        fields = {key: values[key] for key in CHECKOUT_FIELD_ORDER}
        fields["signature"] = self.signature(fields)
        return fields

    def is_valid_notification(self, data):
        """True when an ITN's signature matches its data.

        ``data`` keeps the order PayFast posted the fields in, which the
        signature depends on.
        """
        received = data.get("signature", "")
        # .items() gives single values for a QueryDict (dict() would give lists).
        fields = {key: value for key, value in data.items()}
        return bool(received) and received == self.signature(fields)
