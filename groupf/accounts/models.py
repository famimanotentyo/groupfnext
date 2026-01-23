from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

# ==========================================
# マスタテーブル定義 (CHOICESの代替)
# ==========================================

# 1. ユーザー役割マスタ (User.role)
class RoleMaster(models.Model):
    """
    ユーザーの役割（権限）定義
    例: admin(管理者), manager(マネージャー), employee(一般社員)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="役割コード") # システム的な識別子
    name = models.CharField(max_length=50, verbose_name="役割名") # 表示名

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "役割マスタ"
        verbose_name_plural = "役割マスタ"


# ==========================================
# メインモデル定義
# ==========================================

class CustomUserManager(BaseUserManager):
    def create_user(self, employee_number, email, password=None, **extra_fields):
        if not employee_number:
            raise ValueError('社員番号は必須です')
        email = self.normalize_email(email)
        user = self.model(employee_number=employee_number, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_number, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # ★修正: デフォルトの役割（admin）をマスタから取得する必要があるが、
        # 初期化前はマスタが存在しないため、運用でカバーするか初期データ投入が必要。
        # ここでは一旦、運用で「admin」というcodeのマスタデータが必須とする前提で進める。
        try:
            admin_role = RoleMaster.objects.get(code='admin')
            extra_fields.setdefault('role', admin_role)
        except RoleMaster.DoesNotExist:
             raise ValueError("RoleMasterに'admin'が存在しません。初期データを投入してください。")

        return self.create_user(employee_number, email, password, **extra_fields)


class Department(models.Model):
    name = models.CharField(max_length=50, verbose_name="グループ名(部署名)")
    description = models.TextField(blank=True, verbose_name="説明")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "グループ"
        verbose_name_plural = "グループ"


class User(AbstractBaseUser, PermissionsMixin):
    """
    社員番号でログインするカスタムユーザーモデル
    """
    employee_number = models.CharField(max_length=20, unique=True, verbose_name="社員番号", help_text="例: 000-000-000")
    last_name = models.CharField(max_length=50, verbose_name="姓")
    first_name = models.CharField(max_length=50, verbose_name="名")
    last_name_kana = models.CharField(max_length=50, verbose_name="セイ")
    first_name_kana = models.CharField(max_length=50, verbose_name="メイ")
    email = models.EmailField(unique=True, verbose_name="メールアドレス")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="電話番号")
    
    # upload_to='avatars/' は media/avatars/ フォルダに保存されます
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="アイコン画像")
    
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="所属グループ")
    
    # ★修正: CHOICESをForeignKeyに変更
    # マスタデータ削除時の挙動は PROTECT (使われている間は削除不可) を推奨
    role = models.ForeignKey(RoleMaster, on_delete=models.PROTECT, null=True, verbose_name="権限")
    
    birth_date = models.DateField(null=True, blank=True, verbose_name="生年月日")
    hire_date = models.DateField(null=True, blank=True, verbose_name="入社日")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="登録日")

    is_initial_setup_completed = models.BooleanField(default=False, verbose_name="初回設定完了")
    temp_password_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="仮パスワード有効期限")
    
    is_active = models.BooleanField(default=True, verbose_name="有効")
    is_staff = models.BooleanField(default=False, verbose_name="管理サイトアクセス権限")

    objects = CustomUserManager()

    USERNAME_FIELD = 'employee_number'
    REQUIRED_FIELDS = ['email', 'last_name', 'first_name']

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.employee_number})"

    def get_completed_tags(self):
        # NOTE: Circular dependency to 'tasks' app. 
        # Since Tag and Task are moving to 'tasks' app, we import them inside the method or use string reference query.
        # But 'Tag' is a model. Using 'tasks.Tag' in filter might work if we import Tag. 
        # For now, I will comment this out or use a local import to avoid circular dependency at module level.
        from tasks.models import Tag
        return Tag.objects.filter(tasks__completed_users=self).distinct()
    
    def is_temp_password_active(self):
        if self.is_initial_setup_completed:
            return True
        if self.temp_password_expires_at:
            return timezone.now() < self.temp_password_expires_at
        return True
