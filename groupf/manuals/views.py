from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, Http404
from .models import Manual, ViewingHistory, ManualStatusMaster, ManualFile
from .forms import ManualCreateForm, ManualFileUploadForm
import os


@login_required
def manual_list(request):
    """
    マニュアル一覧表示
    - 基本的には「承認済み」のマニュアルのみ表示
    - 自分が作成した「承認待ち」マニュアルも表示
    """
    active_tab = request.GET.get('tab', 'all') 
    
    if active_tab == 'recent':
        histories = ViewingHistory.objects.filter(user=request.user).select_related('manual')
        manuals = [h.manual for h in histories if not h.manual.is_deleted]
        
    elif active_tab == 'bookmark':
        manuals = request.user.bookmarked_manuals.filter(is_deleted=False)
        
    else:
        # 承認済みマニュアル + 自分が作成した承認待ちマニュアル
        try:
            approved_status = ManualStatusMaster.objects.get(code='approved')
            manuals = Manual.objects.filter(
                status=approved_status,
                is_deleted=False
            ) | Manual.objects.filter(
                created_by=request.user,
                is_deleted=False
            )
            manuals = manuals.distinct()
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

    if request.method == "POST":
        form = ManualFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            for f in form.cleaned_data["files"]:
                ManualFile.objects.create(
                    manual=manual,
                    file=f,
                    original_name=f.name,
                )
            return redirect("manual_detail", pk=manual.pk)

        # バリデーションエラー時は詳細画面を再表示
        # 既存の詳細表示ロジックに合わせて context を再構築する必要があるが
        # ここでは簡易的に redirect するか、エラーを表示する形にする。
        # 今回は一旦 detail に戻す
        messages.error(request, "ファイルのアップロードに失敗しました。")
        return redirect("manual_detail", pk=manual.pk)

    return redirect("manual_detail", pk=manual.pk)

@login_required
def manual_file_view(request, file_id):
    try:
        mf = ManualFile.objects.get(id=file_id)
    except ManualFile.DoesNotExist:
        raise Http404("file not found")

    # PDFならinlineで返す（iframe表示できる）
    if (mf.file.name or "").lower().endswith(".pdf"):
        response = FileResponse(mf.file.open("rb"), content_type="application/pdf")
        # 日本語ファイル名対応のため、filename* を使うのがモダンだが簡易的に original_name を使う
        # 必要に応じて URL エンコードなど検討
        response["Content-Disposition"] = f'inline; filename="{mf.original_name or mf.file.name}"'
        return response

    # PDF以外は通常のURLでOK（開くリンクは別でもよい）
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
    return render(request, 'manual/manual_list.html')

@login_required
def manual_delete_preview(request, pk):
    return redirect('manual_list')

@login_required
def manual_delete_execute(request, pk):
    return redirect('manual_list')

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
