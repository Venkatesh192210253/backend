from rest_framework import serializers
from .models import FoodEntry, WorkoutLog, ExerciseLogEntry, WorkoutTemplate, WorkoutTemplateExercise, UserWeeklySchedule, WeightLog, WeightGoal

class FoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodEntry
        fields = ['id', 'date', 'meal_type', 'food_name', 'quantity', 'calories', 'protein', 'carbs', 'fat', 'created_at']
        read_only_fields = ['id', 'created_at']

class ExerciseLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseLogEntry
        fields = ['id', 'name', 'sets_reps', 'weight', 'is_completed']

class WorkoutLogSerializer(serializers.ModelSerializer):
    exercises = ExerciseLogEntrySerializer(many=True)

    class Meta:
        model = WorkoutLog
        fields = ['id', 'date', 'workout_type', 'calories_burned', 'duration_minutes', 'exercises', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        exercises_data = validated_data.pop('exercises')
        workout = WorkoutLog.objects.create(**validated_data)
        for exercise_data in exercises_data:
            ExerciseLogEntry.objects.create(workout=workout, **exercise_data)
        return workout

class WorkoutTemplateExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutTemplateExercise
        fields = ['id', 'name', 'sets_reps', 'weight', 'order']

class WorkoutTemplateSerializer(serializers.ModelSerializer):
    exercises = WorkoutTemplateExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutTemplate
        fields = ['id', 'name', 'description', 'exercises', 'created_at']

class UserWeeklyScheduleSerializer(serializers.ModelSerializer):
    template = WorkoutTemplateSerializer(read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkoutTemplate.objects.all(), source='template', write_only=True, required=False, allow_null=True
    )
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = UserWeeklySchedule
        fields = ['id', 'day_of_week', 'day_name', 'template', 'template_id', 'is_rest_day']

class WeightLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightLog
        fields = ['id', 'date', 'weight', 'created_at']
        read_only_fields = ['id', 'created_at']

class WeightGoalSerializer(serializers.ModelSerializer):
    weeks_remaining = serializers.SerializerMethodField()

    class Meta:
        model = WeightGoal
        fields = ['id', 'start_weight', 'target_weight', 'weekly_goal_weight', 'weeks_remaining', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_weeks_remaining(self, obj):
        if not obj.weekly_goal_weight or obj.weekly_goal_weight <= 0:
            return 0
        
        # Get latest current weight from log
        latest_log = WeightLog.objects.filter(user=obj.user).order_by('-date', '-created_at').first()
        current = latest_log.weight if latest_log else obj.start_weight
        
        if not current:
            return 0
            
        diff = abs(obj.target_weight - current)
        return round(diff / obj.weekly_goal_weight, 1)
