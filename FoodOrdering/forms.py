from django import forms
from .models import TableReservation

class TableReservationForm(forms.ModelForm):
    class Meta:
        model = TableReservation
        fields = ["name", "email", "phone", "date", "time", "people", "message"]

    def clean_people(self):
        people = self.cleaned_data["people"]
        if people < 1 or people > 50:
            raise forms.ValidationError("Bitte geben Sie eine gültige Personenzahl an (1–50).")
        return people
