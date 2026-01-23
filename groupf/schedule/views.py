from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Placeholder for schedule views
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import ScheduleEvent
from interviews.models import Interview
from accounts.models import User
import json
import datetime

@login_required
def index(request):
    """
    カレンダーメイン画面
    """
    users = User.objects.filter(is_active=True).order_by('department', 'employee_number')
    return render(request, 'schedule/index.html', {'users': users})

@login_required
def get_events(request):
    """
    FullCalendar用イベントデータ取得API
    """
    target_user_id = request.GET.get('user_id')
    
    if target_user_id:
        target_user = get_object_or_404(User, pk=target_user_id)
    else:
        target_user = request.user
        
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    # URLパラメータの+がスペースに変換される問題への対処
    if start_str and ' ' in start_str:
        start_str = start_str.replace(' ', '+')
    if end_str and ' ' in end_str:
        end_str = end_str.replace(' ', '+')
    
    events = []
    
    # helper: 閲覧制限ロジック
    is_me = (target_user == request.user)
    
    # 1. ScheduleEvent (その他の予定)
    schedule_events = ScheduleEvent.objects.filter(user=target_user)
    if start_str and end_str:
        schedule_events = schedule_events.filter(start_at__range=(start_str, end_str))
        
    for event in schedule_events:
        title = event.title
        description = event.description
        color = '#3788d8' # default blue
        
        # マスキング処理
        if not is_me:
            # 他人の場合
            description = "" # 詳細は隠す
            
            if event.category == 'personal':
                title = "不在"
                color = '#dc3545' # red
            elif event.category == 'work':
                title = "予定あり"
                color = '#6c757d' # grey
        else:
            # 自分の場合
            if event.category == 'personal':
                color = '#dc3545'
            elif event.category == 'work':
                color = '#3788d8'

        events.append({
            'title': title,
            'description': description,
            'start': event.start_at.isoformat(),
            'end': event.end_at.isoformat(),
            'color': color,
            'extendedProps': {
                'category': event.category
            }
        })

    # 2. Interviews (面談)
    # target_user が manager または employee になっている面談
    interviews = Interview.objects.filter(
        Q(manager=target_user) | Q(employee=target_user)
    )
    if start_str and end_str:
        interviews = interviews.filter(scheduled_at__range=(start_str, end_str))
        
    for interview in interviews:
        # 面談の当事者かどうか
        is_party = (request.user == interview.manager or request.user == interview.employee)
        
        if is_party or is_me: # 自分自身の予定として見る場合も詳細は見える（is_meは上で判定済みだが念の為）
            # 詳細表示
            title = f"面談: {interview.theme}"
            description = f"相手: {interview.employee.last_name if interview.manager == target_user else interview.manager.last_name}\n場所: {interview.location}"
            
            # ステータスごとの色
            if interview.status and interview.status.code == 'tentative':
                color = '#ffc107' # yellow
                textColor = 'black'
            elif interview.status and interview.status.code == 'confirmed':
                color = '#198754' # green
                textColor = 'white'
            elif interview.status and interview.status.code == 'completed':
                color = '#6c757d' # grey
                textColor = 'white'
            else:
                color = '#0d6efd'
                textColor = 'white'
        else:
            # 無関係な他人が見る場合 -> マスキング
            title = "予定あり"
            description = ""
            color = '#6c757d' # grey
            textColor = 'white'

        events.append({
            'title': title,
            'description': description,
            'start': interview.scheduled_at.isoformat(),
            'end': interview.end_at.isoformat() if interview.end_at else (interview.scheduled_at + datetime.timedelta(hours=1)).isoformat(),
            'color': color,
            'textColor': textColor,
        })
        
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def add_event(request):
    """
    イベント簡易登録 (AJAX)
    """
    import json
    data = json.loads(request.body)
    
    title = data.get('title')
    start = data.get('start')
    end = data.get('end')
    category = data.get('category')
    description = data.get('description', '')
    
    if not title or not start or not end:
        return JsonResponse({'status': 'error', 'message': '必須項目が足りません'}, status=400)
        
    ScheduleEvent.objects.create(
        user=request.user,
        title=title,
        start_at=start,
        end_at=end,
        category=category,
        description=description
    )
    
    return JsonResponse({'status': 'success'})
