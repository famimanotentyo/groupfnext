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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input' # Checkbox style
            else:
                field.widget.attrs['class'] = 'form-control'
        
        # マネージャーの場合は「役割・権限」を変更不可にする
        if user and user.role.code == 'manager':
            self.fields['role'].disabled = True
            self.fields['department'].disabled = True
            self.fields['is_active'].disabled = True

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

class PasswordResetRequestForm(forms.Form):
    """パスワードリセット申請フォーム"""
    employee_number = forms.CharField(
        label='社員番号',
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '社員番号', 'class': 'form-control'})
    )
    
    manager = forms.ModelChoiceField(
        label='送信先上司を選択',
        queryset=User.objects.none(), # __init__でセットする
        empty_label="上司を選択してください",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # manager権限（またはそれ以上）を持つユーザーをプルダウンに表示
        # role.code で判別 (admin, manager, etc.)
        # 必要に応じて 'admin' も含めるかどうか検討。今回は 'manager' 以上とする。
        self.fields['manager'].queryset = User.objects.filter(
            is_active=True,
            role__code__in=['manager', 'admin']
        ).order_by('last_name', 'first_name')

    def clean_employee_number(self):
        emp_num = self.cleaned_data.get('employee_number')
        if not User.objects.filter(employee_number=emp_num, is_active=True).exists():
            raise forms.ValidationError('指定された社員番号のユーザーは見つかりません。')
        return emp_num
