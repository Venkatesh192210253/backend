from django.urls import path
from .views import (
    RegisterView, LoginView, VerifyTokenView, 
    ProfileView,
    GenerateOTPView, VerifyOTPView,
    ForgotPasswordView, VerifyResetOtpView, ResetPasswordView,
    CompleteGoalsView, DailyStatsView, DetailedStatsView, DashboardDataView,
    send_friend_request, accept_friend_request, reject_friend_request, get_friend_requests, get_friends, remove_friend,
    create_group, get_my_groups, accept_group_invite, search_users,
    get_group_detail, create_challenge, get_group_challenges,
    delete_group, delete_challenge, join_challenge, get_challenge_participants,
    get_suggested_friends, invite_to_group, reject_group_invite, get_group_messages, send_group_message,
    chat_with_ai,
    PrivacySettingsView, ChangePasswordView,
    DeleteAccountView, DownloadDataView,
    BlockUserView, UnblockUserView, BlockedUsersListView,
    ListSessionsView, RevokeSessionView, GoalSettingsView, AchievementsView,
    compare_stats,
    trained_ai_ask
)

urlpatterns = [
    # Auth APIs
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/verify/', VerifyTokenView.as_view(), name='verify-token'),
    
    # Profile APIs
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileView.as_view(), name='profile-update'),
    
    # Onboarding APIs
    path('onboarding/complete-goals/', CompleteGoalsView.as_view(), name='complete-goals'),
    
    # OTP & Password Reset (Keeping existing for completeness)
    path('otp/generate/', GenerateOTPView.as_view(), name='generate-otp'),
    path('otp/verify/', VerifyOTPView.as_view(), name='verify-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-reset-otp/', VerifyResetOtpView.as_view(), name='verify-reset-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    
    # Stats APIs
    path('stats/daily/', DailyStatsView.as_view(), name='daily-stats'),
    path('stats/detailed/', DetailedStatsView.as_view(), name='detailed-stats'),
    path('stats/achievements/', AchievementsView.as_view(), name='achievements'),
    path('dashboard/data/', DashboardDataView.as_view(), name='dashboard-data'),

    # Friends APIs
    path('friends/', get_friends),
    path('friends/search/', search_users),
    path('friends/send-request/', send_friend_request),
    path('friends/accept/', accept_friend_request),
    path('friends/requests/', get_friend_requests),
    path('friends/reject/', reject_friend_request),
    path('friends/remove/', remove_friend),
    path('friends/suggestions/', get_suggested_friends),
    path('friends/compare/<int:friend_id>/', compare_stats),

    # Groups APIs
    path('groups/create/', create_group),
    path('groups/my/', get_my_groups),
    path('groups/accept/', accept_group_invite),
    path('groups/reject/', reject_group_invite),
    path('groups/invite/', invite_to_group),
    path('groups/detail/<int:group_id>/', get_group_detail),
    path('groups/<int:group_id>/messages/', get_group_messages),
    path('groups/<int:group_id>/messages/send/', send_group_message),
    path('groups/create-challenge/', create_challenge),
    path('groups/challenges/<int:group_id>/', get_group_challenges),
    path('groups/delete/<int:group_id>/', delete_group),
    path('groups/challenges/delete/<int:challenge_id>/', delete_challenge),
    path('groups/challenges/join/<int:challenge_id>/', join_challenge),
    path('groups/challenges/participants/<int:challenge_id>/', get_challenge_participants),
    
    # AI Assistant
    path('ai/chat/', chat_with_ai),
    
    # Settings and Security
    path('privacy-settings/', PrivacySettingsView.as_view(), name='privacy-settings'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/delete/', DeleteAccountView.as_view(), name='delete-account'),
    
    path('profile/download-data/', DownloadDataView.as_view(), name='download-data'),
    
    path('users/block/', BlockUserView.as_view(), name='block-user'),
    path('users/unblock/', UnblockUserView.as_view(), name='unblock-user'),
    path('users/blocked/', BlockedUsersListView.as_view(), name='blocked-users'),
    
    path('sessions/', ListSessionsView.as_view(), name='list-sessions'),
    path('sessions/revoke/', RevokeSessionView.as_view(), name='revoke-session'),

    path('goal-settings/', GoalSettingsView.as_view(), name='goal-settings'),
    
    # Trained AI
    path('trained-ai/ask/', trained_ai_ask, name='trained-ai-ask'),
]
