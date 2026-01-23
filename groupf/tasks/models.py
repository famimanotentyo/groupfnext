from django.db import models
from django.conf import settings

# ==========================================
# マスタテーブル定義
# ==========================================

# 2. タスク状態マスタ (Task.status)
class TaskStatusMaster(models.Model):
    """
    タスクの進行状態定義
    例: unstarted(未着手), completed(完了)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="状態コード")
    name = models.CharField(max_length=50, verbose_name="状態名")
    order = models.IntegerField(default=0, verbose_name="表示順") # 並び順制御用

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "タスク状態マスタ"
        verbose_name_plural = "タスク状態マスタ"
        ordering = ['order']

# 9. 新しいマスタテーブル: タスク種別
class TaskTypeMaster(models.Model):
    """
    タスクの種類定義
    例: self(自作), request(依頼)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="種別コード")
    name = models.CharField(max_length=50, verbose_name="種別名")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "タスク種別マスタ"
        verbose_name_plural = "タスク種別マスタ"

# ==========================================
# メインモデル定義
# ==========================================

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="タグ名")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "タグ"
        verbose_name_plural = "タグ"
        ordering = ['name']


class Task(models.Model):
    title = models.CharField(max_length=200, verbose_name="タスク名")
    due_date = models.DateTimeField(verbose_name="期限")
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks', verbose_name="タグ")
    
    # ★修正: CHOICESをForeignKeyに変更
    status = models.ForeignKey(TaskStatusMaster, on_delete=models.PROTECT, null=True, verbose_name="タスク状態")
    
    assigned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='assigned_tasks', blank=True, verbose_name="取り掛かり中の人")
    completed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='completed_tasks', blank=True, verbose_name="完了とした人")
    
    task_type = models.ForeignKey(
        TaskTypeMaster, 
        on_delete=models.PROTECT, 
        null=True,  # 既存データ用にnull許可、あとでマスタ登録後にデータ移行推奨
        blank=True,
        verbose_name="タスク種別"
    )
    
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='requested_tasks', 
        verbose_name="依頼者"
    )

    notes = models.TextField(blank=True, verbose_name="タスク備考欄")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "タスク"
        verbose_name_plural = "タスク"
        ordering = ['due_date', 'status']
