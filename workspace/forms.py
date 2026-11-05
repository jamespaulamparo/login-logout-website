from django import forms
from .models import Entry

class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ["title", "category", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Community issue report"}),
            "category": forms.TextInput(attrs={"placeholder": "e.g. Operations"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Add a short description..."}),
        }
