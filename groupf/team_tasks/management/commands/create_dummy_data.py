import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from team_tasks.models import Task, Tag, TaskStatusMaster, RoleMaster

User = get_user_model()

class Command(BaseCommand):
    help = 'ダッシュボード確認用のダミーデータを生成します'

    def handle(self, *args, **kwargs):
        self.stdout.write("ダミーデータの生成を開始します...")

        # --- 1. マスタデータの準備 ---
        try:
            status_unstarted, _ = TaskStatusMaster.objects.get_or_create(code='unstarted', defaults={'name': '未着手'})
            status_progress, _ = TaskStatusMaster.objects.get_or_create(code='in_progress', defaults={'name': '着手中'})
            active_statuses = [status_unstarted, status_progress]
        except Exception:
            self.stdout.write(self.style.ERROR("エラー: TaskStatusMaster(unstarted/in_progress)が必要です。"))
            return

        role_employee, _ = RoleMaster.objects.get_or_create(code='employee', defaults={'name': '一般社員'})

        # --- 2. タグの準備 ---
        tag_names = ['#難易度高', '#難易度中', '#難易度低', '#Python', '#Design', '#要件定義', '#バグ修正', '#資料作成']
        tags = []
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(name=name)
            tags.append(t)

        # --- 3. ダミーユーザー作成 (5名) ---
        dummy_users = []
        last_names = ['佐藤', '鈴木', '高橋', '田中', '渡辺']
        first_names = ['一郎', '花子', '健太', '美咲', '大輔']
        
        for i in range(5):
            # ★修正: username ではなく employee_number を使う
            emp_num = f'dummy_{i+1:03}' 
            
            # ★修正: employee_number で検索・作成
            user, created = User.objects.get_or_create(employee_number=emp_num, defaults={
                'email': f'{emp_num}@example.com',
                'last_name': last_names[i],
                'first_name': first_names[i],
                'role': role_employee,
                'is_active': True
            })
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f"ユーザー作成: {user.last_name} {user.first_name} ({emp_num})")
            dummy_users.append(user)

        # 依頼者役（管理者）
        admin_user = User.objects.filter(role__code='admin').first() or dummy_users[0]

        # --- 4. タスク生成 ---
        # Task.objects.all().delete() # 必要ならコメントアウト解除
        
        for user in dummy_users:
            task_count = random.randint(15, 25)
            
            for j in range(task_count):
                # 期限決定（色分け用）
                category = random.choice(['red', 'yellow', 'green'])
                today = timezone.now()
                
                if category == 'red':
                    due_date = today + timedelta(days=random.randint(0, 2))
                elif category == 'yellow':
                    due_date = today + timedelta(days=random.randint(3, 7))
                else:
                    due_date = today + timedelta(days=random.randint(8, 30))

                # 依頼タイプ決定
                is_request = random.random() < 0.3
                requested_by = admin_user if is_request else user

                task = Task.objects.create(
                    title=f"ダミー案件_{category}_{j+1}",
                    
                    # ★修正: description ではなく notes に変更
                    notes="自動生成されたタスクです。",  
                    
                    due_date=due_date,
                    status=random.choice(active_statuses),
                    requested_by=requested_by
                )
                
                task.assigned_users.add(user)

                # タグ付け
                difficulty_tag = random.choice(tags[:3])
                other_tags = random.sample(tags[3:], k=random.randint(0, 2))
                
                task.tags.add(difficulty_tag)
                for t in other_tags:
                    task.tags.add(t)

        self.stdout.write(self.style.SUCCESS(f"完了！合計 {len(dummy_users)} 名分のリッチなデータを生成しました。"))