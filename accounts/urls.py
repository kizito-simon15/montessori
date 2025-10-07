from django.urls import path
from .views import (
    create_parent_user, create_teacher_user, create_bursor_user, 
    create_secretary_user, create_academic_user, list_users, 
    update_parent_user, update_teacher_user, update_bursor_user, 
    update_secretary_user, update_academic_user, delete_parent_user, 
    delete_teacher_user, delete_bursor_user, delete_secretary_user, 
    delete_academic_user, CustomLoginView, superuser_dashboard, 
    select_user_type, toggle_user_status,
    toggle_parent_status, toggle_teacher_status, toggle_bursor_status, 
    toggle_secretary_status, toggle_academic_status,
    toggle_all_parents_status, toggle_all_teachers_status, 
    toggle_all_bursors_status, toggle_all_secretaries_status, 
    toggle_all_academics_status, index, accounts_dashboard,
    create_headteacher_user, update_headteacher_user,
    delete_headteacher_user, toggle_headteacher_status, profile_view, profile_edit, toggle_all_headteachers_status

)
from django.contrib.auth import views as auth_views

urlpatterns = [

    
    path('create-headteacher/',           create_headteacher_user,  name='create_headteacher_user'),
    path('update-headteacher/<int:pk>/',  update_headteacher_user,  name='update_headteacher_user'),
    path('delete-headteacher/<int:pk>/',  delete_headteacher_user,  name='delete_headteacher_user'),
    path('toggle-headteacher/<int:user_id>/', toggle_headteacher_status, name='toggle_headteacher_status'),
     path(
        "toggle-headteachers/", toggle_all_headteachers_status, name="toggle_all_headteachers_status"),
     # optional dashboard:
 

    
    path("accounts_dashboard/", accounts_dashboard, name="accounts_dashboard"),
    path('', index, name='index'),  # New index view for the entry point
    path('custom_login/', CustomLoginView.as_view(), name='custom_login'),
    path('superuser_dashboard/', superuser_dashboard, name='superuser_dashboard'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('select_user_type/', select_user_type, name='select_user_type'),

    # Create User Paths
    path('create_parent_user/', create_parent_user, name='create_parent_user'),
    path('create_teacher_user/', create_teacher_user, name='create_teacher_user'),
    path('create_bursor_user/', create_bursor_user, name='create_bursor_user'),
    path('create_secretary_user/', create_secretary_user, name='create_secretary_user'),
    path('create_academic_user/', create_academic_user, name='create_academic_user'),

    # List Users Path
    path('list_users/', list_users, name='list_users'),
    path('list_users/<str:account_type>/', list_users, name='list_users_by_type'),

    # Update User Paths
    path('update_parent_user/<int:pk>/', update_parent_user, name='update_parent_user'),
    path('update_teacher_user/<int:pk>/', update_teacher_user, name='update_teacher_user'),
    path('update_bursor_user/<int:pk>/', update_bursor_user, name='update_bursor_user'),
    path('update_secretary_user/<int:pk>/', update_secretary_user, name='update_secretary_user'),
    path('update_academic_user/<int:pk>/', update_academic_user, name='update_academic_user'),

    # Delete User Paths
    path('delete_parent_user/<int:pk>/', delete_parent_user, name='delete_parent_user'),
    path('delete_teacher_user/<int:pk>/', delete_teacher_user, name='delete_teacher_user'),
    path('delete_bursor_user/<int:pk>/', delete_bursor_user, name='delete_bursor_user'),
    path('delete_secretary_user/<int:pk>/', delete_secretary_user, name='delete_secretary_user'),
    path('delete_academic_user/<int:pk>/', delete_academic_user, name='delete_academic_user'),

    path('toggle_user_status/<int:user_id>/', toggle_user_status, name='toggle_user_status'),
    path('toggle_parent_status/<int:user_id>/', toggle_parent_status, name='toggle_parent_status'),
    path('toggle_teacher_status/<int:user_id>/', toggle_teacher_status, name='toggle_teacher_status'),
    path('toggle_bursor_status/<int:user_id>/', toggle_bursor_status, name='toggle_bursor_status'),
    path('toggle_secretary_status/<int:user_id>/', toggle_secretary_status, name='toggle_secretary_status'),
    path('toggle_academic_status/<int:user_id>/', toggle_academic_status, name='toggle_academic_status'),
    path('toggle_all_parents_status/', toggle_all_parents_status, name='toggle_all_parents_status'),
    path('toggle_all_teachers_status/', toggle_all_teachers_status, name='toggle_all_teachers_status'),
    path('toggle_all_bursors_status/', toggle_all_bursors_status, name='toggle_all_bursors_status'),
    path('toggle_all_secretaries_status/', toggle_all_secretaries_status, name='toggle_all_secretaries_status'),
    path('toggle_all_academics_status/', toggle_all_academics_status, name='toggle_all_academics_status'),

    path("profile/",       profile_view, name="profile"),
    path("profile/edit/",  profile_edit, name="profile_edit"),
]