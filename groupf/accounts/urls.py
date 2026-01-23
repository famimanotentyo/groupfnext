from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.account_logout_view_page, name='account_logout_view_page'),
    path('logout/success/', views.account_logout_success_page, name='logout_success'),
    
    path('initial-login/', views.initial_login_page, name='initial_login_page'),
    path('register-profile/', views.profile_registration_page, name='profile_registration_page'),
    path('process-registration/', views.process_registration, name='process_registration'),
    
    path('account/create/', views.account_create_page, name='account_create_page'),
    path('account/create/success/', views.account_create_success_page, name='account_create_success_page'),
    path('account/', views.account_management_page, name='account_management_page'),
    path('accounts/', views.account_list_page, name='account_list_page'),
    path('accounts/profile/', views.account_detail_page, name='account_detail_page'),
    path('accounts/profile-edit/', views.profile_edit_page, name='profile_edit_page'),
    path('accounts/edit/<int:pk>/', views.account_edit_page, name='account_edit_page'),
    
    path('password-reset/request/', views.password_reset_request_view, name='password_reset_request'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    path('profile/<int:pk>/', views.user_profile_detail, name='user_profile_detail'),
    path('member-list/', views.member_list_view, name='member_list'),
    path('management/member/<int:pk>/', views.manager_member_detail, name='manager_member_detail'),
    path('api/accounts/<int:user_id>/', views.api_account_detail, name='api_account_detail'),
]
