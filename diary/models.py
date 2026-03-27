from django.db import models
from django.conf import settings
from django.utils import timezone

class FoodEntry(models.Model):
    # ... (existing fields)
    MEAL_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snacks', 'Snacks'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='food_entries')
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES)
    food_name = models.CharField(max_length=255)
    quantity = models.CharField(max_length=100)
    calories = models.IntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.food_name} ({self.meal_type}) on {self.date}"

class WorkoutLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_logs')
    date = models.DateField(default=timezone.now)
    workout_type = models.CharField(max_length=100)
    calories_burned = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.workout_type} on {self.date} by {self.user.username}"

class ExerciseLogEntry(models.Model):
    workout = models.ForeignKey(WorkoutLog, on_delete=models.CASCADE, related_name='exercises')
    name = models.CharField(max_length=255)
    sets_reps = models.CharField(max_length=100)
    weight = models.CharField(max_length=100)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} in {self.workout}"

class WorkoutTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class WorkoutTemplateExercise(models.Model):
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='exercises')
    name = models.CharField(max_length=255)
    sets_reps = models.CharField(max_length=100)
    weight = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} in {self.template.name}"

class UserWeeklySchedule(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weekly_schedules')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    is_rest_day = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'day_of_week')
        ordering = ['day_of_week']

    def __str__(self):
        return f"{self.user.username} - {self.get_day_of_week_display()}"

class WeightLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weight_logs')
    date = models.DateField(default=timezone.now)
    weight = models.FloatField()  # in kg
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.user.username} - {self.weight}kg on {self.date}"

class WeightGoal(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weight_goal')
    start_weight = models.FloatField(null=True, blank=True)
    target_weight = models.FloatField(null=True, blank=True)
    weekly_goal_weight = models.FloatField(default=0.5)  # in kg/week
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.start_weight}kg → {self.target_weight}kg"

class WaterIntake(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='water_intakes')
    date = models.DateField(default=timezone.now)
    amount_ml = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.amount_ml}ml on {self.date}"
