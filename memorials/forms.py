from django import forms
from django.conf import settings

from cemeteries.models import Grave

from .models import Condolence, Donation, Memorial

PRESET_AMOUNTS = [100, 250, 500, 1000]


class BootstrapMixin:
    """Adds Bootstrap classes to every widget."""

    def _style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class MemorialForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Memorial
        fields = (
            "full_name", "birth_date", "death_date", "tagline", "biography",
            "photo_url", "grave", "donations_enabled",
        )
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "death_date": forms.DateInput(attrs={"type": "date"}),
            "biography": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grave"].queryset = Grave.objects.active().select_related("cemetery")
        self.fields["grave"].required = False
        self.fields["grave"].help_text = "Optional: link this memorial to a grave record."
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        born, died = cleaned.get("birth_date"), cleaned.get("death_date")
        if born and died and died < born:
            self.add_error("death_date", "Date of passing cannot be before the date of birth.")
        return cleaned


class CondolenceForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Condolence
        fields = ("author_name", "message")
        labels = {"author_name": "Your name", "message": "Your message"}
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class DonationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Donation
        fields = ("amount", "donor_name", "donor_email", "is_anonymous", "message")
        labels = {
            "amount": "Amount (R)",
            "donor_name": "Your name",
            "donor_email": "Your email",
            "is_anonymous": "Hide my name on the memorial",
            "message": "Message to the family (optional)",
        }
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"].widget.attrs.update({"min": settings.DONATION_MINIMUM, "step": "1"})
        self._style_fields()

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < settings.DONATION_MINIMUM:
            raise forms.ValidationError(f"The minimum donation is R{settings.DONATION_MINIMUM:.0f}.")
        return amount
