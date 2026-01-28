from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
import json
from datetime import datetime, timedelta
import google.generativeai as genai
from django.conf import settings

from .models import Task, Tag, TaskStatusMaster, TaskTypeMaster
from accounts.models import User
from notifications.models import Notification, NotificationTypeMaster
from manuals.models import Manual
from consultations.models import Question
from .forms import TaskRegisterForm, CSVUploadForm

def top_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # --- 統一検索ロジック (省略なしで維持) ---
    search_query = request.GET.get('q')
    search_results = None
    
    if search_query:
        # マニュアル検索
        manual_hits = Manual.objects.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query),
            is_deleted=False
        ).select_related('status', 'visibility')
        
        # ナレッジ検索
        question_hits = Question.objects.filter(
            Q(title__icontains=search_query) | 
            Q(problem_summary__icontains=search_query) | 
            Q(solution_summary__icontains=search_query)
        )
        
        search_results = {
            'manuals': manual_hits,
            'questions': question_hits,
            'count': manual_hits.count() + question_hits.count()
        }
    # -----------------------

    # ユーザーの権限コードを取得
    role_code = request.user.role.code if request.user.role else None

    # ★ 変更: 全ロールでダッシュボードを表示する方向へ修正
    # ただし、employee は自部署固定、managerは自部署デフォルトだが変更可、
    # adminは全部署可（managerと同じでOK）

    from accounts.models import Department
    
    # 部署リスト（admin/managerは選択用に取得）
    all_departments = []
    if role_code in ['admin', 'manager']:
        all_departments = Department.objects.all()

    selected_department_id = request.GET.get('department')
    selected_department = None
    
    # --- 部署選択ロジック ---
    if role_code == 'employee':
        # employeeは自部署固定
        if request.user.department:
            selected_department = request.user.department
            selected_department_id = str(selected_department.id)
        else:
            # 部署なしemployeeの場合... 全体表示にするか、あるいは何も表示しないか
            # ここでは「部署なし」として扱う（members絞り込みで対応）
            pass

    elif role_code == 'manager':
        # managerはデフォルト自部署（選択あればそちら優先）
        if not selected_department_id and request.user.department:
             selected_department = request.user.department
             selected_department_id = str(selected_department.id)
    
    # --- メンバー取得ロジック ---
    if selected_department_id:
        try:
             # IDから部署オブジェクト取得（employeeの場合すでに取得済みだが念のため）
            if not selected_department or str(selected_department.id) != str(selected_department_id):
                selected_department = Department.objects.get(id=selected_department_id)
            
            # 自部署のメンバー（自分以外）
            members = User.objects.filter(is_active=True, department=selected_department).exclude(id=request.user.id)
        except Department.DoesNotExist:
            members = User.objects.filter(is_active=True).exclude(id=request.user.id)
    else:
        # 部署未選択（全部署表示） - employeeで部署なしの場合もここに来る
        members = User.objects.filter(is_active=True).exclude(id=request.user.id)

    # --- ダッシュボードデータ構築 (全員共通) ---
    dashboard_data = []
    
    # ★ 全体チャート用の集計変数
    overall_stats = {
        'own': {'0-3日': 0, '4-7日': 0, '8日以上': 0},
        'request': {'0-3日': 0, '4-7日': 0, '8日以上': 0}
    }

    # 期限判定用ヘルパー関数 (JSとロジックを合わせる)
    def get_deadline_category(deadline_date):
        if not deadline_date:
            return '8日以上'
        # deadline_date is DateTimeField, convert to date
        diff = (deadline_date.date() - timezone.now().date()).days
        if diff <= 3: return '0-3日'
        elif diff <= 7: return '4-7日'
        else: return '8日以上'

    for member in members:
        # スキル: 完了済みタスクのタグ上位3つを取得
        skills = [tag.name for tag in member.get_completed_tags()][:3]
        
        grade = member.role.name if member.role else "-"

        active_tasks = member.assigned_tasks.exclude(status__code='completed')
        
        own_tasks = []     
        request_tasks = [] 
        difficulty_counts = {'high': 0, 'mid': 0, 'low': 0}

        for task in active_tasks:
            # 期限集計用
            cat = get_deadline_category(task.due_date)
            
            deadline_str = task.due_date.strftime('%Y-%m-%d') if task.due_date else ''
            
            if task.requested_by and task.requested_by != member:
                request_tasks.append({'deadline': deadline_str})
                overall_stats['request'][cat] += 1 # 全体集計加算
            else:
                own_tasks.append({'deadline': deadline_str})
                overall_stats['own'][cat] += 1 # 全体集計加算

            task_tags = [t.name for t in task.tags.all()]
            is_high = any('難易度高' in t or '高' in t for t in task_tags if '難易度' in t)
            is_mid = any('難易度中' in t or '中' in t for t in task_tags if '難易度' in t)
            is_low = any('難易度低' in t or '低' in t for t in task_tags if '難易度' in t)

            if is_high: difficulty_counts['high'] += 1
            elif is_mid: difficulty_counts['mid'] += 1
            elif is_low: difficulty_counts['low'] += 1
            else:
                difficulty_counts['mid'] += 1 

        dashboard_data.append({
            'id': member.id,
            'name': f"{member.last_name} {member.first_name}",
            'department_id': member.department.id if member.department else None, # 部署IDを追加
            'grade': grade,
            'skills': skills,
            'tasks': {
                'own': own_tasks,
                'request': request_tasks,
                'difficulty': difficulty_counts
            }
        })

    context = {
        'page_title': 'チームダッシュボード' if role_code in ['manager', 'admin', 'employee'] else 'ホーム',
        'members_json': json.dumps(dashboard_data, ensure_ascii=False),
        'overall_stats_json': json.dumps(overall_stats, ensure_ascii=False), # 追加
        'all_departments': all_departments, # employeeの場合は空リストになるので選択肢でない
        'selected_department': selected_department,
        'user_department_id': request.user.department.id if request.user.department else None, # JS制御用
    }
    return render(request, 'index.html', context)
    
def task_assign(request):
    context = {}
    return render(request, 'tasks/task_assign.html', context)

def task_board(request):
    context = {}
    return render(request, 'tasks/task_board.html', context)

@login_required
def task_approve(request, task_id):
    if not request.user.role or request.user.role.code not in ['admin', 'manager']:
        messages.error(request, '承認権限がありません。')
        return redirect('task_board_page')

    task = get_object_or_404(Task, id=task_id)
    
    try:
        is_self_approval = (task.requested_by == request.user)
        is_assigned_to_self = (request.user in task.assigned_users.all())

        if is_self_approval and is_assigned_to_self:
            try:
                self_type = TaskTypeMaster.objects.get(code='self')
                task.task_type = self_type
            except TaskTypeMaster.DoesNotExist:
                pass

        completed_status = TaskStatusMaster.objects.get(code='completed')
        task.status = completed_status
        task.updated_at = timezone.now()
        task.save()
        
        messages.success(request, f'タスク「{task.title}」を承認し、完了としました。')
        
    except TaskStatusMaster.DoesNotExist:
        messages.error(request, 'システムエラー: ステータスマスタ(completed)が見つかりません。')

    return redirect('task_board_page')

def task_register(request):
    context = {}
    return render(request, 'tasks/task_register.html', context)

def management_support_page(request):
    context = {
        'page_title': 'マネジメント支援'
    }
    return render(request, 'tasks/management_support.html', context)

@login_required
def task_assign_page(request):
    context = {
        'page_title': 'タスク割り当て',
    }
    return render(request, 'tasks/task_assign.html', context)

@login_required
def api_search_tasks(request):
    keyword = request.GET.get('keyword', '')
    target_statuses = ['unstarted', 'in_progress']
    tasks = Task.objects.filter(status__code__in=target_statuses).select_related('status').prefetch_related('tags')

    if keyword:
        tasks = tasks.filter(title__icontains=keyword)

    data = []
    for task in tasks:
        data.append({
            'id': task.id,
            'title': task.title,
            'status': task.status.name,
            'due_date': task.due_date.strftime('%Y-%m-%dT%H:%M') if task.due_date else '',
            'tags': [tag.name for tag in task.tags.all()],
            'notes': task.notes,
        })
    
    return JsonResponse({'tasks': data})

@login_required
def api_recommend_users(request):
    task_id = request.GET.get('task_id')
    user_name_keyword = request.GET.get('user_name', '')
    users = User.objects.filter(is_active=True).prefetch_related('assigned_tasks')

    if user_name_keyword:
        users = users.filter(
            Q(last_name__icontains=user_name_keyword) | 
            Q(first_name__icontains=user_name_keyword)
        )

    user_data = []
    target_task_tags = []
    if task_id:
        try:
            task = Task.objects.get(id=task_id)
            target_task_tags = list(task.tags.all())
        except Task.DoesNotExist:
            pass

    for user in users:
        current_load = user.assigned_tasks.filter(status__code='in_progress').count()
        match_count = 0
        if target_task_tags:
            user_skill_tags = user.get_completed_tags()
            for tag in target_task_tags:
                if tag in user_skill_tags:
                    match_count += 1
        
        user_data.append({
            'id': user.id,
            'name': f"{user.last_name} {user.first_name}",
            'avatar_url': user.avatar.url if user.avatar else None, 
            'current_load': current_load,
            'match_count': match_count,
            'department': user.department.name if user.department else "未所属",
        })

    user_data.sort(key=lambda x: (-x['match_count'], x['current_load']))
    return JsonResponse({'users': user_data})

@require_POST
@login_required
def api_execute_assignment(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        user_id = data.get('user_id')
        new_due_date = data.get('due_date')
        notes = data.get('notes')

        task = Task.objects.get(id=task_id)
        user = User.objects.get(id=user_id)

        task.assigned_users.add(user)
        
        if new_due_date:
            task.due_date = new_due_date
            
        if notes:
            if task.notes:
                task.notes += f"\n\n【割当指示】{notes}"
            else:
                task.notes = notes

        if task.status.code == 'unstarted':
            try:
                in_progress = TaskStatusMaster.objects.get(code='in_progress')
                task.status = in_progress
            except:
                pass

        task.save()

        try:
            type_assign = NotificationTypeMaster.objects.get(code='task_assign')
            Notification.objects.create(
                recipient=user,
                title="新しいタスクが割り当てられました",
                message=f"タスク「{task.title}」の担当に指名されました。",
                notification_type=type_assign,
                related_object_id=task.id,
                link_url='/task-board/' 
            )
        except Exception as e:
            print(f"通知作成エラー: {e}")

        return JsonResponse({'status': 'success', 'message': f'{user.last_name}さんに割り当てました'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def task_board_page(request):
    user = request.user
    one_week_ago = timezone.now() - timedelta(days=7)
    
    tasks = Task.objects.select_related('requested_by', 'status', 'task_type').prefetch_related('assigned_users')
    
    tasks = tasks.filter(
        Q(status__code__in=['unstarted', 'in_progress', 'pending_review']) | 
        Q(status__code='completed', updated_at__gte=one_week_ago)
    )

    if user.department:
        tasks = tasks.filter(requested_by__department=user.department)

    # パターンA: Board shows only requests
    tasks = tasks.filter(task_type__code='request')

    context = {
        'page_title': 'タスクボード',
        'tasks_unstarted': tasks.filter(status__code='unstarted'),
        'tasks_in_progress': tasks.filter(status__code='in_progress'),
        'tasks_pending': tasks.filter(status__code='pending_review'),
        'tasks_completed': tasks.filter(status__code='completed'),
    }
    
    return render(request, 'tasks/task_board.html', context)

# Gemini configuration
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Updated model name as per user code
TAG_GENERATION_PROMPT_TEMPLATE = """
以下のタスク名から、ハッシュタグ形式で20個以内の関連タグを生成してください。
タグには必ず #難易度 (高、中、低) のいずれか一つを含めてください。

例: 議事録の製作
出力: #議事録 #文章作成 #ドキュメント作成 #ビジネス文書 #情報整理 #効率化 #会議 #記録 #難易度中

タスク名: {task_title}
出力:
"""

def generate_tags_with_gemini(task_title):
    try:
        prompt = TAG_GENERATION_PROMPT_TEMPLATE.format(task_title=task_title)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # print(f"Gemini API Error: {e}") 
        return ""

@login_required
def task_register_page(request):
    page_title = 'タスク登録'

    if request.method == 'POST':
        form = TaskRegisterForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.requested_by = request.user
            
            try:
                generated_tags_str = generate_tags_with_gemini(task.title)
                tag_names = [name.strip().lstrip('#') for name in generated_tags_str.split() if name.strip().startswith('#')]
            except Exception:
                tag_names = []

            post_task_type = request.POST.get('task_type', 'self')
            is_manager = (request.user.role and request.user.role.code in ['admin', 'manager'])
            target_type_code = 'self' 

            if is_manager and post_task_type == 'board':
                target_type_code = 'request'
            else:
                target_type_code = 'self'

            try:
                type_obj = TaskTypeMaster.objects.get(code=target_type_code)
                task.task_type = type_obj
            except TaskTypeMaster.DoesNotExist:
                pass

            # ★ステータス設定: 自作タスクは「着手中」、ボードタスクは「未着手」
            try:
                if target_type_code == 'self':
                    in_progress_status = TaskStatusMaster.objects.get(code='in_progress')
                    task.status = in_progress_status
                else:
                    unstarted_status = TaskStatusMaster.objects.get(code='unstarted')
                    task.status = unstarted_status
            except TaskStatusMaster.DoesNotExist:
                messages.error(request, 'システムエラー: タスク状態マスタが見つかりません。')
                return redirect('task_register_page')

            task.save()

            for tag_name in tag_names:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                task.tags.add(tag)

            if target_type_code == 'self':
                task.assigned_users.add(request.user)
                messages.success(request, f'タスク「{task.title}」をマイタスク(自作)に登録しました。')
            else:
                messages.success(request, f'タスク「{task.title}」をタスクボード(依頼)に公開しました。')

            return redirect('task_register_page')
        else:
            messages.error(request, '入力内容にエラーがあります。')
    else:
        form = TaskRegisterForm()

    context = {
        'page_title': page_title,
        'form': form,
    }
    return render(request, 'tasks/task_register.html', context)

@login_required
def assign_task_to_self(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.assigned_users.add(request.user)
    
    if task.status and task.status.code == 'unstarted':
        try:
            in_progress_status = TaskStatusMaster.objects.get(code='in_progress')
            task.status = in_progress_status
        except TaskStatusMaster.DoesNotExist:
            pass
    
    task.save()
    messages.success(request, f'タスク「{task.title}」に着手しました！')
    return redirect('task_board_page')

@login_required
def complete_task_by_user(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    if request.user not in task.assigned_users.all():
        messages.error(request, "あなたはタスクの担当者ではありません。")
        return redirect('my_tasks_page')

    task.completed_users.add(request.user)
    
    assigned_count = task.assigned_users.count()
    completed_count = task.completed_users.count()

    if completed_count >= assigned_count:
        try:
            is_request_task = False
            if task.task_type and task.task_type.code == 'request':
                is_request_task = True
            
            if is_request_task:
                pending_status = TaskStatusMaster.objects.get(code='pending_review')
                task.status = pending_status
                messages.success(request, f'タスク「{task.title}」の全作業が終了しました。ステータスを「確認待ち」に変更します。')
            
            elif task.requested_by == request.user:
                completed_status = TaskStatusMaster.objects.get(code='completed')
                task.status = completed_status
                task.updated_at = timezone.now()
                messages.success(request, f'タスク「{task.title}」を完了しました！')
            
            else:
                pending_status = TaskStatusMaster.objects.get(code='pending_review')
                task.status = pending_status
                messages.success(request, f'タスク「{task.title}」を確認待ちにしました。')

        except TaskStatusMaster.DoesNotExist:
            messages.error(request, 'システムエラー：ステータスマスタが見つかりません。')
            
    else:
        messages.info(request, f'あなたの作業を完了しました（他 {assigned_count - completed_count} 名の完了待ちです）。')

    task.save()
    return redirect(request.META.get('HTTP_REFERER', 'my_tasks_page'))

@login_required
def dashboard_view(request):
    user = request.user
    selected_month_str = request.GET.get('month')
    if selected_month_str:
        selected_date = datetime.strptime(selected_month_str, '%Y-%m')
        year = selected_date.year
        month = selected_date.month
    else:
        now = datetime.now()
        year = now.year
        month = now.month

    tasks = Task.objects.filter(
        status__code='completed',
        updated_at__year=year, # Using updated_at as completed_at roughly
        updated_at__month=month
    )

    if user.role.code in ['admin', 'manager']:
        tasks = tasks.filter(requested_by__department=user.department) # Assuming requested_by dept for filtering

    elif user.role.code == 'employee':
        # Condition A: Requested tasks in department? Logic adjusted to fit model
        # Just creating a placeholder logic based on original view intent
        pass 

    filter_type = request.GET.get('filter_type', 'all')
    if filter_type == 'requested':
        tasks = tasks.filter(task_type__code='request')
    elif filter_type == 'self':
        tasks = tasks.filter(task_type__code='self')

    context = {
        'tasks': tasks,
        'selected_year': year,
        'selected_month': month,
        'filter_type': filter_type,
    }
    return render(request, 'dashboard.html', context)

def task_guide_page(request):
    context = { 'page_title': 'タスクガイド' }
    return render(request, 'tasks/task_guide.html', context)

def interview_advice_menu_page(request):
    context = { 'page_title': '面談アドバイス' }
    return render(request, 'tasks/interview_advice_menu.html', context)

@login_required
def admin_csv_import_page(request):
    import csv
    from io import TextIOWrapper
    from accounts.models import User, RoleMaster
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.urls import reverse

    """
    CSVによるユーザー一括登録
    CSV形式: 社員番号, メール, 姓, 名
    """
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            try:
                # ユーザーの環境によりShift-JISかUTF-8か異なるが、ここではUTF-8CP932(Microsoft Excel標準)を考慮しつつ
                # 一般的な utf-8-sig (BOM付き対応) を試す、あるいはエラーハンドリングが必要
                # 今回は utf-8 で実装
                text_file = TextIOWrapper(csv_file.file, encoding='utf-8-sig')
                reader = csv.reader(text_file)
                
                created_count = 0
                error_count = 0
                
                # デフォルト権限（employee）の取得
                try:
                    default_role = RoleMaster.objects.get(code='employee')
                except RoleMaster.DoesNotExist:
                    default_role = None
                
                print("=== Created User Login URLs ===") 

                for i, row in enumerate(reader):
                    # ヘッダー行のスキップ判定（簡易的）
                    if i == 0 and ("社員番号" in row[0] or "employee" in row[0].lower()):
                        continue
                    
                    if len(row) < 4:
                        error_count += 1
                        continue

                    emp_num = row[0].strip()
                    email = row[1].strip()
                    lname = row[2].strip()
                    fname = row[3].strip()
                    
                    # 必須チェック
                    if not emp_num or not email:
                        error_count += 1
                        continue

                    if User.objects.filter(employee_number=emp_num).exists():
                        # 既に存在する場合はスキップ
                        error_count += 1
                        continue

                    try:
                        # パスワードは初期値として社員番号を設定
                        user = User.objects.create_user(
                            employee_number=emp_num,
                            email=email,
                            password=emp_num, 
                            last_name=lname,
                            first_name=fname,
                            role=default_role,
                            is_initial_setup_completed=False # 初回ログイン誘導のため
                        )
                        created_count += 1
                        
                        # 初回ログイン用のURL発行 (PasswordResetTokenを利用)
                        token = default_token_generator.make_token(user)
                        uid = urlsafe_base64_encode(force_bytes(user.pk))
                        reset_path = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                        full_url = request.build_absolute_uri(reset_path)
                        print(f"[{emp_num}] {lname} {fname}: {full_url}")

                    except Exception as e:
                        print(f"Line {i+1} Error: {e}")
                        error_count += 1
                
                print("================================")

                if created_count > 0:
                    messages.success(request, f"{created_count}件のアカウントを作成しました。ターミナルにログイン用URLを出力しました。")
                
                if error_count > 0:
                    messages.warning(request, f"{error_count}件のデータは登録できませんでした（重複など）。")

            except Exception as e:
                messages.error(request, f"ファイル読み込みエラー: {e}")
                
            return redirect('admin_csv_import_page')
    else:
        form = CSVUploadForm()
    return render(request, 'management/csv_import.html', {'form': form})

@login_required
def my_tasks_page(request):
    user = request.user
    # Fetch tasks assigned to current user, excluding completed
    tasks = Task.objects.filter(assigned_users=user).exclude(status__code='completed').select_related('status', 'requested_by', 'requested_by__department').prefetch_related('tags').order_by('due_date')
    
    # Structure for template - 未着手を削除
    tasks_to_display = {
        '進行中': [],
        '確認待ち・その他': []
    }
    
    import json
    for task in tasks:
        # タスクタイプ判定（self = 自作タスク）
        task_type_code = task.task_type.code if task.task_type else 'self'
        is_self_task = (task_type_code == 'self')
        
        # JSON Data for Modal
        task_data = {
            'id': task.id,
            'title': task.title,
            'task_type': task_type_code,  # 追加: タスクタイプ
            'is_self_task': is_self_task,  # 追加: 自作タスクかどうか
            'detail': {
                'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else '未設定',
                'assignee': f"{user.last_name} {user.first_name}",
                'description': task.notes or '',
                'manual': 'なし' 
            }
        }
        task.json_string = json.dumps(task_data)
        
        # Display Attributes
        task.due_date_full = task.due_date.strftime('%Y/%m/%d %H:%M') if task.due_date else '未設定'
        task.department = task.requested_by.department.name if (task.requested_by and task.requested_by.department) else '-'

        # Grouping - 未着手を削除、in_progressとそれ以外のみ
        if task.status.code == 'in_progress' or task.status.code == 'unstarted':
            tasks_to_display['進行中'].append(task)
        else:
            tasks_to_display['確認待ち・その他'].append(task)

    context = {
        'page_title': 'MYタスク',
        'tasks_to_display': tasks_to_display
    }
    return render(request, 'tasks/my_tasks.html', context)

@login_required
def completed_task_list_view(request):
    user = request.user
    
    # URLパラメータから年月の取得
    selected_month_str = request.GET.get('month')
    filter_type = request.GET.get('filter_type', 'all') 
    
    today = timezone.now().date()
    
    if selected_month_str:
        try:
            selected_date = datetime.strptime(selected_month_str, '%Y-%m')
            year = selected_date.year
            month = selected_date.month
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
        
    tasks = Task.objects.filter(
        status__code='completed',
        completed_users=user
    ).distinct()

    # 月次フィルター (updated_at で簡易判定)
    tasks = tasks.filter(updated_at__year=year, updated_at__month=month)

    # タイプフィルター
    if filter_type == 'requested':
        tasks = tasks.filter(task_type__code='request')
    elif filter_type == 'self':
        tasks = tasks.filter(task_type__code='self')
    
    tasks = tasks.order_by('-updated_at')

    # テンプレート側でループしやすいように構造化（月ごとグループ化はテンプレートでも可能だが、ここではリストのみ渡す形でもOK）
    # しかしテンプレート(completed_task_list.html)を見ると grouped_tasks を期待しているのでそれに合わせる
    
    # 今回はシンプルに、単一月表示なのでグループは1つだけ作る
    grouped_tasks = []
    if tasks.exists():
        grouped_tasks.append({
            'month': datetime(year, month, 1),
            'count': tasks.count(),
            'tasks': tasks
        })

    context = {
        'page_title': '完了タスク一覧',
        'grouped_tasks': grouped_tasks,
        'selected_year': year,
        'selected_month': month,
        'filter_type': filter_type,
    }
    return render(request, 'tasks/completed_task_list.html', context)

@login_required
def task_return_page(request, task_id):
    """
    タスクを返却する
    - 担当者が自分だけ → タスクボードに戻す（未着手に）
    - 担当者が複数 → 自分を担当から外すのみ
    """
    task = get_object_or_404(Task, id=task_id)
    
    # 自分が担当者か確認
    if request.user not in task.assigned_users.all():
        messages.error(request, 'このタスクの担当者ではありません。')
        return redirect('my_tasks_page')
    
    assigned_count = task.assigned_users.count()
    
    if assigned_count == 1:
        # 自分だけが担当者 → タスクボードに戻す
        task.assigned_users.remove(request.user)
        
        try:
            unstarted_status = TaskStatusMaster.objects.get(code='unstarted')
            task.status = unstarted_status
        except TaskStatusMaster.DoesNotExist:
            pass
        
        task.save()
        
        # ★通知: タスク投稿者に返却を通知
        if task.requested_by and task.requested_by != request.user:
            try:
                type_info = NotificationTypeMaster.objects.get(code='info')
                Notification.objects.create(
                    recipient=task.requested_by,
                    title="タスクがタスクボードに返却されました",
                    message=f"「{task.title}」が{request.user.last_name}さんからタスクボードに返却されました。",
                    notification_type=type_info,
                    related_object_id=task.id,
                    link_url='/task-board/'
                )
            except Exception as e:
                print(f"通知作成エラー: {e}")
        
        messages.success(request, f'タスク「{task.title}」をタスクボードに返却しました。')
    else:
        # 複数名が担当 → 自分だけ外れる
        task.assigned_users.remove(request.user)
        task.save()
        messages.success(request, f'タスク「{task.title}」の担当から外れました。')
    
    return redirect('my_tasks_page')

@login_required
def task_transfer_page(request, task_id):
    """
    タスク譲渡フォームを表示・処理するビュー
    """
    task = get_object_or_404(Task, id=task_id)
    users = User.objects.filter(is_active=True).exclude(id=request.user.id).select_related('department')

    if request.method == 'POST':
        new_user_id = request.POST.get('assignee_id')
        reason = request.POST.get('reason', '')

        if new_user_id:
            try:
                new_owner = User.objects.get(id=new_user_id)
                task.assigned_users.remove(request.user)
                task.assigned_users.add(new_owner)
                
                timestamp = timezone.now().strftime('%Y/%m/%d %H:%M')
                log_note = f"\n【譲渡】{request.user.last_name} → {new_owner.last_name} (理由: {reason} / {timestamp})"
                task.notes = (task.notes or "") + log_note
                task.save()
                
                # ★通知: 譲渡先のユーザーに通知
                try:
                    type_info = NotificationTypeMaster.objects.get(code='info')
                    Notification.objects.create(
                        recipient=new_owner,
                        title="タスクが譲渡されました",
                        message=f"「{task.title}」が{request.user.last_name}さんからあなたに譲渡されました。",
                        notification_type=type_info,
                        related_object_id=task.id,
                        link_url='/my-tasks/'
                    )
                except Exception as e:
                    print(f"通知作成エラー: {e}")
                
                messages.success(request, f'タスク「{task.title}」を{new_owner.last_name}さんに譲渡しました。')
                return redirect('my_tasks_page')
            except User.DoesNotExist:
                messages.error(request, '指定されたユーザーが見つかりませんでした。')

    tags_str = ", ".join([t.name for t in task.tags.all()]) if task.tags.exists() else "タグなし"

    context = {
        'page_title': 'タスクの譲渡',
        'task': task,
        'users': users,
        'tags_str': tags_str,
    }
    return render(request, 'tasks/task_transfer.html', context)

@login_required
def manager_dashboard_view(request):
    return render(request, 'tasks/manager_dashboard.html')

def surprise_page(request):
    return render(request, 'tasks/surprise.html')

@login_required
def delete_task(request, task_id):
    """
    タスクを物理削除する（自作タスク用）
    """
    task = get_object_or_404(Task, id=task_id)

    # 権限チェック: 自作タスクか、あるいは自分が作成したタスクかなどを確認
    is_authorized = False
    
    # Check if user is in assigned users (basic check for "My Task")
    if request.user in task.assigned_users.all():
        # Check if it is a self task
        try:
            if task.task_type and task.task_type.code == 'self':
                is_authorized = True
            elif task.requested_by == request.user:
                 is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        messages.error(request, 'タスクを削除する権限がありません。')
        return redirect('my_tasks_page')

    # 物理削除実行
    task_title = task.title
    task.delete()
    messages.success(request, f'タスク「{task_title}」を削除しました。')

    return redirect('my_tasks_page')
