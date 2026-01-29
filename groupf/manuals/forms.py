from django import forms
from .models import Manual

# ✅ 複数選択を許可する ClearableFileInput
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

# ✅ 複数ファイルを受け取れる FileField
class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        # required=False のとき data が None になるので空リストを返す
        if not data:
            return []

        # ✅ ここが超重要：list comprehension 内で super() を直呼びすると TypeError になりやすい
        parent_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [parent_clean(d, initial) for d in data]

        return [parent_clean(data, initial)]

class ManualFileUploadForm(forms.Form):
    files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True})
    )

class ManualCreateForm(forms.ModelForm):
    class Meta:
        # ここはあなたの Manual モデルに合わせて
        # model = Manual を書いてください（省略してるなら書く）
        model = Manual
        fields = ["title", "description"]
