from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Interview, InterviewStatusMaster, InterviewFeedback, MemberAnalysis
from accounts.models import User
from django.db.models import Q

import json
import datetime
from django.utils import timezone

from openai import OpenAI
import os

@login_required
def interview_home(request):
    """
    面談アドバイストップ画面
    - 検索機能
    - 進行中・今後の面談
    - 面談履歴
    - 要アクション件数（準備中で期限切れ＆FB未入力）
    - 今月の実施率
    """
    from django.db.models import Count
    from accounts.models import RoleMaster
    
    # 検索機能
    search_query = request.GET.get('q', '').strip()
    search_results = []
    
    # ログインユーザーの部署を取得
    user_department = request.user.department

    if search_query:
        # ユーザーを検索（名前、カナ、部署で）
        base_query = User.objects.filter(
            Q(last_name__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name_kana__icontains=search_query) |
            Q(first_name_kana__icontains=search_query) |
            Q(department__name__icontains=search_query),
            is_active=True
        )
        
        # 部署フィルタを追加
        if user_department:
            base_query = base_query.filter(department=user_department)
            
        search_results = base_query.select_related('department', 'role').distinct()
    
    now = timezone.now()
    
    # --- 要アクション件数の計算 ---
    # 「準備中」(confirmed) ステータスで、予定日時が過ぎており、フィードバックがない面談
    action_interviews = Interview.objects.filter(
        manager=request.user,
        status__code='confirmed',  # 準備中
        scheduled_at__lt=now       # 予定日時が過去
    ).exclude(
        feedback__isnull=False     # フィードバックがない
    )
    if user_department:
        action_interviews = action_interviews.filter(employee__department=user_department)
    action_count = action_interviews.count()
    action_interviews_list = action_interviews.select_related('employee')[:5]  # 表示用に最大5件
    
    # --- 今月の実施率の計算 ---
    # 今月の開始日と終了日
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 部署内のemployee権限のユーザー一覧
    try:
        employee_role = RoleMaster.objects.get(code='employee')
        if user_department:
            all_employees = User.objects.filter(
                department=user_department,
                role=employee_role,
                is_active=True
            ).exclude(id=request.user.id)
        else:
            all_employees = User.objects.filter(
                role=employee_role,
                is_active=True
            ).exclude(id=request.user.id)
    except RoleMaster.DoesNotExist:
        all_employees = User.objects.none()
    
    total_employees = all_employees.count()
    
    # 今月面談を1回以上実施した人（completed or フィードバック済み）
    completed_this_month = Interview.objects.filter(
        manager=request.user,
        scheduled_at__gte=first_day_of_month,
        scheduled_at__lt=now
    ).filter(
        Q(status__code='completed') | Q(feedback__isnull=False)
    )
    if user_department:
        completed_this_month = completed_this_month.filter(employee__department=user_department)
    
    # 実施済みの部下IDリスト（重複なし）
    completed_employee_ids = completed_this_month.values_list('employee_id', flat=True).distinct()
    completed_count = len(set(completed_employee_ids))  # x
    
    remaining_count = total_employees - completed_count  # z
    if remaining_count < 0:
        remaining_count = 0
    
    # 実施率 m = x / (x + z) * 100
    if total_employees > 0:
        completion_rate = int((completed_count / total_employees) * 100)
    else:
        completion_rate = 0
    
    # 進行中・今後の面談（自分が担当する面談）
    # 実施済み（completed）は表示しない
    # ★追加: 却下（declined）も表示しない
    upcoming_query = Interview.objects.filter(
        manager=request.user,
        scheduled_at__gte=now
    ).exclude(
        status__code__in=['completed', 'declined']  # 実施済み・却下を除外
    )
    if user_department:
         upcoming_query = upcoming_query.filter(employee__department=user_department)

    upcoming_interviews = upcoming_query.select_related('employee', 'status').order_by('scheduled_at')[:5]
    
    # 最近の面談履歴（自分が担当した面談、過去のもの）
    # ★追加: 却下（declined）も表示しない（あるいは履歴としては残す？要望は「表示しない」なので除外）
    recent_query = Interview.objects.filter(
        manager=request.user,
        scheduled_at__lt=now
    ).exclude(
        status__code='declined'
    )
    if user_department:
        recent_query = recent_query.filter(employee__department=user_department)

    recent_interviews = recent_query.select_related('employee', 'status').prefetch_related('feedback').order_by('-scheduled_at')[:10]
    
    return render(request, 'interviews/index.html', {
        'search_query': search_query,
        'search_results': search_results,
        'upcoming_interviews': upcoming_interviews,
        'recent_interviews': recent_interviews,
        # 新規追加
        'action_count': action_count,
        'action_interviews': action_interviews_list,
        'completion_rate': completion_rate,
        'completed_count': completed_count,
        'remaining_count': remaining_count,
    })

    # 部下リスト（自分以外）
    employees = User.objects.exclude(id=request.user.id).filter(is_active=True)
    return render(request, 'interviews/create.html', {'employees': employees})

@login_required
def interview_create(request):
    """
    面談作成＆AIシナリオ生成画面
    """
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        theme = request.POST.get('theme')
        location = request.POST.get('location')  # 場所を取得
        scheduled_at = request.POST.get('scheduled_at')
        
        # 日時必須チェック
        if not scheduled_at:
            messages.error(request, '日時（予定）は必須です。')
            # フォームに入力値を保持して戻したいが、簡易的にリダイレクトまたは再描画
            # ここでは再描画が望ましいが、view構造上 redirect して再入力させるか、renderで戻すか。
            # 今回は renderで戻すが、employeesリストが必要。
            from accounts.models import RoleMaster
            try:
                employee_role = RoleMaster.objects.get(code='employee')
                employees = User.objects.exclude(id=request.user.id).filter(
                    is_active=True,
                    role=employee_role
                )
            except RoleMaster.DoesNotExist:
                employees = User.objects.none()
            return render(request, 'interviews/create.html', {
                'employees': employees,
                'error_theme': theme, # 入力保持用（簡易）
                'error_location': location,
            })

        employee = get_object_or_404(User, pk=employee_id)
        
        # 部下の分析データがあれば取得
        analysis_text = "（まだ分析データはありません）"
        if hasattr(employee, 'member_analysis'):
            analysis_text = employee.member_analysis.analysis_text

        # Geminiへのプロンプト作成
        prompt = f"""
        あなたは優秀なマネジメントコーチです。
        以下の上司と部下の面談に向けた「トークスクリプト（台本）」と「アドバイス」を作成してください。

        【上司】{request.user.last_name} {request.user.first_name}
        【部下】{employee.last_name} {employee.first_name} ({employee.department.name if employee.department else '部署なし'}, {employee.role.name if employee.role else ''})
        【面談テーマ】{theme}
        【部下の特性（過去の分析）】
        {analysis_text}

        【出力フォーマット】
        # 1. アプローチ戦略
        （簡潔に）
        # 2. トークスクリプト
        上司: 「〜」
        部下: （想定）「〜」
        上司: 「〜」
        # 3. 注意点（NGワードなど）
        部下の世代や特性を考慮した注意点を挙げてください。
        例: 【世代別NGワード】もし部下がコロナ世代（Z世代など）の場合、「修学旅行の思い出は？」など、コロナ禍で失われた経験に関する話題は避ける、など。
        """

        script = "AI生成に失敗しました。"
        try:
            if settings.OPENAI_API_KEY:
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "あなたは優秀なマネジメントコーチです。"},
                        {"role": "user", "content": prompt}
                    ]
                )
                script = response.choices[0].message.content
            else:
                script = "APIキーが設定されていないため、デモ用のテキストを表示します。\n（APIキーを設定するとここにAI生成テキストが表示されます）"
        except Exception as e:
            script = f"エラーが発生しました: {str(e)}"

        # 面談レコード保存
        try:
            status_tentative, _ = InterviewStatusMaster.objects.get_or_create(code='tentative', defaults={'name': '仮予約'})
            
            interview = Interview.objects.create(
                manager=request.user,
                employee=employee,
                scheduled_at=scheduled_at, # 必須なのでそのまま使用
                theme=theme,
                location=location, # 場所を保存
                status=status_tentative,
                script_generated=script
            )
            
            # --- 部下へ通知を作成 ---
            from notifications.models import Notification, NotificationTypeMaster
            
            # 通知タイプを取得（なければ作成）
            notif_type, _ = NotificationTypeMaster.objects.get_or_create(code='interview_invite', defaults={'name': '面談依頼'})
            
            Notification.objects.create(
                recipient=employee,
                title=f"面談の依頼が届いています（{theme}）",
                message=f"{request.user.last_name}マネージャーから面談の依頼があります。\n日時: {scheduled_at}\n場所: {location}",
                notification_type=notif_type,
                related_object_id=interview.pk,
                link_url=f"/interviews/confirm/{interview.pk}/" # 確定画面へのリンク
            )
            # ---------------------

            messages.success(request, '面談プランを作成し、対象者に通知を送りました！')
            return redirect('interview_detail', pk=interview.pk)
        except Exception as e:
            messages.error(request, f'保存に失敗しました: {e}')
    
    # 部下リスト（employee権限のみ）
    from accounts.models import RoleMaster
    try:
        employee_role = RoleMaster.objects.get(code='employee')
        employees = User.objects.exclude(id=request.user.id).filter(
            is_active=True,
            role=employee_role
        )
    except RoleMaster.DoesNotExist:
        employees = User.objects.none()
    return render(request, 'interviews/create.html', {'employees': employees})

@login_required
def interview_confirm(request, pk):
    """
    部下用：面談詳細・承諾画面
    """
    interview = get_object_or_404(Interview, pk=pk)
    
    # 本人確認（部下本人であることを確認）
    if interview.employee != request.user:
        messages.error(request, '他人の面談情報にはアクセスできません。')
        return redirect('index') # トップページなどへリダイレクト
        
    if request.method == 'POST':
        # 承諾処理
        status_confirmed, _ = InterviewStatusMaster.objects.get_or_create(code='confirmed', defaults={'name': '確定'})
        interview.status = status_confirmed
        interview.save()
        
        messages.success(request, '面談を承諾しました。')
        return redirect('notifications_index') # 通知一覧などへ戻る

    return render(request, 'interviews/confirm.html', {'interview': interview})


@login_required
def interview_decline(request, pk):
    """
    面談辞退処理
    """
    interview = get_object_or_404(Interview, pk=pk)
    
    # 本人確認
    if interview.employee != request.user:
        messages.error(request, '他人の面談情報にはアクセスできません。')
        return redirect('index')
    
    if request.method == 'POST':
        reason = request.POST.get('decline_reason', '')
        
        try:
            # ステータスを「却下・辞退」に変更
            declined_status = InterviewStatusMaster.objects.get(code='declined')
            interview.status = declined_status
            interview.save()
            
            # マネージャー（上司）へ通知
            from notifications.models import Notification, NotificationTypeMaster
            notif_type, _ = NotificationTypeMaster.objects.get_or_create(code='interview_decline', defaults={'name': '面談辞退'})
            
            Notification.objects.create(
                recipient=interview.manager,
                title=f"面談が辞退されました（{interview.employee.last_name} {interview.employee.first_name}）",
                message=f"以下の面談が辞退されました。\nテーマ: {interview.theme}\n日時: {interview.scheduled_at}\n理由: {reason}",
                notification_type=notif_type,
                related_object_id=interview.pk,
                link_url=None # 却下されたので飛ぶ先は特にない、あるいは履歴へ
            )
            
            messages.warning(request, '面談を辞退しました。')
            return redirect('notifications_index')
            
        except InterviewStatusMaster.DoesNotExist:
             messages.error(request, 'ステータスマスタ(declined)が見つかりません。')
             
    return redirect('interview_confirm', pk=pk)

@login_required
def interview_detail(request, pk):
    """
    面談詳細・スクリプト閲覧画面
    """
    interview = get_object_or_404(Interview, pk=pk)
    return render(request, 'interviews/detail.html', {'interview': interview})

@login_required
def interview_feedback(request, pk):
    """
    面談後のフィードバック入力画面
    """
    interview = get_object_or_404(Interview, pk=pk)
    
    if request.method == 'POST':
        evaluation = request.POST.get('evaluation')
        # タグはカンマ区切り、またはCheckboxのリストで来る想定
        tags_list = request.POST.getlist('tags') 
        memo = request.POST.get('memo')
        
        # フィードバック保存
        # 既存があれば更新、なければ作成
        fb, created = InterviewFeedback.objects.update_or_create(
            interview=interview,
            defaults={
                'evaluation': evaluation,
                'tags': tags_list,
                'memo': memo
            }
        )
        
        # ★追加: 面談ステータスを「実施済み」に更新
        status_completed, _ = InterviewStatusMaster.objects.get_or_create(
            code='completed', 
            defaults={'name': '実施済み'}
        )
        interview.status = status_completed
        interview.save()
        
        # --- AIによる部下分析の更新 ---
        employee = interview.employee
        
        # 現在の分析データ
        current_analysis = ""
        if hasattr(employee, 'member_analysis'):
            current_analysis = employee.member_analysis.analysis_text
            
        # プロンプト作成
        prompt = f"""
        あなたは優秀なマネジメントコーチです。
        以下の面談結果のフィードバックに基づき、この部下の「取扱説明書（特性分析データ）」を更新・追記してください。
        
        【部下】{employee.last_name} {employee.first_name}
        【今回の面談テーマ】{interview.theme}
        【結果評価】{evaluation} (3:成功, 2:普通, 1:失敗)
        【観察タグ】{', '.join(tags_list)}
        【上司メモ】{memo}

        【これまでの分析データ】
        {current_analysis}

        【指示】
        上記の「これまでの分析データ」をベースに、今回の結果を踏まえて内容を洗練させてください。
        特に「効果的な褒め方」「注意すべき接し方」「思考パターン」について具体的に記述してください。
        Markdown形式で出力してください。
        """
        
        new_analysis = current_analysis
        ai_log = ""
        new_analysis = current_analysis
        ai_log = ""
        try:
            if settings.OPENAI_API_KEY:
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "あなたは優秀なマネジメントコーチです。"},
                        {"role": "user", "content": prompt}
                    ]
                )
                new_analysis = response.choices[0].message.content
                ai_log = "AI Analysis Success"
            else:
                ai_log = "No API Key"
        except Exception as e:
            ai_log = str(e)
            
        # 分析データの保存
        MemberAnalysis.objects.update_or_create(
            target_user=employee,
            defaults={'analysis_text': new_analysis}
        )
        
        # ログ保存
        fb.ai_analysis_log = ai_log
        fb.save()
        
        messages.success(request, 'フィードバックを保存し、部下データを更新しました。')
        return redirect('member_analysis', pk=employee.pk)

    return render(request, 'interviews/feedback.html', {'interview': interview})

@login_required
def member_analysis(request, pk):
    """
    部下の分析結果（トリセツ）閲覧画面
    """
    target_user = get_object_or_404(User, pk=pk)
    analysis = None
    if hasattr(target_user, 'member_analysis'):
        analysis = target_user.member_analysis
    
    return render(request, 'interviews/analysis_view.html', {
        'target_user': target_user, 
        'analysis': analysis
    })

@login_required
def interview_history_select(request):
    """
    過去の面談一覧：メンバー選択画面
    interview_create と同じロジックで employee 権限のユーザーを表示
    """
    from accounts.models import RoleMaster
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        if employee_id:
            return redirect('member_analysis', pk=employee_id)
    
    # 部下リスト（employee権限のみ）
    try:
        employee_role = RoleMaster.objects.get(code='employee')
        employees = User.objects.exclude(id=request.user.id).filter(
            is_active=True,
            role=employee_role
        )
    except RoleMaster.DoesNotExist:
        employees = User.objects.none()
    
    return render(request, 'interviews/history_select.html', {'employees': employees})

@login_required
def follow_up_report(request):
    """
    要フォローアップレポート
    最近面談していないメンバーを表示
    """
    from accounts.models import RoleMaster
    from django.db.models import Max
    
    user_department = request.user.department
    now = timezone.now()
    
    # 部署内のemployee権限のユーザー一覧
    try:
        employee_role = RoleMaster.objects.get(code='employee')
        if user_department:
            all_employees = User.objects.filter(
                department=user_department,
                role=employee_role,
                is_active=True
            ).exclude(id=request.user.id)
        else:
            all_employees = User.objects.filter(
                role=employee_role,
                is_active=True
            ).exclude(id=request.user.id)
    except RoleMaster.DoesNotExist:
        all_employees = User.objects.none()
    
    # 各メンバーの最終面談日を取得
    members_data = []
    for employee in all_employees:
        # このマネージャーとこの部下の面談履歴
        last_interview = Interview.objects.filter(
            manager=request.user,
            employee=employee
        ).order_by('-scheduled_at').first()
        
        if last_interview:
            last_date = last_interview.scheduled_at
            days_since = (now - last_date).days
        else:
            last_date = None
            days_since = 999  # 面談履歴なし
        
        members_data.append({
            'employee': employee,
            'last_interview': last_interview,
            'last_date': last_date,
            'days_since': days_since,
        })
    
    # 最終面談日が古い順にソート（面談履歴なしが最優先）
    members_data.sort(key=lambda x: -x['days_since'])
    
    return render(request, 'interviews/follow_up_report.html', {
        'members_data': members_data,
    })

