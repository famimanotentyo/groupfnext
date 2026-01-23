from django.db import models
from django.conf import settings

# ==========================================
# マスタテーブル定義
# ==========================================

# 7. 面談状態マスタ (Interview.status)
class InterviewStatusMaster(models.Model):
    """
    面談の進行・承認状態定義
    例: tentative(仮予約), confirmed(確定)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="状態コード")
    name = models.CharField(max_length=50, verbose_name="状態名")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "面談状態マスタ"
        verbose_name_plural = "面談状態マスタ"

# ==========================================
# メインモデル定義
# ==========================================

class Interview(models.Model):
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conducted_interviews', verbose_name="担当上司")
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_interviews', verbose_name="対象部下")
    
    scheduled_at = models.DateTimeField(verbose_name="面談日時")
    end_at = models.DateTimeField(verbose_name="終了日時", null=True, blank=True)
    
    notes = models.TextField(blank=True, verbose_name="面談メモ")
    
    status = models.ForeignKey(InterviewStatusMaster, on_delete=models.PROTECT, null=True, verbose_name="状態")

    # ★追加: 面談テーマとAI生成スクリプト
    theme = models.CharField(max_length=100, blank=True, verbose_name="面談テーマ")
    location = models.CharField(max_length=100, blank=True, verbose_name="場所")
    script_generated = models.TextField(blank=True, null=True, verbose_name="AI生成スクリプト")

    def __str__(self):
        return f"面談: {self.manager} - {self.employee} ({self.scheduled_at})"

    class Meta:
        verbose_name = "面談"
        verbose_name_plural = "面談"

class InterviewFeedback(models.Model):
    """
    面談後のフィードバック情報
    """
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='feedback', verbose_name="対象面談")
    
    EVALUATION_CHOICES = [
        (3, 'うまくいった'),
        (2, '普通・保留'),
        (1, '失敗・イマイチ'),
    ]
    evaluation = models.IntegerField(choices=EVALUATION_CHOICES, verbose_name="総合評価")
    
    # 部下の反応タグ（例: ["納得した", "感謝された"]）をリストで保存
    tags = models.JSONField(default=list, verbose_name="反応タグ")
    
    memo = models.TextField(blank=True, verbose_name="一言メモ")
    
    # このFBを受けてAIがどう分析したかのログ（デバッグ・履歴用）
    ai_analysis_log = models.TextField(blank=True, null=True, verbose_name="AI分析ログ")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FB: {self.interview}"
    class Meta:
        verbose_name = "面談フィードバック"
        verbose_name_plural = "面談フィードバック"

class MemberAnalysis(models.Model):
    """
    部下のAI分析データ（取扱説明書）
    """
    target_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='member_analysis', verbose_name="対象部下")
    
    # AIが生成した分析テキスト（Markdown形式想定）
    analysis_text = models.TextField(blank=True, verbose_name="AI分析テキスト（取説）")
    
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最終更新日時")

    def __str__(self):
        return f"分析: {self.target_user}"
    class Meta:
        verbose_name = "部下分析データ"
        verbose_name_plural = "部下分析データ"
