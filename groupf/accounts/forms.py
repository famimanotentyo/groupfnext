from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'last_name', 'first_name', 
            'last_name_kana', 'first_name_kana', 
            'email',
            'phone_number', 'avatar'
        ]
        labels = {
            'last_name': '姓',
            'first_name': '名',
            'last_name_kana': '姓（カナ）',
            'first_name_kana': '名（カナ）',
            'email': 'メールアドレス',
            'phone_number': '電話番号',
            'avatar': 'アイコン画像',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class AccountAdminEditForm(forms.ModelForm):
    """管理者用アカウント編集フォーム"""
    class Meta:
        model = User
        fields = [
            'last_name', 'first_name',
            'last_name_kana', 'first_name_kana',
            'department', 'role',
            'email', 'employee_number',
            'is_active',
            'hire_date', 'birth_date'
        ]
        labels = {
            'last_name': '姓',
            'first_name': '名',
            'last_name_kana': '姓（カナ）',
            'first_name_kana': '名（カナ）',
            'department': '所属部署',
            'role': '役割・権限',
            'email': 'メールアドレス',
            'employee_number': '社員番号',
            'is_active': 'アカウント状態（有効/無効）',
            'hire_date': '入社日',
            'birth_date': '生年月日',
        }
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input' # Checkbox style
            else:
                field.widget.attrs['class'] = 'form-control'

from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    # AuthenticationForm expects 'username' field, but our model uses 'employee_number'.
    # We can alias it or just use 'username' field which AuthenticationForm provides by default.
    # However, to keep the UI 'employee_id' label consistent:
    
    username = forms.CharField(
        label='社員番号',
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': '社員番号を入力', 'class': 'form-field'})
    )
    password = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={'placeholder': 'パスワードを入力', 'class': 'form-field'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # フォームのフィールドクラスをBootstrap用に調整
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-field'
    
    # AuthenticationForm already has a clean() method that authenticates.
    # We don't need to override it if we use standard authentication backend.

