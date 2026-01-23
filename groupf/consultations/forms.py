from django import forms
from django.contrib.auth import get_user_model
from .models import Consultation, ConsultationMessage

User = get_user_model()

class ConsultationCreateForm(forms.ModelForm):
    """
    新規相談作成フォーム
    """
    class Meta:
        model = Consultation
        fields = ['title', 'respondent'] 
        labels = {
            'title': '相談タイトル',
            'respondent': '相談する相手（詳しい人）',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user') 
        super().__init__(*args, **kwargs)
        self.fields['respondent'].queryset = User.objects.filter(is_active=True).exclude(id=user.id)
        self.fields['title'].widget.attrs['class'] = 'form-control'
        self.fields['respondent'].widget.attrs['class'] = 'form-select'

class ConsultationMessageForm(forms.ModelForm):
    """
    チャットメッセージ送信フォーム
    """
    class Meta:
        model = ConsultationMessage
        fields = ['content']
        labels = {'content': ''} 
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'メッセージを入力...'
            }),
        }
