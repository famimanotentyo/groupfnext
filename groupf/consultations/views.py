from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q
import json

from django.conf import settings

from .models import Consultation, ConsultationMessage, ConsultationStatusMaster, Question
from manuals.models import Manual
from notifications.models import Notification, NotificationTypeMaster
from .forms import ConsultationCreateForm, ConsultationMessageForm

# Gemini config (if needed here, though logic is in resolve)
from openai import OpenAI
import os

@login_required
def consultation_list_view(request):
    """
    相談一覧画面
    自分が「相談した件」と「相談された件」を表示
    """
    user = request.user
    
    # 自分が質問した相談
    my_questions = Consultation.objects.filter(requester=user).order_by('-updated_at')
    
    # 自分に来ている相談
    received_requests = Consultation.objects.filter(respondent=user).order_by('-updated_at')

    # --- 統一検索ロジック (Topから移動) ---
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

    context = {
        'page_title': '相談・チャット一覧',
        'my_questions': my_questions,
        'received_requests': received_requests,
        'search_query': search_query,
        'search_results': search_results,
    }
    return render(request, 'consultation/list.html', context)

@login_required
def consultation_create_view(request):
    """
    新規相談の作成
    """
    if request.method == 'POST':
        form = ConsultationCreateForm(request.POST, user=request.user)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.requester = request.user
            
            # ステータスを「解決中(open)」に設定
            try:
                open_status = ConsultationStatusMaster.objects.get(code='open')
                consultation.status = open_status
            except:
                pass # マスタがない場合は一旦スルー

            consultation.save()
            messages.success(request, f'{consultation.respondent.last_name}さんへの相談を開始しました。')
            return redirect('consultation_detail_view', pk=consultation.pk)
    else:
        form = ConsultationCreateForm(user=request.user)

    return render(request, 'consultation/create.html', {'form': form, 'page_title': '新規相談'})

@login_required
def consultation_detail_view(request, pk):
    """
    チャット画面（詳細）
    """
    consultation = get_object_or_404(Consultation, pk=pk)
    
    # 権限チェック（関係ない人は見れない）
    if request.user != consultation.requester and request.user != consultation.respondent:
        # 管理者は見てもいいならここに条件追加
        return redirect('consultation_list_view')

    # メッセージ送信処理
    if request.method == 'POST':
        form = ConsultationMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.consultation = consultation
            message.sender = request.user
            message.save()
            
            # 相談の更新日時を更新（一覧で上に上げるため）
            consultation.updated_at = timezone.now()
            consultation.save()
            
            # --- 通知の作成 ---
            # メッセージ送信者が requester なら recipient は respondent (逆も然り)
            recipient = consultation.respondent if request.user == consultation.requester else consultation.requester
            
            # 自分への通知は不要なので、相手に送る
            if recipient != request.user:
                # 通知タイプの取得・作成
                notif_type, _ = NotificationTypeMaster.objects.get_or_create(
                    code='consultation_message',
                    defaults={'name': '相談メッセージ'}
                )
                
                Notification.objects.create(
                    recipient=recipient,
                    title='相談メッセージ',
                    message=f'{request.user.last_name}さんから相談メッセージが届きました。確認してみましょう',
                    notification_type=notif_type,
                    related_object_id=consultation.id,
                    link_url=f"/consultations/{consultation.id}/" # 本当は reverseを使うべきだが簡易実装
                )
            
            return redirect('consultation_detail_view', pk=pk)
    else:
        form = ConsultationMessageForm()

    context = {
        'consultation': consultation,
        'messages_list': consultation.messages.all().select_related('sender'),
        'form': form,
    }
    return render(request, 'consultation/detail.html', context)


@login_required
def consultation_resolve(request, pk):
    """
    相談を解決済みにし、Geminiで会話内容を要約して「ナレッジ(Question)」を作成する
    """
    consultation = get_object_or_404(Consultation, pk=pk)
    
    # 権限チェック
    if request.user != consultation.requester and request.user != consultation.respondent:
        return redirect('consultation_list_view')

    if request.method == 'POST':
        # 1. ステータスを「解決済み(resolved)」に変更
        try:
            resolved_status = ConsultationStatusMaster.objects.get(code='resolved')
            consultation.status = resolved_status
            consultation.save()
        except:
            messages.error(request, 'ステータスマスタ(resolved)がありません。')
            return redirect('consultation_detail_view', pk=pk)

        # 2. 会話ログの収集
        chat_history = ""
        for msg in consultation.messages.all().order_by('created_at'):
            chat_history += f"[{msg.sender.last_name}]: {msg.content}\n"

        # 3. OpenAIによる要約生成 (APIキーがある場合のみ)
        ai_data = {}
        ai_success = False

        if settings.OPENAI_API_KEY:
            try:
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                
                # プロンプトの作成
                prompt = f"""
                あなたは親切で丁寧な社内ナレッジ管理者です。
                以下の社内チャットの履歴を読み、他の社員にも役立つ「ナレッジ」として整理してください。
                
                【重要】
                - 誰にでもわかる、優しく丁寧な言葉遣い（です・ます調）で書いてください。
                - 専門用語には簡単な解説を加えるなど、初心者にも配慮してください。
                - 読む人が「なるほど！」と安心できるようなトーンでお願いします。

                【判定について】
                チャットの内容から、最終的に「解決した」か「解決しなかった（「わからない」「解決できず」などで終わっている）」かを判断してください。

                出力は以下のJSON形式のみで行ってください。
                
                {{
                    "title": "一目で内容がわかる、親しみやすいタイトル(30文字以内)",
                    "problem": "どのようなことで困っていたか（優しく要約）",
                    "solution": "どのように解決したか（手順などを分かりやすく、ステップ形式などで）",
                    "is_solved": true または false (解決していない場合は false)
                }}

                --- チャット履歴 ---
                {chat_history}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes chat history into knowledge base entries. You always output valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                raw_text = response.choices[0].message.content
                import json
                ai_data = json.loads(raw_text)
                ai_success = True

            except Exception as e:
                print(f"AI Summary Error: {e}")
                # 失敗時は空の辞書または失敗メッセージを入れる（後続でデフォルト値が入る）
        
        else:
            print("OpenAI API Key is missing. Skipping AI summary.")
        
        # 4. Question(ナレッジ)モデルへの保存
        # APIキーがない、または失敗した場合は「要約失敗/手動修正待ち」として保存する
        
        # AIが「解決していない」と判断した場合はナレッジを作成しない
        is_solved = ai_data.get('is_solved', True) # キーがない場合はTrue扱いにする（後方互換）ただしAPI成功時のみ有効
        
        if ai_success and not is_solved:
             messages.warning(request, '相談を終了しました。（解決に至らなかったと判断されたため、ナレッジ化はスキップしました）')
        else:
            title = ai_data.get('title', consultation.title)
            
            if ai_success:
                problem = ai_data.get('problem', '自動生成失敗')
                solution = ai_data.get('solution', '自動生成失敗')
                msg_text = '相談を解決しました。AIが会話を要約し、ナレッジベースに登録しました！'
                msg_level = messages.SUCCESS
            else:
                problem = "【自動要約失敗】\nAPIキーが設定されていないか、AI処理中にエラーが発生しました。\nここを手動で編集して、課題内容を記述してください。"
                solution = "【解決策未記入】\nここを手動で編集して、解決手順を記述してください。"
                msg_text = '相談を解決しました。（AI要約はスキップされました。ナレッジの内容を手動で修正してください）'
                msg_level = messages.WARNING

            Question.objects.create(
                source_consultation=consultation,
                title=title,
                problem_summary=problem,
                solution_summary=solution,
                created_by=request.user
            )
            
            messages.add_message(request, msg_level, msg_text)

        return redirect('consultation_list_view')

    return redirect('consultation_detail_view', pk=pk)
