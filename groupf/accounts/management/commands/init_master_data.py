from django.core.management.base import BaseCommand
from accounts.models import RoleMaster, Department
from tasks.models import TaskStatusMaster, TaskTypeMaster
from manuals.models import ManualStatusMaster, ManualVisibilityMaster
from consultations.models import ConsultationStatusMaster
from schedule.models import ScheduleEventTypeMaster
from interviews.models import InterviewStatusMaster
from notifications.models import NotificationTypeMaster

class Command(BaseCommand):
    help = 'Initializes master data (Roles, Statuses, Types, Departments) for the application.'

    def handle(self, *args, **options):
        self.stdout.write("Creating Master Data...")

        # 1. ユーザー役割マスタ
        roles = [
            {'code': 'admin', 'name': '管理者'},
            {'code': 'manager', 'name': 'マネージャー'},
            {'code': 'employee', 'name': '一般社員'},
        ]
        for r in roles:
            RoleMaster.objects.get_or_create(code=r['code'], defaults={'name': r['name']})

        # 2. タスク状態マスタ
        task_statuses = [
            {'code': 'unstarted', 'name': '未着手', 'order': 1},
            {'code': 'in_progress', 'name': '着手中', 'order': 2},
            {'code': 'pending_review', 'name': '確認待ち', 'order': 3},
            {'code': 'completed', 'name': '完了', 'order': 4},
        ]
        for s in task_statuses:
            TaskStatusMaster.objects.get_or_create(code=s['code'], defaults={'name': s['name'], 'order': s['order']})

        # 3. タスク種別マスタ
        task_types = [
            {'code': 'self', 'name': '自作(Myタスク)'},
            {'code': 'request', 'name': '依頼(タスクボード)'},
        ]
        for t in task_types:
            TaskTypeMaster.objects.get_or_create(code=t['code'], defaults={'name': t['name']})
            
        # 4. マニュアル状態マスタ
        manual_statuses = [
            {'code': 'pending', 'name': '承認待ち'},
            {'code': 'approved', 'name': '公開中'},
            {'code': 'rejected', 'name': '却下'},
        ]
        for s in manual_statuses:
            ManualStatusMaster.objects.get_or_create(code=s['code'], defaults={'name': s['name']})
            
        # 5. マニュアル公開範囲マスタ
        manual_visibilities = [
            {'code': 'public', 'name': '全社員'},
            {'code': 'manager_only', 'name': '管理職のみ'},
        ]
        for v in manual_visibilities:
            ManualVisibilityMaster.objects.get_or_create(code=v['code'], defaults={'name': v['name']})
            
        # 6. 相談状態マスタ
        consultation_statuses = [
            {'code': 'open', 'name': '受付中'},
            {'code': 'resolved', 'name': '解決済み'},
        ]
        for s in consultation_statuses:
            ConsultationStatusMaster.objects.get_or_create(code=s['code'], defaults={'name': s['name']})
            
        # 7. スケジュール種別マスタ
        schedule_types = [
            {'code': 'meeting', 'name': '会議'},
            {'code': 'vacation', 'name': '休暇'},
            {'code': 'other', 'name': 'その他'},
        ]
        for s in schedule_types:
            ScheduleEventTypeMaster.objects.get_or_create(code=s['code'], defaults={'name': s['name']})
            
        # 8. 面談状態マスタ
        interview_statuses = [
            {'code': 'tentative', 'name': '仮予約'},
            {'code': 'confirmed', 'name': '確定'},
            {'code': 'completed', 'name': '実施済み'},
            {'code': 'declined', 'name': '却下・辞退'},
        ]
        for s in interview_statuses:
            InterviewStatusMaster.objects.get_or_create(code=s['code'], defaults={'name': s['name']})

        # 9. 通知タイプマスタ
        notification_types = [
            {'code': 'info', 'name': 'お知らせ'},
            {'code': 'task_assign', 'name': 'タスクアサイン'},
            {'code': 'interview_invite', 'name': '面談依頼'},
            {'code': 'manual_approval', 'name': 'マニュアル承認依頼'},
            {'code': 'manual_reject', 'name': 'マニュアル却下'},
            {'code': 'interview_decline', 'name': '面談辞退'},
            {'code': 'consultation_message', 'name': '相談メッセージ'},
        ]
        for t in notification_types:
            NotificationTypeMaster.objects.get_or_create(code=t['code'], defaults={'name': t['name']})
            
        # 10. 部署
        departments = [
            {'name': '開発部', 'description': 'システム開発を行う部署'},
            {'name': '営業部', 'description': '顧客対応を行う部署'},
        ]
        for d in departments:
            Department.objects.get_or_create(name=d['name'], defaults={'description': d['description']})

        self.stdout.write(self.style.SUCCESS("All Master Data Created Successfully."))
