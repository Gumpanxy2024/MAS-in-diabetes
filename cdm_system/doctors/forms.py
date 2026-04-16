from django import forms

from patients.models import Patient
from .models import MedicationPlan


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["name", "age", "gender", "height", "diagnosis_year", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "height": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "diagnosis_year": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class MedicationPlanForm(forms.ModelForm):
    class Meta:
        model = MedicationPlan
        fields = [
            "drug_name", "dosage", "frequency",
            "remind_times", "total_days", "start_date", "is_active",
        ]
        widgets = {
            "drug_name": forms.TextInput(attrs={"class": "form-control"}),
            "dosage": forms.TextInput(attrs={"class": "form-control"}),
            "frequency": forms.TextInput(attrs={"class": "form-control", "placeholder": "如：每日2次"}),
            "remind_times": forms.TextInput(attrs={"class": "form-control", "placeholder": "08:00,20:00"}),
            "total_days": forms.NumberInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
