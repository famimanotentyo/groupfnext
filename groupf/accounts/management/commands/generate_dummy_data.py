from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
import random
from accounts.models import RoleMaster, Department
from tasks.models import Task, TaskStatusMaster, TaskTypeMaster, Tag
from interviews.models import Interview, InterviewStatusMaster, InterviewFeedback

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates dummy data for demonstration purposes'

    def handle(self, *args, **options):
        self.stdout.write("Starting Dummy Data Generation...")

        # 1. 部署データの補完
        extra_departments = [
            {'name': '人事部', 'description': '採用・労務管理'},
            {'name': '経理部', 'description': '財務・会計処理'},
            {'name': 'マーケティング部', 'description': '広告・広報活動'},
        ]
        
        all_departments = list(Department.objects.all())
        for d in extra_departments:
            dept, created = Department.objects.get_or_create(name=d['name'], defaults={'description': d['description']})
            if created:
                self.stdout.write(f"Created Department: {d['name']}")
                all_departments.append(dept)

        dev_dept = Department.objects.filter(name='開発部').first() or all_departments[0]
        
        # 2. ユーザーデータの生成
        last_names = ['佐藤', '鈴木', '高橋', '田中', '伊藤', '渡辺', '山本', '中村', '小林', '加藤', '吉田', '山田', '佐々木', '山口', '松本', '井上', '木村', '林', '斎藤', '清水', '山崎', '森', '阿部', '池田', '橋本', '山下', '石川', '中島', '前田', '藤田']
        first_names = ['太郎', '次郎', '三郎', '花子', '健太', '美咲', '大輔', '陽菜', '翔太', '美優', '誠', '直美', '隆', '由美', '健一', 'さくら', '大樹', '優衣', '達也', '愛', '剛', '麻衣', '涼介', '七海', '和也', '里奈', '拓真', '結衣', '駿', '杏奈']
        
        # 役割
        try:
            manager_role = RoleMaster.objects.get(code='manager')
            employee_role = RoleMaster.objects.get(code='employee')
        except RoleMaster.DoesNotExist:
            self.stdout.write(self.style.ERROR("RoleMaster data missing. Run init_master_data first."))
            return

        users = []
        # 既存ユーザーも含める
        users.extend(list(User.objects.filter(is_active=True).exclude(employee_number__regex=r'\D'))) # 除外: 数字以外の社員番号（adminなど）
        
        # マネージャー候補（既存含む）
        managers = list(User.objects.filter(role=manager_role, is_active=True))

        for i in range(30):
            emp_num = f'10{i:02d}'
            if User.objects.filter(employee_number=emp_num).exists():
                u = User.objects.get(employee_number=emp_num)
                if u not in users: users.append(u)
                if u.role == manager_role and u not in managers: managers.append(u)
                continue

            last_name = random.choice(last_names)
            first_name = random.choice(first_names)
            dept = random.choice(all_departments)
            
            # 5人に1人はマネージャー
            role = manager_role if i % 6 == 0 else employee_role
            
            hire_year = random.randint(2015, 2024)
            hire_date = date(hire_year, random.randint(1, 12), 1)

            user = User.objects.create_user(
                employee_number=emp_num,
                email=f'user{emp_num}@example.com',
                password='password123',
                last_name=last_name,
                first_name=first_name,
                last_name_kana='ダミー',
                first_name_kana='ユーザー',
                department=dept,
                role=role,
                hire_date=hire_date,
                is_initial_setup_completed=True
            )
            users.append(user)
            if role == manager_role:
                managers.append(user)
            
            self.stdout.write(f"Created User: {last_name} {first_name} ({role.name})")

        # 3. タスクデータの生成
        verbs = ['作成', 'レビュー', '更新', '調査', '修正', '打ち合わせ', '設計', 'テスト', '分析', '報告']
        nouns = ['議事録', '仕様書', 'コード', 'バグ', '顧客データ', '売上レポート', 'デザイン', 'API', 'データベース', '企画書', 'マニュアル', 'スケジュール']
        
        difficulty_tags = ['#難易度高', '#難易度中', '#難易度低']
        skill_tags = ['#Python', '#JavaScript', '#Excel', '#PowerPoint', '#SQL', '#AWS', '#Design', '#Management', '#Communication', '#Writing']

        try:
            status_unstarted = TaskStatusMaster.objects.get(code='unstarted')
            status_in_progress = TaskStatusMaster.objects.get(code='in_progress')
            status_completed = TaskStatusMaster.objects.get(code='completed')
            status_pending = TaskStatusMaster.objects.get(code='pending_review')
            
            type_self = TaskTypeMaster.objects.get(code='self')
            type_request = TaskTypeMaster.objects.get(code='request')
        except:
             self.stdout.write(self.style.ERROR("TaskMaster data missing."))
             return

        statuses = [status_unstarted, status_in_progress, status_completed, status_pending]

        self.stdout.write("Generating Tasks...")
        for _ in range(120): # 120タスク生成
            title = f"{random.choice(nouns)}の{random.choice(verbs)}"
            owner = random.choice(users)
            
            days_delta = random.randint(-20, 30)
            due_date = timezone.now() + timedelta(days=days_delta)
            
            status = random.choices(statuses, weights=[10, 30, 50, 10])[0] # 完了多め
            task_type = random.choices([type_self, type_request], weights=[70, 30])[0]
            
            requester = owner
            if task_type == type_request:
                requester = random.choice(managers) if managers else owner
            
            task = Task.objects.create(
                title=title,
                notes="ダミーデータとして自動生成されたタスクです。",
                due_date=due_date,
                status=status,
                task_type=task_type,
                requested_by=requester,
                created_at=timezone.now() - timedelta(days=random.randint(0, 60))
            )

            # 過去のタスクで完了している場合はupdated_atも調整（ダッシュボード用）
            if status == status_completed:
                 task.updated_at = task.due_date if task.due_date < timezone.now() else timezone.now()
                 task.completed_users.add(owner)
                 task.save()
            
            task.assigned_users.add(owner)
            
            # タグ付け
            tags_to_add = []
            tags_to_add.append(random.choice(difficulty_tags))
            tags_to_add.extend(random.sample(skill_tags, k=random.randint(1, 3)))
            
            for t_name in set(tags_to_add): # setで重複排除
                tag, _ = Tag.objects.get_or_create(name=t_name.lstrip('#'))
                task.tags.add(tag)

        # 4. 面談データの生成
        self.stdout.write("Generating Interviews...")
        try:
            int_confirmed = InterviewStatusMaster.objects.get(code='confirmed')
            int_completed = InterviewStatusMaster.objects.get(code='completed')
        except:
             self.stdout.write(self.style.ERROR("InterviewMaster data missing."))
             return

        for employee in users:
            if employee in managers: continue # マネージャー自身の評価面談は今回はスキップ
            
            manager = random.choice(managers)
            
            # 過去の面談
            for i in range(random.randint(1, 3)):
                date_past = timezone.now() - timedelta(days=random.randint(1, 60))
                interview = Interview.objects.create(
                     manager=manager,
                     employee=employee,
                     scheduled_at=date_past,
                     status=int_completed,
                     location='https://meet.google.com/xyz-abc-def',
                     notes='定期1on1'
                )
                
                # フィードバック
                InterviewFeedback.objects.create(
                    interview=interview,
                    memo="最近の業務パフォーマンスは安定しています。引き続き頑張ってください。",
                    evaluation=random.randint(2, 3)
                )

            # 未来の面談（一部の人のみ）
            if random.random() < 0.3:
                date_future = timezone.now() + timedelta(days=random.randint(1, 14))
                Interview.objects.create(
                     manager=manager,
                     employee=employee,
                     scheduled_at=date_future,
                     status=int_confirmed,
                     location='https://meet.google.com/future-meet-url',
                     notes='次回の目標設定'
                )

        self.stdout.write(self.style.SUCCESS('Successfully generated dummy data!'))
