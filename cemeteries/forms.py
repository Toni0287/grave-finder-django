from django import forms

from .models import Cemetery, Grave


class GraveSearchForm(forms.Form):
    """Search filters for grave records. Every field is optional."""

    first_name = forms.CharField(required=False, max_length=100)
    surname = forms.CharField(required=False, max_length=100)
    cemetery = forms.ModelChoiceField(
        queryset=Cemetery.objects.all(), required=False, empty_label="All cemeteries"
    )
    cemetery_type = forms.ChoiceField(
        required=False, choices=[("", "Public and private")] + list(Cemetery.Type.choices)
    )
    min_age = forms.IntegerField(required=False, min_value=0, max_value=130)
    max_age = forms.IntegerField(required=False, min_value=0, max_value=130)
    year_of_death = forms.IntegerField(required=False, min_value=1800, max_value=2100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_age"), cleaned.get("max_age")
        if low is not None and high is not None and low > high:
            raise forms.ValidationError("Minimum age cannot be more than maximum age.")
        return cleaned

    def has_filters(self):
        """True when the user filled in at least one field."""
        return self.is_valid() and any(v not in (None, "") for v in self.cleaned_data.values())

    def filter(self, queryset):
        """Apply the cleaned filters to a ``Grave`` queryset."""
        data = self.cleaned_data
        if data.get("first_name"):
            queryset = queryset.filter(first_name__icontains=data["first_name"].strip())
        if data.get("surname"):
            queryset = queryset.filter(surname__icontains=data["surname"].strip())
        if data.get("cemetery"):
            queryset = queryset.filter(cemetery=data["cemetery"])
        if data.get("cemetery_type"):
            queryset = queryset.filter(cemetery__type=data["cemetery_type"])
        if data.get("min_age") is not None:
            queryset = queryset.filter(age_at_death__gte=data["min_age"])
        if data.get("max_age") is not None:
            queryset = queryset.filter(age_at_death__lte=data["max_age"])
        if data.get("year_of_death"):
            queryset = queryset.filter(date_of_death__year=data["year_of_death"])
        return queryset


class GraveForm(forms.ModelForm):
    """Used by cemetery staff to add or edit a grave record."""

    class Meta:
        model = Grave
        exclude = ("created_at", "updated_at", "deleted_at")
        widgets = {
            "date_of_death": forms.DateInput(attrs={"type": "date"}),
            "date_of_burial": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        cleaned = super().clean()
        death, burial = cleaned.get("date_of_death"), cleaned.get("date_of_burial")
        if death and burial and burial < death:
            self.add_error("date_of_burial", "Burial cannot be before the date of death.")
        return cleaned
