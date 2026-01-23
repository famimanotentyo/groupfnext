from django.db import models
from django.conf import settings

# ==========================================
# マスタテーブル定義
# ==========================================

# 4. マニュアル状態マスタ (Manual.status)
class ManualStatusMaster(models.Model):
    """
    マニュアルの承認状態定義
    例: pending(承認待ち), approved(公開中)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="状態コード")
    name = models.CharField(max_length=50, verbose_name="状態名")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "マニュアル状態マスタ"
        verbose_name_plural = "マニュアル状態マスタ"

# 5. マニュアル公開範囲マスタ (Manual.visibility)
class ManualVisibilityMaster(models.Model):
    """
    マニュアルの公開範囲定義
    例: public(全社員), manager_only(管理職のみ)
    """
    code = models.CharField(max_length=30, unique=True, verbose_name="範囲コード")
    name = models.CharField(max_length=100, verbose_name="範囲名")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "マニュアル公開範囲マスタ"
        verbose_name_plural = "マニュアル公開範囲マスタ"

# ==========================================
# メインモデル定義
# ==========================================

class Manual(models.Model):
    """
    業務マニュアル（承認フロー & 閲覧制限付き）
    """
    title = models.CharField(max_length=100, verbose_name="マニュアル名")
    description = models.TextField(blank=True, verbose_name="説明・備考")
    file = models.FileField(upload_to='manuals/', verbose_name="ファイル")
    
    # ★修正: CHOICESをForeignKeyに変更
    status = models.ForeignKey(ManualStatusMaster, on_delete=models.PROTECT, null=True, verbose_name="状態")
    visibility = models.ForeignKey(ManualVisibilityMaster, on_delete=models.PROTECT, null=True, verbose_name="公開範囲")
    is_deleted = models.BooleanField(default=False, verbose_name="論理削除")
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_manuals', verbose_name="作成者")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_manuals', verbose_name="承認者")
    # Department is now in accounts app. Use string reference 'accounts.Department'
    department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="関連部署")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="承認日時")
    bookmarks = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmarked_manuals', blank=True, verbose_name="ブックマーク")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "マニュアル"
        verbose_name_plural = "マニュアル"
        ordering = ['-created_at']


class ViewingHistory(models.Model):
    """
    マニュアルの閲覧履歴（「最近使ったもの」用）
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="閲覧ユーザー")
    manual = models.ForeignKey(Manual, on_delete=models.CASCADE, verbose_name="閲覧マニュアル")
    viewed_at = models.DateTimeField(auto_now=True, verbose_name="最終閲覧日時")

    class Meta:
        verbose_name = "閲覧履歴"
        verbose_name_plural = "閲覧履歴"
        # 1人のユーザーが1つのマニュアルに対して1つの履歴レコードだけ持つようにする
        unique_together = ('user', 'manual')
        # 閲覧が新しい順に並べる
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user} -> {self.manual} ({self.viewed_at})"
