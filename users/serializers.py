from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import (
    UserProfile, Goal, DailyStats, FriendRequest, Friend, Group, 
    GroupMember, Challenge, PrivacySettings, BlockedUser, UserSession, 
    UserGoalSettings, Achievement, UserAchievement
)

User = get_user_model()

from diary.serializers import WeightGoalSerializer

class UserProfileSerializer(serializers.ModelSerializer):
    achievements_count = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ('bio', 'profile_photo', 'fitness_level', 'streak', 'longest_streak', 'level', 'workouts_completed', 'xp', 'full_name', 'achievements_count')

    def get_achievements_count(self, obj):
        return UserAchievement.objects.filter(user=obj.user).count()

class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ('id', 'goal_type', 'created_at')

class DailyStatsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='userid_id', read_only=True)
    calories_consumed = serializers.SerializerMethodField()
    calories_burned = serializers.SerializerMethodField()
    water_ml = serializers.SerializerMethodField()
    workouts_completed = serializers.SerializerMethodField()
    protein_consumed = serializers.SerializerMethodField()
    carbs_consumed = serializers.SerializerMethodField()
    fat_consumed = serializers.SerializerMethodField()

    class Meta:
        model = DailyStats
        fields = ('id', 'date', 'steps', 'calories_consumed', 'calories_burned', 'water_ml', 'workouts_completed', 'protein_consumed', 'carbs_consumed', 'fat_consumed')
        read_only_fields = ('id', 'date')

    def get_calories_consumed(self, obj):
        from diary.models import FoodEntry
        from django.db.models import Sum
        return FoodEntry.objects.filter(user=obj.userid, date=obj.date).aggregate(Sum('calories'))['calories__sum'] or 0

    def get_calories_burned(self, obj):
        from diary.models import WorkoutLog
        from django.db.models import Sum
        return WorkoutLog.objects.filter(user=obj.userid, date=obj.date).aggregate(Sum('calories_burned'))['calories_burned__sum'] or 0

    def get_water_ml(self, obj):
        from diary.models import WaterIntake
        from django.db.models import Sum
        return WaterIntake.objects.filter(user=obj.userid, date=obj.date).aggregate(Sum('amount_ml'))['amount_ml__sum'] or 0

    def get_workouts_completed(self, obj):
        from diary.models import WorkoutLog
        return WorkoutLog.objects.filter(user=obj.userid, date=obj.date).count()

    def get_protein_consumed(self, obj):
        from diary.models import FoodEntry
        from django.db.models import Sum
        return FoodEntry.objects.filter(user=obj.userid, date=obj.date).aggregate(Sum('protein'))['protein__sum'] or 0

    def get_carbs_consumed(self, obj):
        from diary.models import FoodEntry
        from django.db.models import Sum
        return FoodEntry.objects.filter(user=obj.userid, date=obj.date).aggregate(Sum('carbs'))['carbs__sum'] or 0

    def get_fat_consumed(self, obj):
        from diary.models import FoodEntry
        from django.db.models import Sum
        return FoodEntry.objects.filter(user=obj.userid, date=obj.date).aggregate(Sum('fat'))['fat__sum'] or 0

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='profile.full_name', read_only=True)
    profile_image = serializers.ImageField(source='profile.profile_photo', read_only=True)
    goals = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='goal_type',
        source='user_goals'
    )
    barriers = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name',
        source='profile.barriers'
    )
    habits = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name', 
        source='profile.habits'
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'phone_number', 'age', 'gender', 
            'country', 'height_feet', 'height_inches', 'current_weight', 
            'goal_weight', 'goals_completed', 'full_name', 'profile', 'profile_image', 'goals',
            'barriers', 'habits'
        )
        read_only_fields = ('id',)

    def to_representation(self, instance):
        # Ensure profile exists to avoid AttributeError in SlugRelatedFields
        if not hasattr(instance, 'profile'):
            UserProfile.objects.get_or_create(user=instance)
        return super().to_representation(instance)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'phone_number')

    def create(self, validated_data):
        user = User(**validated_data)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField() # Email or Phone
    password = serializers.CharField(write_only=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data

class FriendRequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = FriendRequest
        fields = '__all__'

class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = '__all__'

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class PrivacySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySettings
        fields = (
            'private_account', 'show_profile_in_search', 'show_activity_status',
            'share_workout_data', 'share_diet_data', 'share_progress_photos',
            'appear_on_leaderboards'
        )

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if user.password != value and not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct")
        return value

    def validate(self, attrs):
        if attrs.get('old_password') == attrs.get('new_password'):
            raise serializers.ValidationError({"new_password": "New password cannot be the same as old password"})
        return attrs

class BlockedUserSerializer(serializers.ModelSerializer):
    blocked_username = serializers.CharField(source='blocked.username', read_only=True)
    blocked_email = serializers.EmailField(source='blocked.email', read_only=True)
    blocked_full_name = serializers.CharField(source='blocked.profile.full_name', read_only=True)

    class Meta:
        model = BlockedUser
        fields = ('id', 'blocked', 'blocked_username', 'blocked_email', 'blocked_full_name', 'created_at')
        read_only_fields = ('id', 'created_at')

class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ('id', 'device_name', 'ip_address', 'created_at', 'last_active', 'is_active')
        read_only_fields = ('id', 'created_at', 'last_active')

class GoalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGoalSettings
        fields = '__all__'
        read_only_fields = ('id', 'user')

class DashboardDataSerializer(serializers.Serializer):
    daily_stats = DailyStatsSerializer()
    goal_settings = GoalSettingsSerializer()
    weekly_history = DailyStatsSerializer(many=True)
    weekly_macros = serializers.ListField(required=False)
    ai_metrics = serializers.DictField()
    weight_goal = WeightGoalSerializer()

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = '__all__'

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ('id', 'achievement', 'unlocked_at')
