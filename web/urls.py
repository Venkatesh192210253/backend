from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('food/', views.food_view, name='food'),
    path('workout/', views.workout_view, name='workout'),
    path('friends/', views.friends_view, name='friends'),
    path('profile/', views.profile_view, name='profile'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('ai-coach/', views.ai_coach_view, name='ai_coach'),
    path('ai-search/', views.ai_food_search_json, name='ai_search'),
    path('water-update/', views.water_update, name='water_update'),
    path('food-delete/<int:entry_id>/', views.food_delete, name='food_delete'),
    path('group/<int:group_id>/', views.group_detail_view, name='group_detail'),
    path('goal-settings/', views.goal_settings_view, name='goal_settings'),
    path('privacy-security/', views.privacy_security_view, name='privacy_security'),
    path('help-support/', views.help_support_view, name='help_support'),
    path('weight/', views.weight_view, name='weight_log'),
    path('weight-delete/<int:entry_id>/', views.weight_delete, name='weight_delete'),
]
