from django.urls import path
from . import views

urlpatterns = [
    path('', views.top_page, name='top_page'),
    
    path('task-assign/', views.task_assign_page, name='task_assign_page'),
    path('api/search-tasks/', views.api_search_tasks, name='api_search_tasks'),
    path('api/recommend-users/', views.api_recommend_users, name='api_recommend_users'),
    path('api/execute-assignment/', views.api_execute_assignment, name='api_execute_assignment'),

    path('task_board/', views.task_board, name='task_board'), # Old path kept for safety
    path('task_register/', views.task_register, name='task_register'), # Old path
    path('management/', views.management_support_page, name='management_support_page'),
    
    path('task-board/', views.task_board_page, name='task_board_page'),
    path('task/<int:task_id>/approve/', views.task_approve, name='task_approve'),
    
    path('task/<int:task_id>/assign/', views.assign_task_to_self, name='assign_task_to_self'),
    path('task/<int:task_id>/complete/', views.complete_task_by_user, name='complete_task_by_user'),
    
    path('task-register/', views.task_register_page, name='task_register_page'),
    path('task-guide/', views.task_guide_page, name='task_guide_page'),
    
    path('manager/dashboard/', views.manager_dashboard_view, name='manager_dashboard'),
    path('inbox/', views.my_tasks_page, name='inbox'),
    path('management/csv-import/', views.admin_csv_import_page, name='admin_csv_import_page'),
    
    path('my-tasks/', views.my_tasks_page, name='my_tasks_page'),
    path('my-tasks/<int:task_id>/transfer/', views.task_transfer_page, name='task_transfer_page'),
    path('completed-tasks/', views.completed_task_list_view, name='completed_task_list'),
    path('my-tasks/<int:task_id>/return/', views.task_return_page, name='task_return_page'),
    
    path('interview-advice/', views.interview_advice_menu_page, name='interview_advice_menu_page'),
    path('surprise/', views.surprise_page, name='surprise_page'),
]
