from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, Http404
from .models import Manual, ViewingHistory, ManualStatusMaster, ManualFile
from django.db.models import Q
from notifications.models import Notification, NotificationTypeMaster
from .forms import ManualCreateForm, ManualFileUploadForm
import os
import mimetypes
import zipfile
import io



@login_required
def manual_list(request):
    """
    マニュアル一覧表示
    - 基本的には「承認済み」のマニュアルのみ表示
    - 自分が作成した「承認待ち」マニュアルも表示
    """
    active_tab = request.GET.get('tab', 'all') 
    
    if active_tab == 'recent':
        histories = ViewingHistory.objects.filter(user=request.user).select_related('manual', 'manual__created_by', 'manual__status')
        manuals = [h.manual for h in histories if not h.manual.is_deleted]
        
    elif active_tab == 'bookmark':
        manuals = request.user.bookmarked_manuals.filter(is_deleted=False).select_related('created_by', 'status').prefetch_related('files')
        
    else:
        # 承認済みマニュアル + 自分が作成した承認待ちマニュアル（却下は除く）
        try:
            approved_status = ManualStatusMaster.objects.get(code='approved')
            
            # 承認済み OR (自分の作成 かつ 削除されていない かつ 却下されていない)
            manuals = Manual.objects.filter(
                Q(status=approved_status, is_deleted=False) |
                (Q(created_by=request.user, is_deleted=False) & ~Q(status__code='rejected'))
            ).distinct().select_related('created_by', 'status').prefetch_related('files')
            
        except ManualStatusMaster.DoesNotExist:
                # ステータスマスタがない場合は全て表示
                manuals = Manual.objects.filter(is_deleted=False)

    context = {
        'manuals': manuals,
        'active_tab': active_tab,
        'page_title': 'マニュアル一覧'
    } 
    return render(request, 'manual/manual_list.html', context)


def manual_detail(request, pk):
    manual = get_object_or_404(Manual, pk=pk)
    
    if request.user.is_authenticated:
        ViewingHistory.objects.update_or_create(
            user=request.user,
            manual=manual
        )
    
    # 追加: 添付ファイル取得
    files = manual.files.all().order_by("-uploaded_at")
    form = ManualFileUploadForm()

    context = { 
        'manual': manual, 
        'page_title': manual.title,
        'files': files,
        'upload_form': form,
    }
    return render(request, 'manual/manual_detail.html', context)

@login_required
def manual_files_upload(request, pk):
    manual = get_object_or_404(Manual, pk=pk, is_deleted=False)

    if request.method != "POST":
        return redirect("manual_detail", pk=manual.pk)

    files = request.FILES.getlist("files")  # ✅ 複数を確実に取る
    if not files:
        messages.error(request, "ファイルが選択されていません。")
        return redirect("manual_detail", pk=manual.pk)

    for f in files:
        ManualFile.objects.create(
            manual=manual,
            file=f,
            original_name=getattr(f, "name", "")
        )

    messages.success(request, f"{len(files)} 件アップロードしました。")

    # 追記: マネージャー以外（部下）がファイルを投稿した場合は「承認待ち」に戻す
    # 権限がない(None)場合も部下とみなして承認待ちにする
    is_manager_or_admin = request.user.role and request.user.role.code in ['manager', 'admin']
    if not is_manager_or_admin:
        try:
            pending_status = ManualStatusMaster.objects.get(code='pending')
            # 既に pending なら変更不要だが、approved などの場合は pending に戻す
            if manual.status != pending_status:
                manual.status = pending_status
                manual.approved_by = None
                manual.approved_at = None
                manual.save()
                messages.info(request, "ファイルを投稿したため、ステータスが「承認待ち」に変更されました。")
        except ManualStatusMaster.DoesNotExist:
            pass # マスタ未設定時は何もしない（あるいはログ出すなど）

    return redirect("manual_detail", pk=manual.pk)

@login_required
def manual_file_view(request, file_id):
    try:
        mf = ManualFile.objects.get(id=file_id)
    except ManualFile.DoesNotExist:
        raise Http404("file not found")

    name = (mf.file.name or "").lower()

    # PDF：iframe用に inline
    if name.endswith(".pdf"):
        response = FileResponse(mf.file.open("rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{mf.original_name or mf.file.name}"'
        return response

    # 画像だけ：img表示できるように content_type を付けて inline にする
    if name.endswith((".png", ".jpg", ".jpeg")):
        ctype, _ = mimetypes.guess_type(name)
        response = FileResponse(mf.file.open("rb"), content_type=ctype or "image/jpeg")
        response["Content-Disposition"] = f'inline; filename="{mf.original_name or mf.file.name}"'
        return response

    # それ以外：従来通り（必要なら attachment にしてもOK）
    return FileResponse(mf.file.open("rb"))


@login_required
def toggle_manual_favorite(request, pk):
    manual = get_object_or_404(Manual, pk=pk)
    
    if manual.bookmarks.filter(id=request.user.id).exists():
        manual.bookmarks.remove(request.user)
        messages.success(request, f'「{manual.title}」をブックマークから外しました。')
    else:
        manual.bookmarks.add(request.user)
        messages.success(request, f'「{manual.title}」をブックマークしました。')
    
    return redirect(request.META.get('HTTP_REFERER', 'manual_list'))

def interview_request_page(request): # Keep here as per original, though maybe belongs in interviews
    context = { 'page_title': '面談依頼' }
    return render(request, 'manual/interview_request.html', context)

@login_required
def manual_approval_list(request):
    """
    マニュアル承認処理（マネージャー以上のみ）
    """
    # 権限チェック
    if not (request.user.role and request.user.role.code in ['manager', 'admin']):
        messages.error(request, 'この機能はマネージャー以上の権限が必要です。')
        return redirect('manual_list')
    
    manual_id = request.GET.get('manual_id')
    
    if manual_id:
        try:
            manual = Manual.objects.get(pk=manual_id, is_deleted=False)
            
            # ステータスを「承認待ち」から「公開中」に変更
            approved_status = ManualStatusMaster.objects.get(code='approved')
            manual.status = approved_status
            manual.approved_by = request.user
            manual.approved_at = timezone.now()
            manual.save()
            
            messages.success(request, f'「{manual.title}」を承認しました。')
        except Manual.DoesNotExist:
            messages.error(request, '指定されたマニュアルが見つかりません。')
        except ManualStatusMaster.DoesNotExist:
            messages.error(request, 'ステータスマスタが見つかりません。')
    
    return redirect('manual_pending_list')


@login_required
def manual_reject(request, pk):
    """
    マニュアル却下処理（マネージャー以上のみ）
    """
    # 権限チェック
    if not (request.user.role and request.user.role.code in ['manager', 'admin']):
        messages.error(request, 'この機能はマネージャー以上の権限が必要です。')
        return redirect('manual_list')
    
    manual = get_object_or_404(Manual, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '')
        
        try:
            # ステータスを「却下」に変更
            rejected_status = ManualStatusMaster.objects.get(code='rejected')
            manual.status = rejected_status
            
            # 論理削除については、要件文に「承認まちから論理削除、状態を却下にする」とあるが
            # モデル定義上は status='rejected' で表現し、一覧から除外する運用が自然かもしれない。
            # ただし、is_deleted=Trueにしてしまうと、ユーザー自身も見れなくなる可能性がある。
            # 要件「上司画面で...承認まちから論理削除」 -> 承認待ちリストから消えるという意味と解釈し、ステータス変更で対応。
            # もし本当に is_deleted=True にすると、修正して再申請ができなくなる（ゴミ箱行き）ので、
            # ここでは status='rejected' に変更するだけにとどめる（pendingリストからは消える）。
            # ※ユーザー要望の「マニュアルを投稿した部下に通知を送るって承認まちから論理削除、状態を却下にする」
            #   -> status='rejected' にすれば pending ではなくなるのでOK。
            #   -> もし is_deleted=True も必要なら追加するが、通常はステータス管理で行う。
            #   -> 文脈的に「承認待ち一覧から消す」という意味合いが強いと判断。
            
            manual.save()
            
            # 通知作成
            notif_type = NotificationTypeMaster.objects.get(code='manual_reject')
            Notification.objects.create(
                recipient=manual.created_by,
                title="マニュアルが却下されました",
                message=f"マニュアル「{manual.title}」が却下されました。\n理由: {reason}",
                notification_type=notif_type,
                related_object_id=manual.pk,
                link_url=f"/manuals/detail/{manual.pk}/" # 修正画面などへのリンクが望ましいが一旦詳細へ
            )
            
            messages.warning(request, f'「{manual.title}」を却下しました。')
            
        except ManualStatusMaster.DoesNotExist:
            messages.error(request, 'ステータスマスタ(rejected)が見つかりません。')
        except NotificationTypeMaster.DoesNotExist:
            messages.error(request, '通知タイプマスタ(manual_reject)が見つかりません。')
            
    return redirect('manual_pending_list')

@login_required
def manual_create_view(request):
    """
    マニュアル作成ビュー
    - manager/admin: 直接公開（approved）
    - employee: 承認待ち（pending）
    """
    if request.method == 'POST':
        form = ManualCreateForm(request.POST, request.FILES)
        if form.is_valid():
            manual = form.save(commit=False)
            manual.created_by = request.user
            
            # 権限に応じてステータスを設定
            if request.user.role and request.user.role.code in ['manager', 'admin']:
                # マネージャー以上は直接公開
                try:
                    approved_status = ManualStatusMaster.objects.get(code='approved')
                    manual.status = approved_status
                    manual.approved_by = request.user  # 自己承認として記録
                    manual.approved_at = timezone.now()
                    messages.success(request, 'マニュアルを公開しました。')
                except ManualStatusMaster.DoesNotExist:
                    # ステータスマスタがない場合はnullで保存（警告表示）
                    messages.warning(request, 'マニュアルを作成しましたが、ステータスマスタが未設定です。')
            else:
                # 従業員は承認待ち
                try:
                    pending_status = ManualStatusMaster.objects.get(code='pending')
                    manual.status = pending_status
                    messages.info(request, 'マニュアルを作成しました。承認されると公開されます。')
                except ManualStatusMaster.DoesNotExist:
                    messages.warning(request, 'マニュアルを作成しましたが、ステータスマスタが未設定です。')
            
            manual.save()
            return redirect('manual_list')
    else:
        form = ManualCreateForm()
    return render(request, 'manual/manual_create.html', {'form': form})

# Placeholders for missing views from original urls
@login_required
def manual_delete_select_list(request):
    """
    削除対象マニュアル選択画面
    - マネージャー以上：全マニュアル
    - 一般社員：アクセス不可（リダイレクト）
    """
    # 権限チェック (Admin or Manager Only)
    if not (request.user.role and request.user.role.code in ['admin', 'manager']):
        messages.error(request, 'この機能はマネージャー以上の権限が必要です。')
        return redirect('manual_list')

    query = request.GET.get('q')

    # 全マニュアルを取得
    manuals = Manual.objects.filter(is_deleted=False)

    # 検索フィルタ
    if query:
        manuals = manuals.filter(title__icontains=query)

    manuals = manuals.select_related('created_by').order_by('-created_at')

    context = {
        'manuals': manuals,
        'page_title': '削除するマニュアルを選択',
    }
    return render(request, 'manual/manual_delete_select_list.html', context)

@login_required
def manual_delete_preview(request, pk):
    """
    削除確認画面
    """
    # 権限チェック
    if not (request.user.role and request.user.role.code in ['admin', 'manager']):
        messages.error(request, 'この機能はマネージャー以上の権限が必要です。')
        return redirect('manual_list')

    manual = get_object_or_404(Manual, pk=pk)
    
    context = {
        'manual': manual,
        'page_title': 'マニュアル削除確認',
    }
    return render(request, 'manual/manual_delete_preview.html', context)

@login_required
def manual_delete_execute(request, pk):
    """
    削除実行処理（論理削除）
    """
    # 権限チェック
    if not (request.user.role and request.user.role.code in ['admin', 'manager']):
        messages.error(request, 'この機能はマネージャー以上の権限が必要です。')
        return redirect('manual_list')

    manual = get_object_or_404(Manual, pk=pk)
    
    # 論理削除
    manual.is_deleted = True
    manual.save()
    
    messages.warning(request, f'マニュアル「{manual.title}」を削除しました。')
    return redirect('manual_delete_select_list')

@login_required
def manual_list_view(request):
     return manual_list(request)

@login_required
def manual_pending_list_view(request):
    """
    承認待ちマニュアル一覧（マネージャー以上のみアクセス可能）
    """
    # 権限チェック
    if not (request.user.role and request.user.role.code in ['manager', 'admin']):
        messages.error(request, 'この機能はマネージャー以上の権限が必要です。')
        return redirect('manual_list')
    
    # 承認待ちマニュアルを取得
    try:
        pending_status = ManualStatusMaster.objects.get(code='pending')
        pending_manuals = Manual.objects.filter(
            status=pending_status,
            is_deleted=False
        ).select_related('created_by', 'status').order_by('-created_at')
    except ManualStatusMaster.DoesNotExist:
        pending_manuals = []
    
    context = {
        'manuals': pending_manuals,
        'page_title': '承認待ちマニュアル'
    }
    return render(request, 'manual/manual_pending_list.html', context)

@login_required
def manual_detail_view(request, pk):
    return manual_detail(request, pk)


@login_required
def manual_download_zip(request, pk):
    """
    マニュアルに関連するファイルをまとめてZIPでダウンロード
    """
    manual = get_object_or_404(Manual, pk=pk)
    
    # ZIPファイルを作成するメモリバッファ
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        # メインファイル
        if manual.file:
            try:
                file_path = manual.file.path
                if os.path.exists(file_path):
                    filename = os.path.basename(manual.file.name)
                    z.write(file_path, filename)
            except Exception:
                pass # ファイルが見つからない場合はスキップ

        # 添付ファイル
        for mf in manual.files.all():
            if mf.file:
                try:
                    file_path = mf.file.path
                    if os.path.exists(file_path):
                        # ファイル名 (オリジナル名優先、なければファイル名)
                        filename = mf.original_name or os.path.basename(mf.file.name)
                        # 同じ名前のファイルがZIP内にあると上書き等の問題が出るため、
                        # 簡易的にIDを付与してユニークにする
                        base, ext = os.path.splitext(filename)
                        filename = f"{base}_{mf.id}{ext}"
                        
                        z.write(file_path, filename)
                except Exception:
                    pass

    buffer.seek(0)
    
    # ダウンロードファイル名
    zip_filename = f"{manual.title}.zip"
    
    return FileResponse(buffer, as_attachment=True, filename=zip_filename)
