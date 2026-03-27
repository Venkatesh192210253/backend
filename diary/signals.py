from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FoodEntry, WorkoutLog

@receiver(post_save, sender=FoodEntry)
def award_food_xp(sender, instance, created, **kwargs):
    if created:
        # Award 10 XP for logging food
        if hasattr(instance.user, 'profile'):
            instance.user.profile.add_xp(10)

@receiver(post_save, sender=WorkoutLog)
def award_workout_xp(sender, instance, created, **kwargs):
    if created:
        # Award 50 XP for logging a workout
        if hasattr(instance.user, 'profile'):
            instance.user.profile.add_xp(50)
            # Update workout count
            instance.user.profile.workouts_completed += 1
            instance.user.profile.save()
