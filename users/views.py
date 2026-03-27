import json
import requests
import os
from rest_framework import status, views, permissions
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import random
import string
import requests
from .serializers import ( UserSerializer, RegisterSerializer, LoginSerializer, GoalSerializer, GoalSettingsSerializer, DashboardDataSerializer, AchievementSerializer, UserAchievementSerializer, FriendRequestSerializer, ChallengeSerializer, GroupSerializer, PrivacySettingsSerializer, UserSessionSerializer, BlockedUserSerializer, DailyStatsSerializer, ChangePasswordSerializer, ForgotPasswordSerializer, PasswordResetSerializer )
from .models import (
    User, UserProfile, EmailOTP, PhoneOTP, Goal, Barrier, Habit, 
    DailyStats, FriendRequest, Friend, Group, GroupMember, GroupMessage, 
    Challenge, ChallengeParticipant, PrivacySettings, BlockedUser, 
    UserSession, UserGoalSettings, Achievement, UserAchievement
)
from notifications.utils import send_notification
try:
    from diary.models import WorkoutLog
except ImportError:
    WorkoutLog = None

User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'goals_completed': False,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            identifier = serializer.validated_data['identifier']
            password = serializer.validated_data['password']

            user_obj = User.objects.filter(email=identifier).first() or \
                       User.objects.filter(phone_number=identifier).first()

            if not user_obj:
                return Response({'error': 'No account found'}, status=status.HTTP_404_NOT_FOUND)

            user = authenticate(username=user_obj.email, password=password)
            if user:
                tokens = get_tokens_for_user(user)
                
                device_name = request.META.get('HTTP_USER_AGENT', 'Unknown Device')[:255]
                ip_address = request.META.get('REMOTE_ADDR')
                UserSession.objects.create(
                    user=user,
                    device_name=device_name,
                    ip_address=ip_address,
                    token_jti=tokens['access'][-255:] 
                )

                if not user.goals_completed and user.user_goals.exists():
                    user.goals_completed = True
                    user.save(update_fields=['goals_completed'])

                return Response({
                    'access': tokens['access'],
                    'refresh': tokens['refresh'],
                    'goals_completed': user.goals_completed,
                    'user': UserSerializer(user).data
                })
            return Response({'error': 'Invalid password'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyTokenView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Auto-correction: if user has goals but flag is False, fix it
        if not user.goals_completed and user.user_goals.exists():
            user.goals_completed = True
            user.save(update_fields=['goals_completed'])
            
        return Response({
            'valid': True,
            'goals_completed': user.goals_completed,
            'user': UserSerializer(user).data
        })

class ProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Auto-correction: if user has goals but flag is False, fix it
        if not user.goals_completed and user.user_goals.exists():
            user.goals_completed = True
            user.save(update_fields=['goals_completed'])
            
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        return self._update(request)

    def put(self, request):
        return self._update(request)

    def patch(self, request):
        return self._update(request)

    def _update(self, request):
        user = request.user
        data = request.data

        # Demographic fields on User model
        user.age = data.get('age', user.age)
        user.gender = data.get('gender', user.gender)
        user.country = data.get('country', user.country)
        user.username = data.get('username', user.username)
        # Support both 'height_feet' and 'height_ft'
        user.height_feet = data.get('height_feet', data.get('height_ft', user.height_feet))
        # Support both 'height_inches' and 'height_in'
        user.height_inches = data.get('height_inches', data.get('height_in', user.height_inches))
        user.height_cm = data.get('height_cm', user.height_cm)
        user.current_weight = data.get('current_weight', user.current_weight)
        user.goal_weight = data.get('goal_weight', user.goal_weight)
        user.weight_kg = data.get('weight_kg', user.weight_kg)
        user.activity_level = data.get('activity_level', user.activity_level)
        user.goals_completed = data.get('goals_completed', user.goals_completed)
        user.save()

        # Profile secondary fields
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.full_name = data.get('full_name', profile.full_name)
        profile.bio = data.get('bio', profile.bio)
        profile.fitness_level = data.get('fitness_level', profile.fitness_level)
        profile.weekly_goal = data.get('weekly_goal', profile.weekly_goal)
        profile.meal_planning_freq = data.get('meal_planning_freq', profile.meal_planning_freq)
        profile.weekly_meal_plans = data.get('weekly_meal_plans', profile.weekly_meal_plans)
        
        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']
        
        profile.save()

        # Handle Many-to-Many fields (Barriers and Habits)
        barriers_data = data.get('barriers')
        if barriers_data is not None:
            profile.barriers.clear()
            for barrier_name in barriers_data:
                if barrier_name:
                    barrier, _ = Barrier.objects.get_or_create(name=barrier_name)
                    profile.barriers.add(barrier)

        habits_data = data.get('habits')
        if habits_data is not None:
            profile.habits.clear()
            for habit_name in habits_data:
                if habit_name:
                    habit, _ = Habit.objects.get_or_create(name=habit_name)
                    profile.habits.add(habit)

        # Handle Goals (FK relationship)
        goals_data = data.get('goals')
        if goals_data is not None:
            user.user_goals.all().delete()
            for goal_type in goals_data:
                if goal_type:
                    Goal.objects.create(user=user, goal_type=goal_type)

        return Response(UserSerializer(user, context={'request': request}).data)

class GenerateOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate random OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Save to DB (Do not delete previous OTPs so they stay in history)
        PhoneOTP.objects.create(phone_number=phone_number, otp_code=otp)
        
        # Log to console (SMS placeholder)
        print(f"\n[SMS] OTP for {phone_number}: {otp}\n")
        
        # Real SMS sending via Fast2SMS
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "route": "q",
                "message": f"Your MyFitnessBuddy OTP is {otp}. Please enter this code to log in. Valid for 10 minutes.",
                "numbers": phone_number,
            }
            headers = {
                "authorization": settings.FAST2SMS_API_KEY,
                "Content-Type": "application/json"
            }
            # Note: Route 'q' (Quick SMS) is easier to use for custom messages
            sms_response = requests.post(url, json=payload, headers=headers)
            print(f"SMS Response: {sms_response.text}")
        except Exception as e:
            print(f"Error sending SMS: {e}")
        
        return Response({'message': 'OTP sent successfully'})

class VerifyOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')
        
        try:
            # Get the most recent valid OTP
            otp_obj = PhoneOTP.objects.filter(phone_number=phone_number, otp_code=otp, is_used=False).order_by('-created_at').first()
            if not otp_obj:
                return Response({'error': 'Invalid or already used OTP'}, status=status.HTTP_400_BAD_REQUEST)
                
            if otp_obj.is_expired():
                otp_obj.is_used = True
                otp_obj.save()
                return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Success - Mark OTP as used and login user
            otp_obj.is_used = True
            otp_obj.save()
            
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'email': f'{phone_number}@mobile.com', 'username': phone_number}
            )
            if created:
                UserProfile.objects.create(user=user)
            
            tokens = get_tokens_for_user(user)
            return Response({
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'goals_completed': user.goals_completed,
                'user': UserSerializer(user).data
            })
        except PhoneOTP.DoesNotExist:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate a 6-digit OTP
                otp = ''.join(random.choices(string.digits, k=6))

                # Save OTP to database (Keeping older history)
                EmailOTP.objects.create(email=email, otp_code=otp)

                # Send email
                subject = 'MyFitnessBuddy - Password Reset OTP'
                message = f'Your OTP for password reset is: {otp}. It will expire in 10 minutes.'
                from_email = settings.DEFAULT_FROM_EMAIL
                send_mail(subject, message, from_email, [email])

                return Response({'message': 'OTP sent to registered email'})
            except User.DoesNotExist:
                return Response({'error': 'Email not registered'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyResetOtpView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        try:
            otp_obj = EmailOTP.objects.filter(email=email, otp_code=otp, is_used=False).order_by('-created_at').first()
            if not otp_obj:
                return Response({'error': 'Invalid or already used OTP'}, status=status.HTTP_400_BAD_REQUEST)
                
            if otp_obj.is_expired():
                otp_obj.is_used = True
                otp_obj.save()
                return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)
                
            return Response({'message': 'OTP verified successfully'})
        except Exception:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']

            try:
                otp_obj = EmailOTP.objects.filter(email=email, otp_code=otp, is_used=False).order_by('-created_at').first()
                if not otp_obj:
                    return Response({'error': 'Invalid or already used OTP'}, status=status.HTTP_400_BAD_REQUEST)
                    
                if otp_obj.is_expired():
                    otp_obj.is_used = True
                    otp_obj.save()
                    return Response({'error': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)

                user = User.objects.get(email=email)
                # Save plain text password exactly as requested by bypassing hashing
                user.password = new_password
                user.save()

                # Mark OTP as used
                otp_obj.is_used = True
                otp_obj.save()

                return Response({'message': 'Password reset successful'})
            except User.DoesNotExist:
                return Response({'error': 'Invalid user'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CompleteGoalsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        goal_data = request.data.get('goals', [])
        
        # Save goal data
        user.user_goals.all().delete() # Clear existing
        for goal_type in goal_data:
            Goal.objects.create(user=user, goal_type=goal_type)
            
        # Set user.goals_completed = True
        user.goals_completed = True
        user.save()
        
        return Response({'message': 'Goals completed successfully', 'goals_completed': True})

class DailyStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        stats, created = DailyStats.objects.get_or_create(userid=request.user, date=today)
        
        # Activity streak is now handled automatically by the DailyStats post_save signal
        serializer = DailyStatsSerializer(stats)
        return Response(serializer.data)

    def post(self, request):
        date_str = request.data.get('date')
        if date_str:
            try:
                # Expecting YYYY-MM-DD
                from django.utils.dateparse import parse_date
                target_date = parse_date(date_str)
                if not target_date:
                    raise ValueError("Invalid date format")
            except Exception as e:
                return Response({"error": str(e)}, status=400)
        else:
            target_date = timezone.now().date()

        stats, created = DailyStats.objects.get_or_create(userid=request.user, date=target_date)

        # Activity streak is now handled automatically by the DailyStats post_save signal

        steps = request.data.get('steps')
        if steps is not None:
            stats.steps = int(steps)

        stats.save()

        calories_burned = request.data.get('calories_burned')
        if calories_burned is not None:
            stats.calories_burned = int(calories_burned)

        water_ml = request.data.get('water_ml')
        if water_ml is not None:
            stats.water_ml = int(water_ml)

        stats.save()
        serializer = DailyStatsSerializer(stats)
        return Response(serializer.data)

class DetailedStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        
        # 1. Streaks and Core Stats
        current_streak = profile.streak if profile else 0
        longest_streak = profile.longest_streak if profile else 0
        total_workouts = profile.workouts_completed if profile else 0
        
        # 2. Weight Loss
        weight_goal = getattr(user, 'weight_goal', None)
        if not weight_goal:
             from diary.models import WeightGoal
             weight_goal, _ = WeightGoal.objects.get_or_create(
                 user=user,
                 defaults={
                     'start_weight': user.current_weight or 75.0,
                     'target_weight': user.goal_weight or 70.0
                 }
             )
        
        weight_lost = round(max(0.0, (weight_goal.start_weight or 0.0) - (user.current_weight or 0.0)), 1)
        
        # 3. Monthly Breakdown (Last 6 months)
        monthly_breakdown = []
        now = timezone.now()
        for i in range(6):
            month_date = now - timezone.timedelta(days=30 * i)
            start_date = month_date.replace(day=1)
            next_month = (start_date + timezone.timedelta(days=32)).replace(day=1)
            
            month_stats = DailyStats.objects.filter(
                userid=user,
                date__range=[start_date, next_month - timezone.timedelta(days=1)]
            ).aggregate(
                total_steps=models.Sum('steps')
            )
            
            monthly_breakdown.append({
                "month": start_date.strftime("%B"),
                "workouts": 0, # Simplified
                "calories": 0  # Simplified
            })
            
        # 4. Personal Records
        max_steps = DailyStats.objects.filter(userid=user).order_by('-steps').first()
        
        records = []
        # max_calories logic removed as it's not in minimalist schema
        if False:
             pass
        if max_steps and max_steps.steps > 0:
            records.append({
                "title": "Most Steps in a Day",
                "value": f"{max_steps.steps:,}",
                "date": max_steps.date.strftime("%b %d, %Y"),
                "type": "steps"
            })

        # Calculate averages
        all_stats = DailyStats.objects.filter(userid=user)
        total_days = all_stats.count()
        total_steps = all_stats.aggregate(models.Sum('steps'))['steps__sum'] or 0
        avg_steps = int(total_steps / total_days) if total_days > 0 else 0

        data = {
            "currentStreak": current_streak,
            "longestStreak": longest_streak,
            "weightLost": weight_lost,
            "totalDaysTracked": total_days,
            "totalWorkouts": 0,
            "totalCaloriesBurned": 0,
            "avgDailyCalories": 0,
            "monthlyBreakdown": monthly_breakdown,
            "personalRecords": records
        }
        
        return Response(data)

class AchievementsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        from diary.models import WorkoutLog, FoodEntry, WaterIntake
        
        # 1. Initialize Default Achievements if they don't exist
        achievements_to_create = [
            {"title": "Early Bird", "description": "Complete a workout before 7 AM", "icon_name": "WbSunny", "color_hex": "#FFB300"},
            {"title": "Consistency King", "description": "Maintain a 30-day streak", "icon_name": "Whatshot", "color_hex": "#FF5722"},
            {"title": "Social Butterfly", "description": "Connect with 10 friends", "icon_name": "Groups", "color_hex": "#2196F3"},
            {"title": "Calorie Crusher", "description": "Burn 10,000 calories total", "icon_name": "LocalFireDepartment", "color_hex": "#F44336"},
            {"title": "Protein Power", "description": "Meet protein goal for 7 days", "icon_name": "FitnessCenter", "color_hex": "#4CAF50"},
            {"title": "Water Master", "description": "Drink 8 glasses daily for a week", "icon_name": "LocalDrink", "color_hex": "#03A9F4"},
            {"title": "Midnight Runner", "description": "Log a workout after 10 PM", "icon_name": "NightsStay", "color_hex": "#673AB7"},
            {"title": "Goal Getter", "description": "Reach your first weight goal", "icon_name": "EmojiEvents", "color_hex": "#FFD700"},
        ]
        
        for ach in achievements_to_create:
            Achievement.objects.get_or_create(title=ach["title"], defaults=ach)
            
        # 2. Check Conditions and Unlock
        # Early Bird
        if not UserAchievement.objects.filter(user=user, achievement__title="Early Bird").exists():
            if WorkoutLog.objects.filter(user=user, created_at__hour__lt=7).exists():
                ach = Achievement.objects.get(title="Early Bird")
                UserAchievement.objects.create(user=user, achievement=ach)

        # Consistency King
        if not UserAchievement.objects.filter(user=user, achievement__title="Consistency King").exists():
            if profile and profile.longest_streak >= 30:
                ach = Achievement.objects.get(title="Consistency King")
                UserAchievement.objects.create(user=user, achievement=ach)

        # Social Butterfly
        if not UserAchievement.objects.filter(user=user, achievement__title="Social Butterfly").exists():
            friend_count = Friend.objects.filter(models.Q(user=user) | models.Q(friend=user)).count()
            if friend_count >= 10:
                ach = Achievement.objects.get(title="Social Butterfly")
                UserAchievement.objects.create(user=user, achievement=ach)

        # Calorie Crusher (Simplified logic using steps as activity proxy)
        if not UserAchievement.objects.filter(user=user, achievement__title="Calorie Crusher").exists():
            total_steps = DailyStats.objects.filter(userid=user).aggregate(models.Sum('steps'))['steps__sum'] or 0
            if total_steps >= 100000:
                ach = Achievement.objects.get(title="Calorie Crusher")
                UserAchievement.objects.create(user=user, achievement=ach)

        # Protein Power (Simplified: check if food was logged)
        if not UserAchievement.objects.filter(user=user, achievement__title="Protein Power").exists():
            days_with_food = FoodEntry.objects.filter(user=user).values('date').distinct().count()
            if days_with_food >= 7:
                 ach = Achievement.objects.get(title="Protein Power")
                 UserAchievement.objects.create(user=user, achievement=ach)

        # Water Master
        if not UserAchievement.objects.filter(user=user, achievement__title="Water Master").exists():
             days_with_water = WaterIntake.objects.filter(user=user).values('date').distinct().count()
             if days_with_water >= 7:
                 ach = Achievement.objects.get(title="Water Master")
                 UserAchievement.objects.create(user=user, achievement=ach)

        # Midnight Runner
        if not UserAchievement.objects.filter(user=user, achievement__title="Midnight Runner").exists():
            if WorkoutLog.objects.filter(user=user, created_at__hour__gte=22).exists():
                ach = Achievement.objects.get(title="Midnight Runner")
                UserAchievement.objects.create(user=user, achievement=ach)

        # Goal Getter
        if not UserAchievement.objects.filter(user=user, achievement__title="Goal Getter").exists():
            if user.goals_completed:
                 ach = Achievement.objects.get(title="Goal Getter")
                 UserAchievement.objects.create(user=user, achievement=ach)
                 send_notification(
                     user_id=user.id,
                     title="Achievement Unlocked! 🏆",
                     message=f"You've earned the '{ach.title}' badge!",
                     type="AchievementUnlocked"
                 )

        # 3. Return all achievements with status
        all_achievements = Achievement.objects.all()
        unlocked_ids = UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
        
        result = []
        for ach in all_achievements:
            result.append({
                "id": ach.id,
                "title": ach.title,
                "description": ach.description,
                "iconName": ach.icon_name,
                "colorHex": ach.color_hex,
                "isUnlocked": ach.id in unlocked_ids,
                "unlockedAt": UserAchievement.objects.filter(user=user, achievement=ach).first().unlocked_at if ach.id in unlocked_ids else None
            })
            
        return Response(result)

def calculate_ai_metrics(user, target_date=None):
    if not target_date:
        target_date = timezone.now().date()
    
    from diary.models import FoodEntry, WorkoutLog, WaterIntake
    from django.db.models import Sum
    
    # Get stats for the day
    from users.models import DailyStats
    user_stats, _ = DailyStats.objects.get_or_create(userid=user, date=target_date)
    
    food_stats = FoodEntry.objects.filter(user=user, date=target_date).aggregate(
        calories=Sum('calories')
    )
    consumed = food_stats['calories'] or 0
    
    # Burned = Workouts + Steps (0.04 kcal per step as per app logic)
    workout_burned = WorkoutLog.objects.filter(user=user, date=target_date).aggregate(
        burned=Sum('calories_burned')
    )['burned'] or 0
    step_burned = user_stats.steps * 0.04
    total_burned = workout_burned + step_burned
    
    # 1. Energy Index Calculation (matches app behavior: 50 + net/10)
    net = total_burned - consumed
    energy_score = int(50 + (net / 10))
    energy_score = max(5, min(100, energy_score)) # Keep at least 5 to prevent app local recalculation if possible
    
    # 2. Work Readiness Calculation
    # Note: App applies Fatigue (-15) and Nutrition (-10) penalties locally.
    # To avoid double-penalization in the app, the backend should return the "Raw" score,
    # but for the Web Dashboard, we need the "Final" score.
    
    # Fresh Base
    readiness_score = 85
    
    # Hydration Impact (Only in backend/web)
    water = WaterIntake.objects.filter(user=user, date=target_date).aggregate(Sum('amount_ml'))['amount_ml__sum'] or 0
    if water < 1000:
        readiness_score -= 10
    elif water > 2500:
        readiness_score += 5
        
    # We'll calculate the final readiness score for the web here, 
    # but we should keep in mind the app will subtract more.
    # To fix parity, we'll return a version that assumes app-side logic will run.
    
    final_readiness = max(0, min(100, readiness_score))
    
    # Message logic based on the raw baseline (approximate)
    msg = "You're rested and ready for a great session!"
    if readiness_score < 70:
        msg = "Recovery active. Focus on mobility and proper fueling."

    return {
        "recovery_score": final_readiness,
        "energy_balance_score": energy_score,
        "injury_risk_score": 15,
        "current_suggestion": {
            "id": "1",
            "message": msg,
            "type": "RECOVERY"
        }
    }

class DashboardDataView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        
        # 1. Daily Stats
        stats, _ = DailyStats.objects.get_or_create(userid=request.user, date=today)
        
        # 2. Goal Settings
        goal_settings, _ = UserGoalSettings.objects.get_or_create(user=request.user)
        
        # 3. Weekly History (Last 7 days)
        last_week = today - timezone.timedelta(days=7)
        weekly_history = DailyStats.objects.filter(
            userid=request.user, 
            date__range=[last_week, today]
        ).order_by('date')
        
        # 3.5 Calculate Weekly Macros from FoodEntry
        from diary.models import FoodEntry
        weekly_macros = []
        
        # Calculate Monday of the current week
        start_of_week = today - timezone.timedelta(days=today.weekday())
        
        for i in range(7):
            target_date = start_of_week + timezone.timedelta(days=i)
            entries = FoodEntry.objects.filter(user=request.user, date=target_date)
            
            day_data = {
                "date": str(target_date),
                "day_name": target_date.strftime("%a").upper(),
                "protein": 0.0,
                "carbs": 0.0,
                "fats": 0.0,
                "meals": {
                    "breakfast": {"protein": 0.0, "carbs": 0.0, "fats": 0.0},
                    "lunch": {"protein": 0.0, "carbs": 0.0, "fats": 0.0},
                    "dinner": {"protein": 0.0, "carbs": 0.0, "fats": 0.0},
                    "snacks": {"protein": 0.0, "carbs": 0.0, "fats": 0.0},
                }
            }
            
            for entry in entries:
                day_data["protein"] += entry.protein
                day_data["carbs"] += entry.carbs
                day_data["fats"] += entry.fat
                
                meal = entry.meal_type.lower()
                if meal in day_data["meals"]:
                    day_data["meals"][meal]["protein"] += entry.protein
                    day_data["meals"][meal]["carbs"] += entry.carbs
                    day_data["meals"][meal]["fats"] += entry.fat
            
            weekly_macros.append(day_data)
            
        # 4. AI Metrics
        ai_metrics = calculate_ai_metrics(request.user, today)

        # 5. Weight Goal from diary app (with progress-optimized start weight)
        from diary.models import WeightLog, WeightGoal
        weight_goal, _ = WeightGoal.objects.get_or_create(
            user=request.user,
            defaults={'start_weight': request.user.current_weight, 'target_weight': request.user.goal_weight}
        )
        
        # Use first log as start weight ONLY if start_weight is not yet established
        if not weight_goal.start_weight or weight_goal.start_weight == 0:
            first_log = WeightLog.objects.filter(user=request.user).order_by('date', 'created_at').first()
            if first_log:
                weight_goal.start_weight = first_log.weight
                weight_goal.save()

        data = {
            "daily_stats": stats,
            "goal_settings": goal_settings,
            "weekly_history": weekly_history,
            "weekly_macros": weekly_macros,
            "ai_metrics": ai_metrics,
            "weight_goal": weight_goal
        }
        
        serializer = DashboardDataSerializer(data)
        return Response(serializer.data)

    def post(self, request):
        today = timezone.now().date()
        stats, created = DailyStats.objects.get_or_create(userid=request.user, date=today)
        
        serializer = DailyStatsSerializer(stats, data=request.data, partial=True)
        if serializer.is_valid():
            updated_stats = serializer.save()
            
            # Check for Step Goal Milestone
            try:
                goal_settings = getattr(request.user, 'goal_settings', None)
                if goal_settings:
                    new_steps = updated_stats.steps
                    goal = goal_settings.daily_step_goal
                    # Avoid sending multiple times if they were already above goal
                    # We can check request data to see if steps were updated in this call
                    if 'steps' in request.data or 'add_steps' in request.data or 'set_steps' in request.data:
                        if new_steps >= goal:
                            # We could also check old_steps < goal to be precise
                            send_notification(
                                user_id=request.user.id,
                                title="Achievement Unlocked! 🏅",
                                message=f"Congratulations! You've reached your daily goal of {goal} steps!",
                                type="GoalCompleted"
                            )
                        
                        # Trigger an AI Insight
                        send_notification(
                            user_id=request.user.id,
                            title="AI Recommendation 🤖",
                            message="Great job tracking! Based on your activity, I suggest increasing your protein intake today to help with muscle recovery.",
                            type="AIRecommendation"
                        )
            except Exception as e:
                print(f"Milestone notification error: {e}")
                
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_friend_request(request):
    receiver_id = request.data.get('receiver_id')
    receiver = get_object_or_404(User, id=receiver_id)

    if receiver == request.user:
        return Response({"error": "Cannot send request to yourself"}, status=400)

    if Friend.objects.filter(user=request.user, friend=receiver).exists():
        return Response({"error": "Already friends"}, status=400)

    friend_request, created = FriendRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver
    )

    if not created:
        if friend_request.status == 'pending':
            return Response({"error": "Request already sent"}, status=400)
        else:
            friend_request.status = 'pending'
            friend_request.save()

    # Send real-time notification
    send_notification(
        user_id=receiver.id,
        title="Friend Request",
        message=f"{request.user.username} sent you a friend request",
        type="FriendRequest"
    )

    return Response({"message": "Friend request sent"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_friend_request(request):
    request_id = request.data.get('request_id')
    friend_request = get_object_or_404(FriendRequest, id=request_id)

    if friend_request.receiver != request.user:
        return Response({"error": "Not authorized"}, status=403)

    if friend_request.status != 'pending':
        return Response({"error": "Request is not pending"}, status=400)

    with transaction.atomic():
        friend_request.status = 'accepted'
        friend_request.save()

        Friend.objects.get_or_create(user=friend_request.sender, friend=friend_request.receiver)
        Friend.objects.get_or_create(user=friend_request.receiver, friend=friend_request.sender)

    # Send notification to sender
    send_notification(
        user_id=friend_request.sender.id,
        title="Friend Request Accepted",
        message=f"{request.user.username} accepted your friend request",
        type="FriendRequest"
    )

    return Response({"message": "Friend request accepted"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_friend_request(request):
    request_id = request.data.get('request_id')
    friend_request = get_object_or_404(FriendRequest, id=request_id)

    if friend_request.receiver != request.user:
        return Response({"error": "Not authorized"}, status=403)

    friend_request.status = 'rejected'
    friend_request.save()

    # Optional: notify sender
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{str(friend_request.sender.id)}",
            {
                "type": "send_notification",
                "message": {
                    "event": "friend_request_rejected",
                    "data": {
                        "by_user_id": str(request.user.id),
                        "by_username": request.user.username,
                        "text": "Your friend request was rejected"
                    }
                }
            }
        )
    except Exception as e:
        print(f"WebSocket notification failed: {e}")

    return Response({"message": "Friend request rejected"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def remove_friend(request):
    friend_id = request.data.get('friend_id')
    
    # Delete friendship from both sides
    deleted_count1, _ = Friend.objects.filter(user=request.user, friend_id=friend_id).delete()
    deleted_count2, _ = Friend.objects.filter(user_id=friend_id, friend=request.user).delete()

    if deleted_count1 > 0 or deleted_count2 > 0:
        return Response({"message": "Friend removed successfully"})
    else:
        return Response({"error": "Friendship not found"}, status=404)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_friends(request):
    friends = Friend.objects.filter(user=request.user)
    # Return user details of the friend
    friends_data = []
    for f in friends:
        serializer = UserSerializer(f.friend, context={'request': request})
        friends_data.append(serializer.data)
    return Response({"friends": friends_data})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_friend_requests(request):
    received = FriendRequest.objects.filter(receiver=request.user, status='pending').select_related('sender', 'receiver')
    sent = FriendRequest.objects.filter(sender=request.user, status='pending').select_related('sender', 'receiver')

    return Response({
        "received_requests": FriendRequestSerializer(received, many=True).data,
        "sent_requests": FriendRequestSerializer(sent, many=True).data,
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_group(request):
    group_name = request.data.get('name') or request.data.get('group_name')
    description = request.data.get('description', '')
    goal = request.data.get('goal', '')
    is_public = request.data.get('is_public', True)
    invited_user_ids = request.data.get('invited_user_ids') or request.data.get('invited_users', [])

    group = Group.objects.create(
        name=group_name,
        description=description,
        goal=goal,
        is_public=is_public,
        created_by=request.user
    )

    # Add creator as admin
    GroupMember.objects.create(
        group=group,
        user=request.user,
        role='admin',
        status='joined',
        invited_by=request.user
    )

    # Invite users
    for user_id in invited_user_ids:
        try:
            user = User.objects.get(id=user_id)
            GroupMember.objects.get_or_create(
                group=group,
                user=user,
                defaults={
                    'role': 'member',
                    'status': 'invited',
                    'invited_by': request.user
                }
            )
            # Notify the user
            send_notification(
                user_id=user.id,
                title="Group Invitation",
                message=f"You have been invited to join '{group.name}' by {request.user.username}",
                type="Social"
            )
        except User.DoesNotExist:
            continue

    return Response({"message": "Group created successfully", "group_id": str(group.id)})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_my_groups(request):
    memberships = GroupMember.objects.filter(user=request.user)
    data = []
    for membership in memberships:
        data.append({
            "id": str(membership.group.id),
            "name": membership.group.name,
            "description": membership.group.description,
            "goal": membership.group.goal,
            "is_public": membership.group.is_public,
            "role": membership.role,
            "status": membership.status,
            "unread_count": membership.unread_count,
            "member_count": membership.group.members.count(),
            "active_challenge": membership.group.active_challenge
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if user is a member
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        return Response({"error": "You are not a member of this group"}, status=403)
        
    # Calculate group stats dynamically
    members = GroupMember.objects.filter(group=group)
    total_workouts = 0
    total_streak = 0
    total_calories_burned = 0
    
    from django.db.models import Sum
    from django.utils import timezone
    
    members_data = []
    for m in members:
        if hasattr(m.user, 'profile'):
            total_workouts += m.user.profile.workouts_completed
            total_streak += m.user.profile.streak
            # Goal calculation logic (simplified for minimalist schema)
            cals = 0
            total_calories_burned += cals
            
        full_name = m.user.profile.full_name if hasattr(m.user, 'profile') and m.user.profile.full_name else m.user.username
        
        members_data.append({
            "id": str(m.user.id),
            "name": full_name,
            "username": m.user.username,
            "initials": full_name[:1].upper(),
            "points": m.user.profile.xp if hasattr(m.user, 'profile') else 0,
            "rank": 0, # Top members sorting handled on frontend or in a leaderboards view
            "is_you": m.user == request.user
        })
        
    member_count = members.count()
    avg_streak = int(total_streak / member_count) if member_count > 0 else 0
    
    progress = 0.0
    challenge_end_days = 0
    if group.active_challenge:
        active = Challenge.objects.filter(group=group, name=group.active_challenge).first()
        if active:
            days_left = (active.created_at + timezone.timedelta(days=active.duration_days) - timezone.now()).days
            challenge_end_days = max(0, days_left)
            
            participants = ChallengeParticipant.objects.filter(challenge=active)
            current_total = 0
            for p in participants:
                try:
                    current_total += float(p.current_value)
                except ValueError:
                    pass
            try:
                target = float(active.target_value) if active.target_value else 1.0
                if target > 0:
                    progress = min(1.0, current_total / target)
            except ValueError:
                progress = 0.0
                
    data = {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "goal": group.goal,
        "is_public": group.is_public,
        "member_count": member_count,
        "active_challenge": group.active_challenge,
        "challenge_end_days": challenge_end_days,
        "progress": progress,
        "total_workouts": total_workouts,
        "total_calories": str(int(total_calories_burned)),
        "avg_streak": avg_streak,
        "members": members_data
    }
    return Response(data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_challenge(request):
    print(f"DEBUG: create_challenge called by {request.user.username}")
    print(f"DEBUG: Data: {request.data}")
    
    group_id = request.data.get('group_id')
    challenge_name = request.data.get('name')
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is admin
    is_admin = GroupMember.objects.filter(group=group, user=request.user, role='admin').exists()
    print(f"DEBUG: User is admin: {is_admin}")
    
    if not is_admin:
        return Response({"error": "Only admins can create challenges"}, status=403)
        
    # Parse numeric fields safely
    try:
        duration_val = request.data.get('duration', '7')
        duration_days = int(duration_val) if duration_val and duration_val.strip() else 7
        
        points_val = request.data.get('points', '500')
        points_reward = int(points_val) if points_val and points_val.strip() else 500
    except (ValueError, TypeError):
        duration_days = 7
        points_reward = 500

    try:
        challenge = Challenge.objects.create(
            group=group,
            name=challenge_name,
            description=request.data.get('description', ''),
            type=request.data.get('type', 'Steps'),
            duration_days=duration_days,
            target_value=request.data.get('target', ''),
            points_reward=points_reward
        )
        
        group.active_challenge = challenge_name
        group.save()
        
        # Activity-based streak maintenance
        from django.utils import timezone
        today = timezone.now().date()
        stats, created = DailyStats.objects.get_or_create(userid=request.user, date=today)
        
        if created:
            profile = getattr(request.user, 'profile', None)
            if profile:
                yesterday = today - timezone.timedelta(days=1)
                yesterday_stats = DailyStats.objects.filter(userid=request.user, date=yesterday).first()
                if yesterday_stats:
                    profile.streak += 1
                else:
                    profile.streak = 1
                profile.save()

        # Notify all group members about the new challenge
        members = GroupMember.objects.filter(group=group, status='joined').exclude(user=request.user)
        for member in members:
            send_notification(
                user_id=member.user.id,
                title="New Group Challenge!",
                message=f"A new challenge '{challenge_name}' has been created in {group.name}",
                type="FriendChallenge"
            )
                
        return Response({"message": "Challenge created successfully", "challenge_id": str(challenge.id)})
    except Exception as e:
        print(f"Error creating challenge: {str(e)}")
        return Response({"error": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_group_challenges(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    challenges = Challenge.objects.filter(group=group).order_by('-created_at')
    serializer = ChallengeSerializer(challenges, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def invite_to_group(request):
    group_id = request.data.get('group_id')
    user_id = request.data.get('user_id')
    
    group = get_object_or_404(Group, id=group_id)
    user_to_invite = get_object_or_404(User, id=user_id)
    
    # Check if request.user is admin
    if not GroupMember.objects.filter(group=group, user=request.user, role='admin').exists():
        return Response({"error": "Only admins can invite members"}, status=403)
        
    member, created = GroupMember.objects.get_or_create(
        group=group,
        user=user_to_invite,
        defaults={'role': 'member', 'status': 'joined', 'invited_by': request.user}
    )
    
    if not created and member.status in ['rejected', 'invited']:
        member.status = 'joined'
        member.invited_by = request.user
        member.save()
        
    # Send real-time notification to the invited user
    send_notification(
        user_id=user_to_invite.id,
        title="Group Invitation",
        message=f"{request.user.username} invited you to join '{group.name}'",
        type="FriendRequest"
    )
        
    return Response({"message": "User invited successfully"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_group_invite(request):
    group_id = request.data.get('group_id')
    membership = get_object_or_404(
        GroupMember,
        group_id=group_id,
        user=request.user,
        status='invited'
    )
    membership.status = 'joined'
    membership.save()
    
    # Optional: Send notification to the group that user joined
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"group_{group_id}",
            {
                "type": "send_notification",
                "message": {
                    "event": "group_member_joined",
                    "data": {
                        "user_id": str(request.user.id),
                        "username": request.user.username,
                        "text": f"{request.user.username} joined the group"
                    }
                }
            }
        )
        
    return Response({"message": "Joined group successfully"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_group_invite(request):
    group_id = request.data.get('group_id')
    membership = get_object_or_404(
        GroupMember,
        group_id=group_id,
        user=request.user,
        status='invited'
    )
    membership.status = 'rejected'
    membership.save()
    return Response({"message": "Group invite rejected"})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_group_messages(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Ensure user is a member
    membership = GroupMember.objects.filter(group=group, user=request.user, status='joined').first()
    if not membership:
        return Response({"error": "You are not a member of this group"}, status=403)
        
    # Reset unread_count since user is viewing messages
    if membership.unread_count > 0:
        membership.unread_count = 0
        membership.save()
        
    messages = GroupMessage.objects.filter(group=group).order_by('created_at')
    
    data = []
    for msg in messages:
        data.append({
            "id": str(msg.id),
            "sender_id": str(msg.sender.id),
            "sender_name": msg.sender_name,
            "message": msg.message,
            "created_at": msg.created_at.isoformat()
        })
        
    return Response(data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_group_message(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Ensure user is a member
    if not GroupMember.objects.filter(group=group, user=request.user, status='joined').exists():
        return Response({"error": "You are not a member of this group"}, status=403)
        
    message_text = request.data.get('message')
    if not message_text:
        return Response({"error": "Message cannot be empty"}, status=400)
        
    msg = GroupMessage.objects.create(
        group=group,
        sender=request.user,
        message=message_text
    )
    
    # Activity-based streak maintenance
    from django.utils import timezone
    today = timezone.now().date()
    stats, created = DailyStats.objects.get_or_create(userid=request.user, date=today)
    
    if created:
        profile = getattr(request.user, 'profile', None)
        if profile:
            yesterday = today - timezone.timedelta(days=1)
            yesterday_stats = DailyStats.objects.filter(userid=request.user, date=yesterday).first()
            if yesterday_stats:
                profile.streak += 1
            else:
                profile.streak = 1
            profile.save()
            
    # Increment unread_count for all other joined members
    from django.db.models import F
    GroupMember.objects.filter(group=group, status='joined').exclude(user=request.user).update(unread_count=F('unread_count') + 1)
    
    # Notify all other joined members via new notification system
    members = GroupMember.objects.filter(group=group, status='joined').exclude(user=request.user)
    for m in members:
        send_notification(
            user_id=m.user.id,
            title=f"New Message in {group.name}",
            message=f"{msg.sender_name}: {msg.message[:50]}...",
            type="Social"
        )
        
    return Response({"message": "Message sent successfully", "message_id": str(msg.id)})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    query = request.query_params.get('q', '')
    if len(query) < 3:
        return Response([])
    
    query_filters = (
        models.Q(username__icontains=query) | 
        models.Q(email__icontains=query) |
        models.Q(profile__full_name__icontains=query)
    )
    
    try:
        import uuid
        parsed_uuid = uuid.UUID(query)
        query_filters |= models.Q(id=parsed_uuid)
    except ValueError:
        pass
        
    users = User.objects.filter(query_filters).exclude(id=request.user.id)[:10]
    
    serializer = UserSerializer(users, many=True, context={'request': request})
    return Response(serializer.data)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if user is the creator or admin
    if group.created_by != request.user and not GroupMember.objects.filter(group=group, user=request.user, role='admin').exists():
        return Response({"error": "You do not have permission to delete this group"}, status=403)
    
    group.delete()
    return Response({"message": "Group deleted successfully"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def delete_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    # Check if user is admin in the group
    if not GroupMember.objects.filter(group=challenge.group, user=request.user, role='admin').exists():
        return Response({"error": "Only admins can delete challenges"}, status=403)
    
    challenge.delete()
    return Response({"message": "Challenge deleted successfully"})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    # Check if user is a member of the group
    if not GroupMember.objects.filter(group=challenge.group, user=request.user).exists():
        return Response({"error": "You must be a member of the group to join the challenge"}, status=403)
    
    participant, created = ChallengeParticipant.objects.get_or_create(
        challenge=challenge,
        user=request.user
    )
    if not created:
        return Response({"message": "You have already joined this challenge"})
        
    # Activity-based streak maintenance
    from django.utils import timezone
    today = timezone.now().date()
    stats, stats_created = DailyStats.objects.get_or_create(userid=request.user, date=today)
    
    if stats_created:
        profile = getattr(request.user, 'profile', None)
        if profile:
            yesterday = today - timezone.timedelta(days=1)
            yesterday_stats = DailyStats.objects.filter(userid=request.user, date=yesterday).first()
            if yesterday_stats:
                profile.streak += 1
            else:
                profile.streak = 1
            profile.save()
    
    # Send confirmation notification
    send_notification(
        user_id=request.user.id,
        title="Challenge Joined!",
        message=f"You have joined the challenge '{challenge.name}'",
        type="Milestone"
    )
    
    return Response({"message": "Joined challenge successfully"})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_challenge_participants(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    participants = ChallengeParticipant.objects.filter(challenge=challenge)
    
    data = []
    for p in participants:
        data.append({
            "id": str(p.user.id),
            "name": p.user.profile.full_name or p.user.username,
            "username": p.user.username,
            "initials": (p.user.profile.full_name or p.user.username)[:1].upper(),
            "progress_value": p.current_value,
            "is_completed": p.is_completed,
            "joined_at": p.joined_at
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_suggested_friends(request):
    # Users who are not the current user and not already friends
    friend_ids = Friend.objects.filter(user=request.user).values_list('friend_id', flat=True)
    suggested_users = User.objects.exclude(id__in=list(friend_ids) + [request.user.id]).order_by('?')[:5]
    
    serializer = UserSerializer(suggested_users, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def compare_stats(request, friend_id):
    friend = get_object_or_404(User, id=friend_id)
    today = timezone.now().date()
    # Import locally to avoid circular imports if any
    from diary.models import WorkoutLog
    from users.models import UserGoalSettings
    
    my_stats, _ = DailyStats.objects.get_or_create(userid=request.user, date=today)
    friend_stats, _ = DailyStats.objects.get_or_create(userid=friend, date=today)
    
    my_profile = getattr(request.user, 'profile', None)
    friend_profile = getattr(friend, 'profile', None)
    
    def get_task_status(user, stats):
        goal_settings, _ = UserGoalSettings.objects.get_or_create(user=user)
        return [
            {
                "name": "Morning Run",
                "completed": WorkoutLog.objects.filter(user=user, date=today, workout_type__icontains='Run').exists()
            },
            {
                "name": "10k Steps",
                "completed": stats.steps >= 10000
            }
        ]

    my_workouts_today = WorkoutLog.objects.filter(user=request.user, date=today).count()
    friend_workouts_today = WorkoutLog.objects.filter(user=friend, date=today).count()
    my_cals_burned = sum(WorkoutLog.objects.filter(user=request.user, date=today).values_list('calories_burned', flat=True))
    friend_cals_burned = sum(WorkoutLog.objects.filter(user=friend, date=today).values_list('calories_burned', flat=True))

    data = {
        "me": {
            "steps": my_stats.steps,
            "workouts": my_workouts_today,
            "streak": my_profile.streak if my_profile else 0,
            "xp": my_profile.xp if my_profile else 0,
            "level": my_profile.level if my_profile else 1,
            "calories_burned": my_cals_burned,
            "tasks": get_task_status(request.user, my_stats)
        },
        "friend": {
            "steps": friend_stats.steps,
            "workouts": friend_workouts_today,
            "streak": friend_profile.streak if friend_profile else 0,
            "xp": friend_profile.xp if friend_profile else 0,
            "level": friend_profile.level if friend_profile else 1,
            "calories_burned": friend_cals_burned,
            "tasks": get_task_status(friend, friend_stats)
        }
    }
    return Response(data)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def chat_with_ai(request):
    user_message = request.data.get('message', '').strip()
    
    if not user_message:
        return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        return Response({"error": "GROQ_API_KEY environment variable not set"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    system_prompt = (
        "You are an AI assistant for a fitness and social app.\n"
        "Your job is to help users understand how to use the app and provide fitness/nutritional advice.\n"
        "The app has features like:\n"
        "- user profiles\n"
        "- friend requests\n"
        "- group challenges\n"
        "- fitness goals\n"
        "- AI workout guidance\n"
        "- leaderboard rankings\n"
        "- daily goal tracking\n\n"
        "You are also permitted to answer questions about food items, calories, macronutrients (protein, carbs, fats), and general fitness/nutritional information.\n"
        "If a user asks something completely unrelated to fitness, nutrition, or the app, politely respond:\n"
        "\"I can help only with questions related to this app, fitness, and nutrition.\""
    )
    
    # Retrieve existing conversation history from the request or session if provided,
    # otherwise default to just the system prompt and current user message.
    messages = request.data.get('history', [])
    
    # Prepend the system prompt if not present
    if not any(msg.get('role') == 'system' for msg in messages):
        messages.insert(0, {"role": "system", "content": system_prompt})
        
    image_base64 = request.data.get('image_base64')
    
    # Append the current user message
    if image_base64:
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        })
        model_name = "llama-3.2-90b-vision-preview"
    else:
        messages.append({
            "role": "user",
            "content": user_message
        })
        model_name = "llama-3.3-70b-versatile"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {groq_api_key}"
    }

    payload = {
        "model": model_name,
        "messages": messages
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        
        # If Groq returns an error, let's catch the exact text instead of throwing a generic exception
        if not response.ok:
            error_data = response.text
            print("Groq API Error:", error_data)
            return Response(
                {"error": f"Groq API Error: {response.status_code}", "details": error_data}, 
                status=status.HTTP_502_BAD_GATEWAY
            )
            
        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "I am having trouble processing that request.")
        return Response({"reply": reply}, status=status.HTTP_200_OK)
        
    except requests.exceptions.RequestException as e:
        print("RequestException when calling Groq:", str(e))
        return Response({"error": f"Error connecting to AI service: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

class PrivacySettingsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings, _ = PrivacySettings.objects.get_or_create(user=request.user)
        serializer = PrivacySettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        settings, _ = PrivacySettings.objects.get_or_create(user=request.user)
        serializer = PrivacySettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.password = serializer.validated_data['new_password']
            user.save()
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteAccountView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get('password')
        user = request.user
        
        if user.password != password and not user.check_password(password):
            return Response({"error": "Incorrect password."}, status=status.HTTP_400_BAD_REQUEST)
            
        user.delete()
        return Response({"message": "Account deleted successfully."}, status=status.HTTP_200_OK)

class DownloadDataView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        profile_data = UserSerializer(user).data
        stats_data = DailyStatsSerializer(DailyStats.objects.filter(userid=user), many=True).data
        settings_data = PrivacySettingsSerializer(PrivacySettings.objects.get(user=user)).data
        
        data = {
            "profile": profile_data,
            "settings": settings_data,
            "daily_stats": stats_data
        }
        return Response(data, status=status.HTTP_200_OK)

class BlockUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        blocked_user = get_object_or_404(User, id=user_id)
        
        if blocked_user == request.user:
            return Response({"error": "Cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
        BlockedUser.objects.get_or_create(blocker=request.user, blocked=blocked_user)
        # Optionally remove any existing friendship
        Friend.objects.filter(user=request.user, friend=blocked_user).delete()
        Friend.objects.filter(user=blocked_user, friend=request.user).delete()
        
        return Response({"message": f"Successfully blocked {blocked_user.username}."}, status=status.HTTP_200_OK)

class UnblockUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        BlockedUser.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response({"message": "Successfully unblocked user."}, status=status.HTTP_200_OK)

class BlockedUsersListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        blocked = BlockedUser.objects.filter(blocker=request.user)
        serializer = BlockedUserSerializer(blocked, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ListSessionsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = UserSession.objects.filter(user=request.user, is_active=True).order_by('-last_active')
        serializer = UserSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RevokeSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session_id = request.data.get('session_id')
        session = get_object_or_404(UserSession, id=session_id, user=request.user)
        session.is_active = False
        session.save()
        return Response({"message": "Session revoked successfully."}, status=status.HTTP_200_OK)

class GoalSettingsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings_obj, created = UserGoalSettings.objects.get_or_create(user=request.user)
        serializer = GoalSettingsSerializer(settings_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        settings_obj, created = UserGoalSettings.objects.get_or_create(user=request.user)
        serializer = GoalSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

# Load dataset for AI Coach
AI_DATASET = []
dataset_path = os.path.join(settings.BASE_DIR, 'ai_trained_model', 'dataset.json')
try:
    if os.path.exists(dataset_path):
        with open(dataset_path, 'r') as f:
            AI_DATASET = json.load(f)
except Exception as e:
    print(f"Error loading AI dataset: {e}")

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def trained_ai_ask(request):
    question = request.data.get('question', '').lower()
    
    if not AI_DATASET:
        return Response({"error": "Dataset not loaded"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # Simple keyword similarity matching
    best_match = None
    max_score = 0
    
    question_words = set(question.split())
    
    for item in AI_DATASET:
        item_q = item.get('question', '').lower()
        item_words = set(item_q.replace('?', '').split())
        score = len(question_words.intersection(item_words))
        
        if score > max_score:
            max_score = score
            best_match = item
            
    if best_match and max_score > 0:
        return Response({
            "answer": best_match['answer'],
            "category": best_match['category']
        })
    else:
        # Better fallback message as requested by user
        return Response({
            "answer": "To reach your goals, focus on a balanced diet of lean proteins and vegetables, drink at least 2L of water daily, and aim for 30 minutes of physical activity. Try logging your meals in the Food Diary for personalized tracking!",
            "category": "general"
        })
