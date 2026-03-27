from django.contrib import admin
from .models import User, UserProfile, UserGoalSettings, PrivacySettings, DailyStats, BlockedUser, UserSession

admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(UserGoalSettings)
admin.site.register(PrivacySettings)
admin.site.register(DailyStats)
admin.site.register(BlockedUser)
admin.site.register(UserSession)
