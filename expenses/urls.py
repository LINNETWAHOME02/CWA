from django.urls import path
from expenses import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('upload/', views.upload_excel, name='upload'),
    path('report/<int:member_id>/', views.generate_report, name='generate_report'),
    path('report-pdf/<int:member_id>/', views.generate_pdf, name='generate_pdf'),
    path('edit/<int:member_id>/', views.edit_contributions, name='edit_contributions'),
    path('delete/<int:member_id>/', views.delete_member, name='delete_member'),
    path('delete-all/', views.delete_all, name='delete_all'),
]