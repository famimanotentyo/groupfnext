from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Interview, InterviewStatusMaster, InterviewFeedback, MemberAnalysis
from accounts.models import User
from django.db.models import Q
import google.generativeai as genai
import json
import datetime
from django.utils import timezone

# Gemini設定
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

@login_required
def interview_home(request):
    """
    面談アドバイストップ画面
    - 検索機能
    - 進行中・今後の面談
    - 面談履歴
    """
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
    
    # 進行中・今後の面談（自分が担当する面談）
    # ★修正: 部署フィルタを追加 (部下の部署が自分の部署と同じであること)
    # 基本的には manager=request.user で絞っているが、念の為部署も確認するか、
    # あるいは「自分が担当」していれば部署またぎもあり得るか？
    # ユーザー要望は「表示するものを、ログインしている上司の部署の人間のみにしてください」なので
    # ここでは厳密に department 一致を追加する。
    
    now = timezone.now()
    upcoming_query = Interview.objects.filter(
        manager=request.user,
        scheduled_at__gte=now
    )
    if user_department:
         upcoming_query = upcoming_query.filter(employee__department=user_department)

    upcoming_interviews = upcoming_query.select_related('employee', 'status').order_by('scheduled_at')[:5]
    
    # 最近の面談履歴（自分が担当した面談、過去のもの）
    recent_query = Interview.objects.filter(
        manager=request.user,
        scheduled_at__lt=now
    )
    if user_department:
        recent_query = recent_query.filter(employee__department=user_department)

    recent_interviews = recent_query.select_related('employee', 'status').prefetch_related('feedback').order_by('-scheduled_at')[:10]
    
    return render(request, 'interviews/index.html', {
        'search_query': search_query,
        'search_results': search_results,
        'upcoming_interviews': upcoming_interviews,
        'recent_interviews': recent_interviews,
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
        """

        script = "AI生成に失敗しました。"
        try:
            if settings.GEMINI_API_KEY:
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                script = response.text
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
                scheduled_at=scheduled_at if scheduled_at else datetime.datetime.now(),
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
    
    # 部下リスト（自分以外）
    employees = User.objects.exclude(id=request.user.id).filter(is_active=True)
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
        try:
            if settings.GEMINI_API_KEY:
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                new_analysis = response.text
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
