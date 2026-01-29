from django.urls import path
from . import views

urlpatterns = [
    # path('manuals/', ... ) prefix will be added in main urls
    path('', views.manual_list, name='manual_list'),
    path('approval/', views.manual_approval_list, name='manual_approval_list'), 
    path('reject/<int:pk>/', views.manual_reject, name='manual_reject'),
    path('create/', views.manual_create_view, name='manual_create_view'),
    path('detail/<int:pk>/', views.manual_detail, name='manual_detail'),
    
    path('interview-request/', views.interview_request_page, name='interview_request_page'),
    
    path('delete/select/', views.manual_delete_select_list, name='manual_delete_select_list'),
    path('delete/preview/<int:pk>/', views.manual_delete_preview, name='manual_delete_preview'),
    path('delete/execute/<int:pk>/', views.manual_delete_execute, name='manual_delete_execute'),
    
    path('favorite/<int:pk>/', views.toggle_manual_favorite, name='toggle_manual_favorite'),
    path('pending/', views.manual_pending_list_view, name='manual_pending_list'),
    
    # Updated/Added paths
    path('<int:pk>/', views.manual_detail_view, name='manual_detail_view_alias'), # Alias
    path("<int:pk>/files/upload/", views.manual_files_upload, name="manual_files_upload"),
    path("files/<int:file_id>/view/", views.manual_file_view, name="manual_file_view"),
]
