from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


INPUT_CLASSES = "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 shadow-sm focus:outline-none focus:ring-4 focus:ring-brandViolet/15 focus:border-brandViolet"


class HomeForm(forms.Form):
    query = forms.CharField(
        required=False,
        label="Recherche YouTube",
        widget=forms.TextInput(attrs={"placeholder": "Ex: Django tutorial FR", "class": INPUT_CLASSES})
    )
    url = forms.URLField(
        required=False,
        label="Lien YouTube",
        widget=forms.URLInput(attrs={"placeholder": "https://www.youtube.com/watch?v=...", "class": INPUT_CLASSES})
    )


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": INPUT_CLASSES}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": INPUT_CLASSES})
        self.fields["password1"].widget.attrs.update({"class": INPUT_CLASSES})
        self.fields["password2"].widget.attrs.update({"class": INPUT_CLASSES})
