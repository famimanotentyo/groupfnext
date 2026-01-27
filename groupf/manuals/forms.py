from django import forms
from .models import Manual

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True  # ★これが必須

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        # data は request.FILES.getlist(...) 相当で list になる
        if not data:
            return []

        # list/tuple のときは1個ずつ親の FileField.clean に流す
        if isinstance(data, (list, tuple)):
            parent_clean = super().clean  # ★内包表記の中で super() しない
            return [parent_clean(d, initial) for d in data]

        # 単体で来た場合も list にして返す
        return [super().clean(data, initial)]


class ManualFileUploadForm(forms.Form):
    files = MultipleFileField(
        required=True,
        label="ファイル",
        widget=MultipleFileInput(attrs={"multiple": True}),
    )

class ManualCreateForm(forms.ModelForm):

    class Meta:
        model = Manual
        fields = ['title', 'description', 'file']
