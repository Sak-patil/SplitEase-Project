from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 1. The Landing/Home Page (Requires Login)
    path('home/', views.home, name='home'), 

    # 2. Authentication (Login/Logout)
    # This uses Django's built-in login system
    path('login/', auth_views.LoginView.as_view(template_name='expenses/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', views.signup, name='signup'),

    # 3. Trip Management
    path('create/', views.create_trip, name='create_trip'),
    path('trip/<int:trip_id>/', views.trip_dashboard, name='trip_dashboard'),
    path('trip/delete/<int:trip_id>/', views.delete_trip, name='delete_trip'),

    # 4. Expense & Settlement Logic
    path('trip/<int:trip_id>/add/', views.add_expense, name='add_expense'),
    path('settle/<int:debt_id>/', views.settle_debt, name='settle_debt'),
    path('trip/<int:trip_id>/settle/<int:debtor_id>/<int:creditor_id>/', views.settle_debt_simplified, name='settle_debt_simplified'),

    path('expense/delete/<int:expense_id>/', views.delete_expense, name='delete_expense'),
]