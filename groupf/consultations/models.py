from django.db import models
from django.conf import settings

# ==========================================
# マスタテーブル定義
# ==========================================

# 3. 相談状態マスタ (Consultation.status)
class ConsultationStatusMaster(models.Model):
    """
    相談の解決状態定義
    例: open(解決中), resolved(解決済み)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="状態コード")
    name = models.CharField(max_length=50, verbose_name="状態名")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "相談状態マスタ"
        verbose_name_plural = "相談状態マスタ"

# ==========================================
# メインモデル定義
# ==========================================

class Consultation(models.Model):
    """
    「詳しい人に質問する」ための専用チャットセッション
    """
    title = models.CharField(max_length=200, verbose_name="相談タイトル")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requested_consultations', verbose_name="質問者")
    respondent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='responded_consultations', verbose_name="回答者")
    
    # ★修正: CHOICESをForeignKeyに変更
    status = models.ForeignKey(ConsultationStatusMaster, on_delete=models.PROTECT, null=True, verbose_name="状態")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.requester} -> {self.respondent})"

class ConsultationMessage(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="メッセージ内容")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class Question(models.Model):
    """
    Consultation解決後にGeminiが生成するナレッジ
    """
    source_consultation = models.OneToOneField(Consultation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="元チャット")
    title = models.CharField(max_length=200, verbose_name="質問タイトル(要約)")
    problem_summary = models.TextField(verbose_name="課題・質問内容")
    solution_summary = models.TextField(verbose_name="解決策・操作手順")
    
    # Tag is in tasks app. Use 'tasks.Tag'
    tags = models.ManyToManyField('tasks.Tag', blank=True, related_name='questions', verbose_name="関連タグ")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="作成者")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "ナレッジ(解決済質問)"
        verbose_name_plural = "ナレッジ(解決済質問)"
