from django.db import models
from django.conf import settings

# ==========================================
# マスタテーブル定義
# ==========================================

# 8. 通知タイプマスタ (Notification.notification_type)
class NotificationTypeMaster(models.Model):
    """
    通知の種類（POP表示時の挙動制御用）定義
    例: info(一般), interview_invite(面談依頼)
    """
    code = models.CharField(max_length=30, unique=True, verbose_name="タイプコード")
    name = models.CharField(max_length=100, verbose_name="タイプ名")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "通知タイプマスタ"
        verbose_name_plural = "通知タイプマスタ"

# ==========================================
# メインモデル定義
# ==========================================

class Notification(models.Model):
    """
    ユーザーへの通知
    POP表示に対応するため、通知の種類と対象IDを保持する
    """
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name="通知先")
    title = models.CharField(max_length=100, verbose_name="タイトル")
    message = models.TextField(verbose_name="本文")
    
    # ★修正: CHOICESをForeignKeyに変更
    notification_type = models.ForeignKey(NotificationTypeMaster, on_delete=models.PROTECT, null=True, verbose_name="通知タイプ")
    
    related_object_id = models.IntegerField(null=True, blank=True, verbose_name="関連ID")
    link_url = models.CharField(max_length=200, blank=True, null=True, verbose_name="リンクURL")
    
    is_read = models.BooleanField(default=False, verbose_name="既読")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="通知日時")

    def __str__(self):
        return f"{self.title} -> {self.recipient}"

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知"
        ordering = ['-created_at']
