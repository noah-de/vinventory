from django import forms
from inventory.models import Server


class NewServerForm(forms.ModelForm):
    class Meta:
        model = Server

class EditServerForm(forms.ModelForm):
    class Meta:
        model = Server