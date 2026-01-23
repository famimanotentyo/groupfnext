import os
import django
import sys
from datetime import date

# Django環境のセットアップ
sys.path.append(r'c:\Django課題制作 - コピー\groupf')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from accounts.models import RoleMaster, User, Department
from tasks.models import TaskStatusMaster, TaskTypeMaster, Tag
from manuals.models import ManualStatusMaster, ManualVisibilityMaster
from consultations.models import ConsultationStatusMaster
from schedule.models import ScheduleEventTypeMaster
from interviews.models import InterviewStatusMaster
from notifications.models import NotificationTypeMaster

def create_master_data():
    print("Creating Master Data...")

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
    ]
    for s in interview_statuses:
        InterviewStatusMaster.objects.get_or_create(code=s['code'], defaults={'name': s['name']})

    # 9. 通知タイプマスタ
    notification_types = [
        {'code': 'info', 'name': 'お知らせ'},
        {'code': 'task_assign', 'name': 'タスクアサイン'},
        {'code': 'interview_invite', 'name': '面談依頼'},
        {'code': 'manual_approval', 'name': 'マニュアル承認依頼'},
    ]
    for t in notification_types:
        NotificationTypeMaster.objects.get_or_create(code=t['code'], defaults={'name': t['name']})
        
    # 10. 部署 (テスト用)
    departments = [
        {'name': '開発部', 'description': 'システム開発を行う部署'},
        {'name': '営業部', 'description': '顧客対応を行う部署'},
    ]
    for d in departments:
        Department.objects.get_or_create(name=d['name'], defaults={'description': d['description']})

    print("Master Data Created.")

def create_users():
    print("Creating Users...")
    
    # 部署を取得
    dev_dept = Department.objects.get(name='開発部')
    sales_dept = Department.objects.get(name='営業部')
    
    # 役割を取得
    admin_role = RoleMaster.objects.get(code='admin')
    manager_role = RoleMaster.objects.get(code='manager')
    employee_role = RoleMaster.objects.get(code='employee')
    
    # 1. Admin User
    if not User.objects.filter(employee_number='001').exists():
        User.objects.create_superuser(
            employee_number='001',
            email='admin@example.com',
            password='password123',
            last_name='管理者',
            first_name='太郎',
            last_name_kana='カンリシャ',
            first_name_kana='タロウ',
            department=dev_dept,
            role=admin_role,
            hire_date=date(2020, 4, 1),
            is_initial_setup_completed=True
        )
        print("Created Admin User: 001 / password123")
    else:
        print("Admin User exists.")

    # 2. Manager User
    if not User.objects.filter(employee_number='002').exists():
        User.objects.create_user(
            employee_number='002',
            email='manager@example.com',
            password='password123',
            last_name='上司',
            first_name='次郎',
            last_name_kana='ジョウシ',
            first_name_kana='ジロウ',
            department=dev_dept,
            role=manager_role,
            hire_date=date(2021, 4, 1),
            is_initial_setup_completed=True
        )
        print("Created Manager User: 002 / password123")
    else:
        print("Manager User exists.")

    # 3. Employee User
    if not User.objects.filter(employee_number='003').exists():
        User.objects.create_user(
            employee_number='003',
            email='employee@example.com',
            password='password123',
            last_name='社員',
            first_name='三郎',
            last_name_kana='シャイン',
            first_name_kana='サブロウ',
            department=sales_dept,
            role=employee_role,
            hire_date=date(2022, 4, 1),
            is_initial_setup_completed=True
        )
        print("Created Employee User: 003 / password123")
    else:
        print("Employee User exists.")
        
    print("Users Created.")

if __name__ == '__main__':
    create_master_data()
    create_users()
