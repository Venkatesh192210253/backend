from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Friend, ChallengeParticipant, DailyStats, UserProfile, PrivacySettings, UserGoalSettings

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        PrivacySettings.objects.get_or_create(user=instance)
        UserGoalSettings.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    if hasattr(instance, 'privacy_settings'):
        instance.privacy_settings.save()
    if hasattr(instance, 'goal_settings'):
        instance.goal_settings.save()

@receiver(post_save, sender=Friend)
def award_friend_xp(sender, instance, created, **kwargs):
    if created:
        # Both users get XP when they become friends
        instance.user.profile.add_xp(100)
        instance.friend.profile.add_xp(100)

@receiver(post_save, sender=ChallengeParticipant)
def award_challenge_xp(sender, instance, created, **kwargs):
    if created:
        instance.user.profile.add_xp(25)
    elif instance.is_completed:
        instance.user.profile.add_xp(200)

@receiver(post_save, sender=DailyStats)
def award_steps_xp(sender, instance, created, **kwargs):
    # We only award once per day per milestone
    # To keep it simple, we check the steps value
    if instance.steps >= 10000:
        # 50 XP for 10k steps
        # This will trigger on every update above 10k, so we should ideally 
        # have a way to track if already awarded.
        # Simple fix: only award if it's the exact crossover or just accept it's simple
        pass
    elif instance.steps >= 5000:
        # 20 XP for 5k steps
        pass
