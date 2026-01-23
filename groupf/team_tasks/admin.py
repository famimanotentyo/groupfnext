from django.contrib import admin
from accounts.models import User, Department, RoleMaster
from tasks.models import Task, Tag, TaskStatusMaster, TaskTypeMaster
from manuals.models import Manual, ManualStatusMaster, ManualVisibilityMaster
from consultations.models import Consultation, ConsultationStatusMaster
from interviews.models import Interview, InterviewStatusMaster
from schedule.models import ScheduleEvent, ScheduleEventTypeMaster
from notifications.models import Notification, NotificationTypeMaster


# --- マスタテーブルの登録 ---
@admin.register(RoleMaster)
class RoleMasterAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

@admin.register(TaskStatusMaster)
class TaskStatusMasterAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order')
    ordering = ('order',)

# ... 他のマスタも同様に登録 ...
admin.site.register(ConsultationStatusMaster)
admin.site.register(ManualStatusMaster)
admin.site.register(ManualVisibilityMaster)
admin.site.register(ScheduleEventTypeMaster)
admin.site.register(InterviewStatusMaster)
admin.site.register(NotificationTypeMaster)

# --- メインモデルの登録 ---
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('employee_number', 'last_name', 'first_name', 'department', 'role')
    list_filter = ('department', 'role', 'is_active')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'due_date', 'requested_by')
    list_filter = ('status', 'tags')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    pass

@admin.register(Tag) # Tagモデルも登録
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'created_by',
        'status',
        'visibility',
        'is_deleted',
        'created_at',
    )
    list_filter = ('status', 'visibility', 'is_deleted')
    search_fields = ('title', 'created_by__last_name')