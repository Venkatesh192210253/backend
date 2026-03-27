from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    
    # Demographic fields
    gender = models.CharField(max_length=10, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    height_feet = models.IntegerField(null=True, blank=True)
    height_inches = models.IntegerField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    current_weight = models.FloatField(null=True, blank=True)
    goal_weight = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    activity_level = models.CharField(max_length=50, null=True, blank=True)
    goals_completed = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

from django.utils import timezone

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_goals')
    goal_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.goal_type}"

class Barrier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name

class Habit(models.Model):
    name = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    fitness_level = models.CharField(max_length=50, null=True, blank=True)
    
    # Detailed tracking/preferences can stay here or be moved if needed
    meal_planning_freq = models.CharField(max_length=50, null=True, blank=True)
    weekly_meal_plans = models.CharField(max_length=50, null=True, blank=True)
    weekly_goal = models.CharField(max_length=100, null=True, blank=True)
    
    streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    workouts_completed = models.IntegerField(default=0)
    xp = models.IntegerField(default=0)
    
    goals = models.ManyToManyField(Goal, blank=True)
    barriers = models.ManyToManyField(Barrier, blank=True)
    habits = models.ManyToManyField(Habit, blank=True)

    def add_xp(self, amount):
        self.xp += amount
        # Level up logic: Each level requires 1000 XP
        new_level = (self.xp // 1000) + 1
        if new_level != self.level:
            self.level = new_level
            # Potential for level up notification event here
        self.save()

    def __str__(self):
        return f"{self.user.username}'s profile (Level {self.level})"

class EmailOTP(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self, minutes=10):
        from django.utils import timezone
        return timezone.now() > self.created_at + timezone.timedelta(minutes=minutes)

    def __str__(self):
        return f"OTP for {self.email}"

class PhoneOTP(models.Model):
    phone_number = models.CharField(max_length=15)
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self, minutes=10):
        from django.utils import timezone
        return timezone.now() > self.created_at + timezone.timedelta(minutes=minutes)

    def __str__(self):
        return f"OTP for {self.phone_number}"

class DailyStats(models.Model):
    userid = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_stats', db_column='userid')
    date = models.DateField(default=timezone.now)
    steps = models.IntegerField(default=0)

    class Meta:
        db_table = 'daily_steps'
        unique_together = ('userid', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_requests', on_delete=models.CASCADE)
    sender_name = models.CharField(max_length=255, blank=True)
    receiver_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'receiver')
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        if self.sender == self.receiver:
            raise models.ValidationError("Cannot send request to yourself")
        if Friend.objects.filter(user=self.sender, friend=self.receiver).exists():
            raise models.ValidationError("Already friends")

    def save(self, *args, **kwargs):
        if not self.sender_name and self.sender_id:
            self.sender_name = self.sender.profile.full_name or self.sender.username
        if not self.receiver_name and self.receiver_id:
            self.receiver_name = self.receiver.profile.full_name or self.receiver.username
        super().save(*args, **kwargs)

class Friend(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friends', on_delete=models.CASCADE)
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_of', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'friend')

class Challenge(models.Model):
    group = models.ForeignKey('Group', related_name='challenges', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=50, default='Steps')
    duration_days = models.IntegerField(default=7)
    target_value = models.CharField(max_length=255, null=True, blank=True)
    points_reward = models.IntegerField(default=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.group.name} - {self.name}"

class ChallengeParticipant(models.Model):
    challenge = models.ForeignKey(Challenge, related_name='participants', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    current_value = models.CharField(max_length=255, default='0')
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('challenge', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.challenge.name}"

class Group(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    goal = models.CharField(max_length=255, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    active_challenge = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class GroupMember(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    STATUS_CHOICES = (
        ('invited', 'Invited'),
        ('joined', 'Joined'),
        ('rejected', 'Rejected'),
    )

    group = models.ForeignKey(Group, related_name='members', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='joined')
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='group_invites', on_delete=models.CASCADE, null=True, blank=True)
    unread_count = models.IntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

class Achievement(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon_name = models.CharField(max_length=50) # e.g., "WbSunny"
    color_hex = models.CharField(max_length=7, default="#2196F3")
    category = models.CharField(max_length=50, default="General")
    
    def __str__(self):
        return self.title

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')

    def __str__(self):
        return f"{self.user.username} - {self.achievement.title}"


class GroupMessage(models.Model):
    group = models.ForeignKey(Group, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='group_messages', on_delete=models.CASCADE)
    sender_name = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.sender_name and self.sender_id:
            self.sender_name = self.sender.profile.full_name or self.sender.username
        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.message[:30]} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"

class PrivacySettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='privacy_settings')
    
    # Account Privacy
    private_account = models.BooleanField(default=False)
    show_profile_in_search = models.BooleanField(default=True)
    show_activity_status = models.BooleanField(default=True)
    
    # Data Sharing
    share_workout_data = models.BooleanField(default=True)
    share_diet_data = models.BooleanField(default=True)
    share_progress_photos = models.BooleanField(default=False)
    appear_on_leaderboards = models.BooleanField(default=True)
    
    # Security
    # two_factor_enabled = models.BooleanField(default=False) # Removed as per user request

    def __str__(self):
        return f"{self.user.username}'s Privacy Settings"

class BlockedUser(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='blocking', on_delete=models.CASCADE)
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='blocked_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sessions', on_delete=models.CASCADE)
    device_name = models.CharField(max_length=255, default="Unknown Device")
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    token_jti = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} on {self.device_name}"

class UserGoalSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goal_settings')
    primary_goal = models.CharField(max_length=50, default="BuildMuscle")
    current_weight = models.FloatField(default=72.0)
    target_weight = models.FloatField(default=75.0)
    weekly_goal_weight = models.FloatField(default=0.5)
    current_body_fat = models.FloatField(default=18.0)
    target_body_fat = models.FloatField(default=15.0)
    muscle_mass_goal = models.FloatField(default=35.0)
    workouts_per_week = models.IntegerField(default=4)
    daily_step_goal = models.IntegerField(default=10000)
    weekly_calorie_burn_goal = models.IntegerField(default=2000)
    daily_calorie_target = models.IntegerField(default=2500)
    protein_g = models.IntegerField(default=160)
    carbs_g = models.IntegerField(default=250)
    fats_g = models.IntegerField(default=70)
    is_adaptive_mode_enabled = models.BooleanField(default=False)
    quiet_hours_from = models.CharField(max_length=5, default="22:00")
    quiet_hours_to = models.CharField(max_length=5, default="07:00")

    def __str__(self):
        return f"{self.user.username}'s Goal Settings"

@receiver(post_save, sender=UserGoalSettings)
def sync_user_goal_fields(sender, instance, created, **kwargs):
    """
    Synchronizes weight goals across User, UserGoalSettings, and WeightGoal models 
     to ensure app and web parity.
    """
    user = instance.user
    
    # 1. Sync Primary User Model
    user_updated = False
    if user.goal_weight != instance.target_weight:
        user.goal_weight = instance.target_weight
        user_updated = True
    if user.current_weight != instance.current_weight:
        user.current_weight = instance.current_weight
        user_updated = True
    if user_updated:
        user.save(update_fields=['goal_weight', 'current_weight'])

    # 2. Sync Diary WeightGoal Model (Used by mobile app for some views)
    try:
        from diary.models import WeightGoal
        weight_goal, created = WeightGoal.objects.get_or_create(
            user=user,
            defaults={
                'start_weight': instance.current_weight,
                'target_weight': instance.target_weight,
                'weekly_goal_weight': instance.weekly_goal_weight or 0.5
            }
        )
        
        if not created:
            wg_updated = False
            if weight_goal.target_weight != instance.target_weight:
                weight_goal.target_weight = instance.target_weight
                wg_updated = True
            if weight_goal.weekly_goal_weight != instance.weekly_goal_weight:
                weight_goal.weekly_goal_weight = instance.weekly_goal_weight
                wg_updated = True
                
            if wg_updated:
                weight_goal.save()
    except ImportError:
        pass

# --- SIGNAL REGISTRATION ---
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=DailyStats)
def update_streak_on_activity(sender, instance, created, **kwargs):
    """
    Automatically increments or resets user streak when a DailyStats record 
    is created (first activity of the day).
    """
    if created:
        user = instance.userid
        profile = getattr(user, 'profile', None)
        if profile:
            today = instance.date
            yesterday = today - timezone.timedelta(days=1)
            
            # Check if there was activity yesterday
            yesterday_exists = DailyStats.objects.filter(userid=user, date=yesterday).exists()
            
            if yesterday_exists:
                profile.streak += 1
            else:
                # If they missed a day, restart at 1
                profile.streak = 1
            
            if profile.streak > profile.longest_streak:
                profile.longest_streak = profile.streak
            
            profile.save()
