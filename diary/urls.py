from django.urls import path
from .views import (
    DiaryDailyView, AddFoodEntryView, UpdateFoodEntryView, DeleteFoodEntryView, SmartSwapsView,
    AddWorkoutLogView, WorkoutHistoryView,
    WeeklyScheduleView, TodayWorkoutView, WorkoutTemplateListView,
    WeightLogView, WeightGoalView
)

urlpatterns = [
    path('', DiaryDailyView.as_view(), name='food-diary'),
    path('add/', AddFoodEntryView.as_view(), name='add-food'),
    path('update/<int:pk>/', UpdateFoodEntryView.as_view(), name='update-food'),
    path('delete/<int:pk>/', DeleteFoodEntryView.as_view(), name='delete-food'),
    path('smart-swaps/', SmartSwapsView.as_view(), name='smart-swaps'),
    path('workout/add/', AddWorkoutLogView.as_view(), name='add-workout'),
    path('workout/history/', WorkoutHistoryView.as_view(), name='workout-history'),
    path('workout/schedule/', WeeklyScheduleView.as_view(), name='workout-schedule'),
    path('workout/today/', TodayWorkoutView.as_view(), name='workout-today'),
    path('workout/templates/', WorkoutTemplateListView.as_view(), name='workout-templates'),
    # Weight tracking
    path('weight/', WeightLogView.as_view(), name='weight-log'),
    path('weight/goal/', WeightGoalView.as_view(), name='weight-goal'),
]
