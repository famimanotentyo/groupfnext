from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
import random
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.utils import timezone
from .models import User
from .models import User
from .forms import ProfileEditForm, LoginForm, AccountAdminEditForm, PasswordResetRequestForm
from tasks.models import Task
from notifications.models import Notification, NotificationTypeMaster



class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if not user.is_initial_setup_completed:
            return reverse_lazy('profile_edit_page')
        return reverse_lazy('top_page') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ここに「気の利いたワード」のリストを作ります
        quotes = [
            "今日の積み重ねが、未来の自分を楽にします。",
            "完璧を目指すより、まずは終わらせよう。",
            "休息も立派な仕事の一部です。",
            "Ctrl + S はこまめにね。",
            "困ったときは、周りを頼ってもいいんです。",
            "焦らず、一歩ずつ進みましょう。",
            "今日のあなたは、昨日より賢くなっている。",
            "タスクの完了は、心の完了。",
            "「忙しい」を「充実している」と言い換えてみる。",
            "とりあえず、コーヒーでも飲みませんか？",
        ]
        
        # ランダムに1つ選んでテンプレートに渡す
        context['daily_quote'] = random.choice(quotes)
        return context 

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_set.html'
    # success_url は form_valid でリダイレクトするため不要になる場合もありますが、念のため残すか、form_validでreturnで返す
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        # パスワード変更処理を実行
        response = super().form_valid(form)
        # ユーザーをログインさせる
        user = form.user
        login(self.request, user)
        # プロフィール編集画面へリダイレクト
        return redirect('profile_edit_page')

def initial_login_page(request):
    """
    初回ログイン画面
    """
    if request.method == 'POST':
        # ここで初回パスワード変更処理などを行う
        pass
    return render(request, 'newemployee/initial_login.html')

@login_required
def profile_registration_page(request):
    """
    プロフィール登録画面
    """
    user = request.user
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('top_page')
    else:
        form = ProfileEditForm(instance=user)
    
    context = {
        'page_title': 'プロフィール登録',
        'form': form
    }
    return render(request, 'newemployee/profile_registration.html', context)

@login_required
def process_registration(request):
    """
    プロフィール登録処理（フォームの送信先）
    """
    # profile_registration_page で処理しているので不要かもしれないが、
    # URLが分かれている場合はこちらにロジックを移動する
    return redirect('profile_registration_page')

def account_create_page(request):
    if request.method == 'POST':
        return redirect('account_create_success_page')
    return render(request, 'accounts/account_create.html')

def account_create_success_page(request):
    return render(request, 'accounts/account_create_success.html')

@login_required
def account_management_page(request):
    context = { 'page_title': 'アカウント管理' }
    return render(request, 'accounts/account_management.html', context)

from django.db.models import Q
from django.utils.timesince import timesince
from django.http import JsonResponse

@login_required
def account_list_page(request):
    category = request.GET.get("category", "name")
    q = (request.GET.get("q") or "").strip()

    users = (
        User.objects.filter(is_active=True)
        .select_related("department", "role")
        .prefetch_related("completed_tasks__tags")
        .order_by("last_name", "first_name")
    )

    # --- 検索（qがある時だけ絞り込む） ---
    if q:
        if category == "name":
            users = users.filter(
                Q(last_name__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name_kana__icontains=q) |
                Q(first_name_kana__icontains=q)
            )
        elif category == "email":
            users = users.filter(email__icontains=q)
        elif category == "department":
            users = users.filter(department__name__icontains=q)
        elif category == "permission":
            users = users.filter(role__name__icontains=q)
        else:
            # 不正なcategoryが来たら名前検索にフォールバック
            users = users.filter(
                Q(last_name__icontains=q) | Q(first_name__icontains=q)
            )

    users_data = []
    for u in users:
        tag_names = list(u.get_completed_tags().values_list("name", flat=True))[:10]  # 最大10個表示
        users_data.append({
            "id": u.id,
            "name": f"{u.last_name} {u.first_name}",
            "email": u.email,
            "department": u.department.name if u.department else "未所属",
            "role": u.role.name if u.role else "-",
            "employee_number": u.employee_number,
            "birth_date": u.birth_date.strftime("%Y年 %m月 %d日") if u.birth_date else "-",
            "hire_date": u.hire_date.strftime("%Y年 %m月 %d日") if u.hire_date else "-",
            "last_active": timesince(u.last_login, timezone.now()) + " ago" if u.last_login else "-",
            "tags": tag_names,
            "tags_script_id": f"tags-{u.id}",
        })

    return render(request, "accounts/account_list.html", {
        "page_title": "メンバー",
        "users_data": users_data,
        "category": category,
        "q": q
    })

@login_required
def api_account_detail(request, user_id):
    u = get_object_or_404(
        User.objects.select_related('department', 'role')
            .prefetch_related('completed_tasks__tags'),
        pk=user_id,
        is_active=True
    )

    def fmt_date(d):
        return d.strftime('%Y年 %m月 %d日') if d else '-'

    # ★タグ（完了タスクのタグ）を作る：prefetch を活かしてDB負荷も抑える
    tag_set = set()
    for t in u.completed_tasks.all():
        for tag in t.tags.all():
            tag_set.add(tag.name)
    tag_names = sorted(tag_set)[:10]

    data = {
        "id": u.id,
        "name": f"{u.last_name} {u.first_name}",
        "department": u.department.name if u.department else "未所属",
        "role": u.role.name if u.role else "-",
        "email": u.email,
        "employee_number": u.employee_number,
        "birth_date": fmt_date(u.birth_date),
        "hire_date": fmt_date(u.hire_date),
        "tags": tag_names,  # ★追加
    }
    return JsonResponse(data)

@login_required
def account_detail_page(request):
    return render(request, 'accounts/account_detail.html')

def account_logout_view_page(request):
    logout(request)
    return redirect('logout_success')

def account_logout_success_page(request):
    return render(request, 'accounts/account_logout_success.html')

@login_required
def profile_edit_page(request):
    """
    プロフィール編集画面 (既存社員用)
    """
    user = request.user
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user_obj = form.save(commit=False)
            user_obj.is_initial_setup_completed = True
            user_obj.save()
            messages.success(request, 'プロフィールを保存しました。')
            return redirect('top_page')
    else:
        form = ProfileEditForm(instance=user)

    context = {
        'page_title': 'プロフィール設定',
        'form': form,
    }
    return render(request, 'accounts/profile_edit.html', context)

def password_reset_request_view(request):
    """
    パスワードリセット申請画面
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            employee_number = form.cleaned_data['employee_number']
            manager = form.cleaned_data['manager']
            
            # 申請者ユーザーを取得
            try:
                requesting_user = User.objects.get(employee_number=employee_number)
                
                # 通知タイプ 'info' を取得 (なければ作成またはエラーハンドリング)
                # populate_data.py で作成済み前提だが、念のためget
                try:
                    info_type = NotificationTypeMaster.objects.get(code='info')
                except NotificationTypeMaster.DoesNotExist:
                     # フォールバック: タイプなしor適当なもの
                     # 本番ではエラー以前にマスタ必須
                     info_type = None

                # マネージャーへの通知を作成
                # リンク先は、その対象ユーザーの編集画面とする (管理者/マネージャー向け画面)
                # URL: accounts/edit/<int:pk>/
                link_url = reverse_lazy('account_edit_page', kwargs={'pk': requesting_user.pk})

                Notification.objects.create(
                    recipient=manager,
                    title="パスワードリセット申請",
                    message=f"{requesting_user.last_name} {requesting_user.first_name} さん ({requesting_user.employee_number}) からパスワードリセットの依頼がありました。\n詳細画面からリセットURLを発行してください。",
                    notification_type=info_type,
                    link_url=link_url,
                    related_object_id=requesting_user.pk
                )
                
                messages.success(request, f"{manager.last_name} {manager.first_name} さんへリセット申請を送信しました。")
                return redirect('login')
                
            except User.DoesNotExist:
                # フォームのcleanでチェック済みだが念のため
                messages.error(request, "指定されたユーザーが見つかりません。")
    else:
        form = PasswordResetRequestForm()

    return render(request, 'accounts/password_reset_request.html', {'form': form})

@login_required
def user_profile_detail(request, pk):
    return render(request, 'accounts/user_profile.html')

@login_required
def member_list_view(request):
    return render(request, 'accounts/member_list.html')

from django.core.exceptions import PermissionDenied

@login_required
def manager_member_detail(request, pk):
    target_member = get_object_or_404(User, pk=pk)
    
    # 権限チェック: マネージャーは自部署のメンバーのみ閲覧可
    if request.user.role.code == 'manager':
        if not request.user.department or target_member.department != request.user.department:
            raise PermissionDenied("他部署のメンバー情報は閲覧できません。")

    tasks = target_member.assigned_tasks.all().select_related('status', 'requested_by', 'task_type').order_by('due_date')
    
    context = {
        'page_title': f'{target_member.last_name} {target_member.first_name} さんの詳細',
        'target_member': target_member,
        'tasks': tasks,
    }
    return render(request, 'management/member_detail.html', context)

@login_required
def account_edit_page(request, pk):
    """
    管理者・マネージャー用アカウント編集画面
    - Admin: 全ユーザー編集可能
    - Manager: Employeeのみ編集可能、Admin/Managerは閲覧のみ（基本編集も制限するかは要件次第だが、安全のためEmployee以外はreadonly扱いにする）
    """
    target_user = get_object_or_404(User, pk=pk)
    
    # 権限判定ロジック
    is_admin = (request.user.role.code == 'admin')
    is_manager = (request.user.role.code == 'manager')
    target_is_employee = (target_user.role.code == 'employee')

    can_edit = False
    if is_admin:
        can_edit = True
    elif is_manager and target_is_employee:
        can_edit = True
    
    # ※マネージャーが自分自身を編集する場合の考慮が必要なら追加（今回は管理画面としての体裁なので他者編集を前提）
    
    if request.method == 'POST':
        if not can_edit:
             messages.error(request, 'このユーザーを編集する権限がありません。')
             return redirect('account_edit_page', pk=pk)

        form = AccountAdminEditForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'{target_user.last_name} {target_user.first_name} さんの情報を更新しました。')
            return redirect('account_list_page')
    else:
        form = AccountAdminEditForm(instance=target_user)

    context = {
        'page_title': 'アカウント編集',
        'form': form,
        'target_user': target_user,
        'can_edit': can_edit, # テンプレート制御用
    }
    return render(request, 'accounts/account_edit.html', context)

@login_required
def trigger_password_reset(request, pk):
    """
    管理者によるパスワードリセットトリガー
    """
    # 権限チェック（管理者 or マネージャー）
    if not request.user.role or request.user.role.code not in ['admin', 'manager']:
        messages.error(request, '権限がありません。')
        return redirect('account_list_page')

    if request.method != 'POST':
        messages.error(request, '無効なリクエストです。')
        return redirect('account_edit_page', pk=pk)

    target_user = get_object_or_404(User, pk=pk)
    
    # ★追加: マネージャーはEmployee以外リセット不可
    if request.user.role.code == 'manager':
        if target_user.role.code != 'employee':
             messages.error(request, 'マネージャーは一般社員以外のパスワードリセットを行えません。')
             return redirect('account_edit_page', pk=pk)

    try:
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.urls import reverse

        # トークン生成
        token = default_token_generator.make_token(target_user)
        uid = urlsafe_base64_encode(force_bytes(target_user.pk))
        
        # リセットURL構築
        # 'password_reset_confirm' というnameのURLパターンが存在することを前提としています
        reset_path = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        full_url = request.build_absolute_uri(reset_path)

        # ログ出力（メール送信シミュレーション）
        print("="*60)
        print(f"[Password Reset Trigger]")
        print(f"User: {target_user.last_name} {target_user.first_name} ({target_user.email})")
        print(f"Reset URL: {full_url}")
        print("="*60)

        messages.success(request, f'{target_user.last_name} さんのパスワードリセットURLを発行しました（ターミナルを確認してください）。')

    except Exception as e:
        messages.error(request, f'エラーが発生しました: {e}')

    return redirect('account_edit_page', pk=pk)
