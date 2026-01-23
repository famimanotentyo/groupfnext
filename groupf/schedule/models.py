from django.db import models
from django.conf import settings

# ==========================================
# マスタテーブル定義
# ==========================================

# 6. スケジュール種別マスタ (ScheduleEvent.event_type)
class ScheduleEventTypeMaster(models.Model):
    """
    予定の種類定義
    例: meeting(会議), vacation(休暇)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="種別コード")
    name = models.CharField(max_length=50, verbose_name="種別名")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "スケジュール種別マスタ"
        verbose_name_plural = "スケジュール種別マスタ"

# ==========================================
# メインモデル定義
# ==========================================

class ScheduleEvent(models.Model):
    """
    カレンダーに表示する「タスク以外の予定」
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schedule_events', verbose_name="ユーザー")
    title = models.CharField(max_length=100, verbose_name="予定タイトル")
    description = models.TextField(blank=True, verbose_name="詳細")
    
    start_at = models.DateTimeField(verbose_name="開始日時")
    end_at = models.DateTimeField(verbose_name="終了日時")
    
    # ★修正: CHOICESをForeignKeyに変更
    event_type = models.ForeignKey(ScheduleEventTypeMaster, on_delete=models.PROTECT, null=True, verbose_name="種類")
    
    CATEGORY_CHOICES = (
        ('personal', '個人的 (不在)'),
        ('work', '仕事 (予定あり)'),
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='work', verbose_name="カテゴリ")
    
    is_private = models.BooleanField(default=False, verbose_name="非公開")

    def __str__(self):
        return f"{self.title} ({self.user})"

    class Meta:
        verbose_name = "スケジュール"
        verbose_name_plural = "スケジュール"
