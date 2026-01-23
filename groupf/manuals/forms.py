from django import forms
from .models import Manual

class ManualCreateForm(forms.ModelForm):

    class Meta:
        model = Manual
        fields = ['title', 'description', 'file']
