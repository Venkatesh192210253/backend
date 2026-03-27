from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import FoodEntry, WorkoutLog, ExerciseLogEntry, WorkoutTemplate, UserWeeklySchedule
from .serializers import (
    FoodEntrySerializer, WorkoutLogSerializer, 
    WorkoutTemplateSerializer, UserWeeklyScheduleSerializer
)
from django.utils import timezone
from .models import FoodEntry, WorkoutLog, ExerciseLogEntry, WorkoutTemplate, WorkoutTemplateExercise, UserWeeklySchedule

def initialize_default_workout_plan(user):
    """Force creates a comprehensive 5-day body-part split for new accounts."""
    existing = UserWeeklySchedule.objects.filter(user=user)
    if existing.exists() and existing.filter(is_rest_day=False).count() >= 6:
        return
        
    existing.delete()
        
    # 1. Chest & Triceps
    chest_tri = WorkoutTemplate.objects.filter(name="Chest & Triceps").first()
    if not chest_tri:
        chest_tri = WorkoutTemplate.objects.create(name="Chest & Triceps", description="Focus on pushing strength.")
        WorkoutTemplateExercise.objects.create(template=chest_tri, name="Bench Press", sets_reps="3 x 10", weight="40kg", order=1)
        WorkoutTemplateExercise.objects.create(template=chest_tri, name="Incline Dumbbell Press", sets_reps="3 x 12", weight="15kg", order=2)
        WorkoutTemplateExercise.objects.create(template=chest_tri, name="Tricep Pushdowns", sets_reps="3 x 15", weight="20kg", order=3)

    # 2. Back & Biceps
    back_bi = WorkoutTemplate.objects.filter(name="Back & Biceps").first()
    if not back_bi:
        back_bi = WorkoutTemplate.objects.create(name="Back & Biceps", description="Focus on pulling strength.")
        WorkoutTemplateExercise.objects.create(template=back_bi, name="Lat Pulldowns", sets_reps="3 x 12", weight="45kg", order=1)
        WorkoutTemplateExercise.objects.create(template=back_bi, name="Seated Cable Rows", sets_reps="3 x 10", weight="40kg", order=2)
        WorkoutTemplateExercise.objects.create(template=back_bi, name="Dumbbell Bicep Curls", sets_reps="3 x 12", weight="10kg", order=3)

    # 3. Legs & Abs
    legs_abs = WorkoutTemplate.objects.filter(name="Legs & Abs").first()
    if not legs_abs:
        legs_abs = WorkoutTemplate.objects.create(name="Legs & Abs", description="Lower body and core stability.")
        WorkoutTemplateExercise.objects.create(template=legs_abs, name="Barbell Squats", sets_reps="3 x 10", weight="50kg", order=1)
        WorkoutTemplateExercise.objects.create(template=legs_abs, name="Leg Extensions", sets_reps="3 x 15", weight="30kg", order=2)
        WorkoutTemplateExercise.objects.create(template=legs_abs, name="Plank", sets_reps="3 x 60s", weight="N/A", order=3)

    # 4. Shoulders & Forearms
    shoulders = WorkoutTemplate.objects.filter(name="Shoulders & Forearms").first()
    if not shoulders:
        shoulders = WorkoutTemplate.objects.create(name="Shoulders & Forearms", description="Upper body focus.")
        WorkoutTemplateExercise.objects.create(template=shoulders, name="Overhead Press", sets_reps="3 x 10", weight="30kg", order=1)
        WorkoutTemplateExercise.objects.create(template=shoulders, name="Lateral Raises", sets_reps="3 x 15", weight="7kg", order=2)
        WorkoutTemplateExercise.objects.create(template=shoulders, name="Wrist Curls", sets_reps="3 x 20", weight="5kg", order=3)

    # 5. Full Body / Cardio
    full_body = WorkoutTemplate.objects.filter(name="Full Body & HIIT").first()
    if not full_body:
        full_body = WorkoutTemplate.objects.create(name="Full Body & HIIT", description="Metabolic conditioning.")
        WorkoutTemplateExercise.objects.create(template=full_body, name="Burpees", sets_reps="3 x 15", weight="N/A", order=1)
        WorkoutTemplateExercise.objects.create(template=full_body, name="Deadlifts", sets_reps="3 x 8", weight="60kg", order=2)

    # 6. Abs & Cardio (Saturday)
    abs_cardio = WorkoutTemplate.objects.filter(name="Abs & Cardio").first()
    if not abs_cardio:
        abs_cardio = WorkoutTemplate.objects.create(name="Abs & Cardio", description="Core and endurance.")
        WorkoutTemplateExercise.objects.create(template=abs_cardio, name="Mountain Climbers", sets_reps="3 x 30", weight="N/A", order=1)
        WorkoutTemplateExercise.objects.create(template=abs_cardio, name="Leg Raises", sets_reps="3 x 15", weight="N/A", order=2)
        WorkoutTemplateExercise.objects.create(template=abs_cardio, name="Russian Twists", sets_reps="3 x 20", weight="N/A", order=3)

    plan = [
        (0, chest_tri, False), # Mon
        (1, back_bi, False),   # Tue
        (2, legs_abs, False),  # Wed
        (3, shoulders, False), # Thu
        (4, full_body, False), # Fri
        (5, abs_cardio, False),# Sat
        (6, None, True),       # Sun (Rest)
    ]
    
    for day_idx, template, is_rest in plan:
        UserWeeklySchedule.objects.create(user=user, day_of_week=day_idx, template=template, is_rest_day=is_rest)

class WeeklyScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        initialize_default_workout_plan(request.user)
        
        schedules = UserWeeklySchedule.objects.filter(user=request.user).order_by('day_of_week')
        serializer = UserWeeklyScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    def post(self, request):
        day_of_week = request.data.get('day_of_week')
        if day_of_week is None:
            return Response({'error': 'day_of_week is required'}, status=400)
            
        schedule, _ = UserWeeklySchedule.objects.get_or_create(user=request.user, day_of_week=day_of_week)
        serializer = UserWeeklyScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class TodayWorkoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Django's weekday() is 0 for Monday, 6 for Sunday
        # This matches our model's day_of_week
        today_idx = timezone.now().weekday()
        schedule = UserWeeklySchedule.objects.filter(user=request.user, day_of_week=today_idx).first()
        
        if not schedule or schedule.is_rest_day or not schedule.template:
            return Response({'message': 'Rest Day', 'is_rest_day': True})
            
        serializer = WorkoutTemplateSerializer(schedule.template)
        return Response(serializer.data)

class WorkoutTemplateListView(generics.ListCreateAPIView):
    queryset = WorkoutTemplate.objects.all()
    serializer_class = WorkoutTemplateSerializer
    permission_classes = [IsAuthenticated]
from users.models import DailyStats
from django.utils import timezone

class AddWorkoutLogView(generics.CreateAPIView):
    serializer_class = WorkoutLogSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        workout = serializer.save(user=self.request.user)
        
        # Update DailyStats
        today = workout.date
        stats, _ = DailyStats.objects.get_or_create(user=self.request.user, date=today)
        stats.workouts_completed += 1
        stats.calories_burned += workout.calories_burned
        stats.save()

class WorkoutHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_logs = WorkoutLog.objects.filter(user=request.user, date__gte=start_of_month)
        
        summary = {
            "monthWorkouts": month_logs.count(),
            "monthMinutes": sum(log.duration_minutes for log in month_logs),
            "monthCalories": sum(log.calories_burned for log in month_logs),
        }
        
        recent_logs = WorkoutLog.objects.filter(user=request.user).order_by('-date', '-created_at')[:10]
        serializer = WorkoutLogSerializer(recent_logs, many=True)
        
        return Response({
            "summary": summary,
            "recentWorkouts": serializer.data
        })

class DiaryDailyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'Date parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        entries = FoodEntry.objects.filter(user=request.user, date=date_str)
        serializer = FoodEntrySerializer(entries, many=True)
        
        # Calculate summary
        goal_calories = 2500
        food_calories = sum(entry.calories for entry in entries)
        exercise_calories = 0  # Placeholder for future integration
        remaining_calories = goal_calories - food_calories + exercise_calories

        # Group by meal
        meals = {
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "snacks": []
        }
        for data in serializer.data:
            meal_type = data['meal_type']
            if meal_type in meals:
                meals[meal_type].append(data)

        # Get water intake
        from water.models import WaterIntake
        water_record = WaterIntake.objects.filter(user=request.user, date=date_str).first()
        water_glasses = water_record.glasses_count if water_record else 0

        return Response({
            "date": date_str,
            "summary": {
                "goal": goal_calories,
                "food": food_calories,
                "exercise": exercise_calories,
                "remaining": remaining_calories
            },
            "meals": meals,
            "water_intake": water_glasses
        })

class AddFoodEntryView(generics.CreateAPIView):
    serializer_class = FoodEntrySerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        import re
        data = request.data
        user = request.user
        date = data.get('date')
        meal_type = data.get('meal_type')
        food_name = data.get('food_name')

        entry = FoodEntry.objects.filter(
            user=user, date=date, meal_type=meal_type, food_name=food_name
        ).first()

        if entry:
            # Accumulate
            match = re.search(r'(\d+)', entry.quantity)
            old_q = int(match.group(1)) if match else 1
            
            # Use data values as deltas (currently frontend sends 1-serving values)
            new_calories = int(data.get('calories', 0))
            new_protein = float(data.get('protein', 0))
            new_carbs = float(data.get('carbs', 0))
            new_fat = float(data.get('fat', 0))

            entry.quantity = f"{old_q + 1} servings"
            entry.calories += new_calories
            entry.protein += new_protein
            entry.carbs += new_carbs
            entry.fat += new_fat
            entry.save()
            
            serializer = self.get_serializer(entry)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        entry = serializer.save(user=self.request.user)
        
        # Sync with DailyStats to trigger streak and update totals
        from users.models import DailyStats
        stats, _ = DailyStats.objects.get_or_create(user=self.request.user, date=entry.date)
        stats.calories_consumed += entry.calories
        stats.protein_consumed += entry.protein
        stats.carbs_consumed += entry.carbs
        stats.fat_consumed += entry.fat
        stats.save()

class UpdateFoodEntryView(generics.UpdateAPIView):
    serializer_class = FoodEntrySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FoodEntry.objects.filter(user=self.request.user)

class DeleteFoodEntryView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FoodEntry.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        import re
        instance = self.get_object()
        match = re.search(r'(\d+)', instance.quantity)
        q = int(match.group(1)) if match else 1

        if q > 1:
            # Decrement nutritional values proportionally
            # We assume calories/macros are for 'q' servings
            per_serving_cals = instance.calories / q
            per_serving_protein = instance.protein / q
            per_serving_carbs = instance.carbs / q
            per_serving_fat = instance.fat / q

            instance.quantity = f"{q - 1} servings"
            instance.calories = round(instance.calories - per_serving_cals)
            instance.protein = max(0, instance.protein - per_serving_protein)
            instance.carbs = max(0, instance.carbs - per_serving_carbs)
            instance.fat = max(0, instance.fat - per_serving_fat)
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        return super().destroy(request, *args, **kwargs)

class SmartSwapsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import os
        import requests
        import json
        from .models import FoodEntry
        from users.models import UserProfile  # Assuming profile exists

        # 1. Get food name to search for (from param or recent log)
        food_name = request.query_params.get('food')
        if not food_name:
            recent_entry = FoodEntry.objects.filter(user=request.user).order_by('-created_at').first()
            food_name = recent_entry.food_name if recent_entry else "White Bread"
        
        # 2. Call AI for a better alternative
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            return Response({
                "current_food": food_name,
                "better_option": "Grilled Chicken and Steamed Veggies",
                "calorie_difference": "-120 kcal",
                "benefits": "Higher protein and lower fat content than standard Biryani"
            })

        system_prompt = (
            "You are a nutrition coach focusing on 'High Protein, Low Calorie' swaps. Suggest an alternative that is notably lower in calories "
            "but maintains or increases protein content (e.g., swapping biryani for grilled chicken salad with egg). "
            "Ensure the calorie_difference is always negative (indicating calories saved, e.g., '-150 kcal'). "
            "Return ONLY a JSON object with: 'current_food', 'better_option', 'calorie_difference', 'benefits'."
        )

        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Food suggestion for: {food_name}"}
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
            if response.ok:
                content = response.json()['choices'][0]['message']['content']
                return Response(json.loads(content))
        except Exception:
            pass

        return Response({
            "current_food": food_name,
            "better_option": "Whole Grain Bread",
            "calorie_difference": "-40 kcal",
            "benefits": "Higher fiber and lower glycemic index"
        })

# ─── Weight Log Views ─────────────────────────────────────────────────────────

from .models import WeightLog, WeightGoal
from .serializers import WeightLogSerializer, WeightGoalSerializer

class WeightLogView(APIView):
    """POST: log weight for a date. GET: return history (last 30 days)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = WeightLog.objects.filter(user=request.user).order_by('date')
        serializer = WeightLogSerializer(logs, many=True)
        return Response(serializer.data)

    def post(self, request):
        date = request.data.get('date')
        weight = request.data.get('weight')
        if not date or weight is None:
            return Response({'error': 'date and weight are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Move imports inside to avoid circular dependency
        from users.models import UserGoalSettings, DailyStats
        
        weight = float(weight)
        
        log = WeightLog.objects.create(
            user=request.user, date=date,
            weight=weight
        )

        # Synchronize with User profile and GoalSettings
        user = request.user
        user.current_weight = weight
        user.save()

        goal_settings, _ = UserGoalSettings.objects.get_or_create(user=user)
        goal_settings.current_weight = weight
        goal_settings.save()

        # Sync with DailyStats for today
        stats, _ = DailyStats.objects.get_or_create(user=user, date=date)
        stats.weight_kg = weight
        stats.save()

        return Response(WeightLogSerializer(log).data, status=status.HTTP_201_CREATED)


class WeightGoalView(APIView):
    """GET: return current goal.  POST/PUT: set or update start+target weight."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            goal = WeightGoal.objects.get(user=request.user)
            return Response(WeightGoalSerializer(goal).data)
        except WeightGoal.DoesNotExist:
            return Response({'start_weight': None, 'target_weight': None}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        start = request.data.get('start_weight')
        target = request.data.get('target_weight')
        weekly = request.data.get('weekly_goal_weight')
        
        if start is None or target is None:
            return Response({'error': 'start_weight and target_weight are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Move imports inside to avoid circular dependency
        from users.models import UserGoalSettings
        
        start = float(start)
        target = float(target)
        weekly = float(weekly) if weekly is not None else 0.5

        goal, _ = WeightGoal.objects.update_or_create(
            user=request.user,
            defaults={
                'start_weight': start, 
                'target_weight': target,
                'weekly_goal_weight': weekly
            }
        )

        # Synchronize with User profile and GoalSettings
        user = request.user
        user.current_weight = start
        user.goal_weight = target
        user.save()

        goal_settings, _ = UserGoalSettings.objects.get_or_create(user=user)
        goal_settings.current_weight = start
        goal_settings.target_weight = target
        goal_settings.save()

        return Response(WeightGoalSerializer(goal).data, status=status.HTTP_200_OK)
