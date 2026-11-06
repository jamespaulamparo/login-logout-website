from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Entry

User = get_user_model()


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ["title", "category", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Community issue report"}),
            "category": forms.TextInput(attrs={"placeholder": "e.g. Operations"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Add a short description..."}),
        }


class RegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Choose a username", "autocomplete": "username"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Create a strong password", "autocomplete": "new-password"}),
        help_text="At least 8 characters, avoiding common passwords."
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Re-enter your password", "autocomplete": "new-password"})
    )

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists. Please sign in instead.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                validate_password(password)
        return cleaned_data


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        label="Verification Code",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "placeholder": "123456",
            "maxlength": "6",
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "autofocus": "autofocus",
            "class": "otp-input"
        })
    )

    def clean_otp_code(self):
        code = self.cleaned_data.get("otp_code", "").strip()
        if not code.isdigit() or len(code) != 6:
            raise ValidationError("Please enter the 6-digit verification code.")
        return code
