from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import TableReservation

class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form matching the website design."""
    username = forms.CharField(
        label="Benutzername",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Benutzername',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="Passwort",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Passwort',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        label="Angemeldet bleiben",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

class TableReservationForm(forms.ModelForm):
    class Meta:
        model = TableReservation
        fields = ["name", "email", "phone", "date", "time", "people", "message"]

    def clean_people(self):
        people = self.cleaned_data["people"]
        if people < 1 or people > 50:
            raise forms.ValidationError("Bitte geben Sie eine gültige Personenzahl an (1–50).")
        return people
