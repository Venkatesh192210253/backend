from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from users.models import User, DailyStats, UserProfile, UserGoalSettings
from users.views import calculate_ai_metrics
from diary.models import FoodEntry, WorkoutLog, WaterIntake, WeightLog
from django.db.models import Sum, Q, F
from datetime import date, timedelta
from .forms import LoginForm, SignupForm, FoodEntryForm, WorkoutLogForm
from django.http import JsonResponse
import os
import requests
import json
from django.conf import settings
from diary.views import initialize_default_workout_plan

# Load dataset for Web AI Coach
AI_DATASET = []
dataset_path = os.path.join(settings.BASE_DIR, 'ai_trained_model', 'dataset.json')
try:
    if os.path.exists(dataset_path):
        with open(dataset_path, 'r') as f:
            AI_DATASET = json.load(f)
except Exception as e:
    print(f"Error loading AI dataset in web views: {e}")

@login_required(login_url='login')
def dashboard_view(request):
    date_str = request.GET.get('date')
    if date_str:
        try:
            today = date.fromisoformat(date_str)
        except ValueError:
            today = date.today()
    else:
        today = date.today()
    
    # Force sync statistics from source models to DailyStats for consistency
    stats, created = DailyStats.objects.get_or_create(userid=request.user, date=today)
    stats.save()

    # Get recent logs
    recent_food = FoodEntry.objects.filter(user=request.user, date=today).order_by('-created_at')[:5]
    recent_workouts = WorkoutLog.objects.filter(user=request.user, date=today).order_by('-created_at')[:5]
    
    # Aggregate statistics from source models
    food_totals = FoodEntry.objects.filter(user=request.user, date=today).aggregate(
        cals=Sum('calories'), prot=Sum('protein'), carb=Sum('carbs'), fat=Sum('fat')
    )
    workout_totals = WorkoutLog.objects.filter(user=request.user, date=today).aggregate(
        burned=Sum('calories_burned'), count=Sum('id')
    )
    water_total = WaterIntake.objects.filter(user=request.user, date=today).aggregate(
        total=Sum('amount_ml')
    )

    # Prepare stats dictionary for the template to maintain compatibility
    stats_data = {
        'steps': stats.steps,
        'calories_consumed': food_totals['cals'] or 0,
        'protein_consumed': food_totals['prot'] or 0,
        'carbs_consumed': food_totals['carb'] or 0,
        'fat_consumed': food_totals['fat'] or 0,
        'calories_burned': workout_totals['burned'] or 0,
        'water_ml': water_total['total'] or 0,
    }
    
    # Goals and Progress
    try:
        goals = request.user.goal_settings
        calorie_progress = (stats_data['calories_consumed'] / goals.daily_calorie_target * 100) if goals.daily_calorie_target > 0 else 0
        step_progress = (stats_data['steps'] / goals.daily_step_goal * 100) if goals.daily_step_goal > 0 else 0
        protein_progress = (stats_data['protein_consumed'] / goals.protein_g * 100) if goals.protein_g > 0 else 0
        carbs_progress = (stats_data['carbs_consumed'] / goals.carbs_g * 100) if goals.carbs_g > 0 else 0
        fat_progress = (stats_data['fat_consumed'] / goals.fats_g * 100) if goals.fats_g > 0 else 0
    except (UserGoalSettings.DoesNotExist, AttributeError):
        goals = None
        calorie_progress = step_progress = protein_progress = carbs_progress = fat_progress = 0

    # Weight Fetching
    latest_weight_log = WeightLog.objects.filter(user=request.user).order_by('-date', '-created_at').first()
    current_weight = latest_weight_log.weight if latest_weight_log else (goals.current_weight if goals else 0)
    
    # AI Metrics (Synchronized with App)
    ai_metrics = calculate_ai_metrics(request.user, today)
    readiness_score = int(ai_metrics['recovery_score'])
    energy_index = int(ai_metrics['energy_balance_score'])
    
    # Apply Mobile App's Local Penalties to Readiness on Web
    # 1. Fatigue Penalty
    yesterday_date = today - timedelta(days=1)
    yesterday_stats = WorkoutLog.objects.filter(user=request.user, date=yesterday_date).aggregate(Sum('calories_burned'))
    yesterday_steps_m = DailyStats.objects.filter(userid=request.user, date=yesterday_date).first()
    yesterday_burned = (yesterday_stats['calories_burned__sum'] or 0) + ((yesterday_steps_m.steps if yesterday_steps_m else 0) * 0.04)
    if yesterday_burned > 800:
        readiness_score -= 15
        
    # 2. Nutrition Penalty
    if goals and stats_data['calories_consumed'] < (goals.daily_calorie_target * 0.4):
        readiness_score -= 10
        
    readiness_score = max(5, min(100, readiness_score))
    
    # SVG Offset calculation
    readiness_offset = 314.159 * (1 - readiness_score / 100)

    # Predictive Goal Analysis (Matches App AdaptiveAiManager)
    target_date_pred = "Set a goal first"
    confidence = 0
    trend = "Stable"
    
    if goals and goals.target_weight and goals.weekly_goal_weight > 0:
        weight_to_go = abs(goals.target_weight - current_weight)
        weeks = weight_to_go / goals.weekly_goal_weight
        predicted_date = today + timedelta(weeks=weeks)
        target_date_pred = predicted_date.strftime("%B %d, %Y")
        
        # Confidence logic based on weekly consistency (Mocked until we have more historical stats)
        confidence = 85 # High baseline for new users
        trend = "On Track" if current_weight != goals.target_weight else "Goal Reached"

    # Enhanced Weight Progress Calculation
    weight_progress = 5 # Minimum visibility
    if goals and goals.target_weight:
        # Try to find the start weight from the earliest log
        earliest_log = WeightLog.objects.filter(user=request.user).order_by('date', 'created_at').first()
        start_w = earliest_log.weight if earliest_log else (goals.current_weight or current_weight)
        
        # Distance from start to target
        total_distance = abs(goals.target_weight - start_w)
        if total_distance > 0:
            # How much we have moved from start towards target
            covered = abs(current_weight - start_w)
            weight_progress = max(5, min(100, (covered / total_distance) * 100))
        elif current_weight == goals.target_weight:
            weight_progress = 100

    context = {
        'stats': stats_data,
        'recent_food': recent_food,
        'recent_workouts': recent_workouts,
        'goals': goals,
        'calorie_progress': calorie_progress,
        'step_progress': step_progress,
        'protein_progress': protein_progress,
        'carbs_progress': carbs_progress,
        'fat_progress': fat_progress,
        'active_date': today,
        'prev_date': today - timedelta(days=1),
        'next_date': today + timedelta(days=1),
        'is_today': today == date.today(),
        'readiness_score': readiness_score,
        'readiness_offset': readiness_offset,
        'energy_index': energy_index,
        'current_weight': current_weight,
        'weight_progress': weight_progress,
        'weight_remaining': abs(goals.target_weight - current_weight) if goals and goals.target_weight else 0,
        'weeks_remaining': round(abs(goals.target_weight - current_weight) / goals.weekly_goal_weight, 1) if goals and goals.target_weight and goals.weekly_goal_weight > 0 else 0,
        'is_bulking': (goals.target_weight > current_weight) if goals and goals.target_weight and current_weight else False,
        'weight_history': latest_weight_log,
        'prediction': {
            'target_date': target_date_pred,
            'confidence': confidence,
            'trend': trend,
            'is_valid': (goals.target_weight > 0) if goals else False
        }
    }
    return render(request, 'web/dashboard.html', context)

@login_required(login_url='login')
def weight_view(request):
    goals_q, _ = UserGoalSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'log_weight':
            weight = request.POST.get('weight')
            if weight:
                w_val = float(weight)
                WeightLog.objects.create(user=request.user, date=date.today(), weight=w_val)
                request.user.current_weight = w_val
                request.user.save()
                goals_q.current_weight = w_val
                goals_q.save()
        elif action == 'update_goal':
            target = request.POST.get('target_weight')
            weekly = request.POST.get('weekly_goal')
            unit = request.POST.get('weekly_unit', 'kg')
            
            if target: goals_q.target_weight = float(target)
            if weekly:
                w_val = float(weekly)
                if unit == 'gm': w_val /= 1000.0
                goals_q.weekly_goal_weight = w_val
            goals_q.save()
            
            # Sync user model
            if target:
                request.user.goal_weight = float(target)
                request.user.save()
                
        return redirect('weight_log')

    weight_history = WeightLog.objects.filter(user=request.user).order_by('-date', '-created_at')
    current_w = request.user.current_weight or 0
    target_w = goals_q.target_weight or 0
    weekly_w = goals_q.weekly_goal_weight or 0.5
    
    weight_diff = abs(target_w - current_w)
    weeks_remaining = round(weight_diff / weekly_w, 1) if weekly_w > 0 else 0
    
    # Unit display logic
    weekly_display = weekly_w
    weekly_unit = 'kg'
    if weekly_w < 1.0:
        weekly_display = int(weekly_w * 1000)
        weekly_unit = 'gm'

    context = {
        'weight_history': weight_history,
        'current_weight': current_w,
        'goal_weight': target_w,
        'weekly_goal': weekly_w,
        'weekly_display': weekly_display,
        'weekly_unit': weekly_unit,
        'weight_remaining': weight_diff,
        'weeks_remaining': weeks_remaining,
        'is_bulking': target_w > current_w if target_w and current_w else False,
    }
    return render(request, 'web/weight_log.html', context)

@login_required(login_url='login')
def weight_delete(request, entry_id):
    entry = get_object_or_404(WeightLog, id=entry_id, user=request.user)
    entry.delete()
    return redirect('weight_log')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    
    return render(request, 'web/login.html', {'form': form, 'hide_nav': True})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Ensure Profile, GoalSettings, and Workout Plan exist for the new user
            UserProfile.objects.get_or_create(user=user)
            UserGoalSettings.objects.get_or_create(user=user)
            initialize_default_workout_plan(user)
            
            user.backend = 'users.backends.PlaintextAuthBackend'
            login(request, user)
            messages.success(request, "Your registration was successful. Welcome to MyFitnessBuddy!")
            return redirect('dashboard')
    else:
        form = SignupForm()
    return render(request, 'web/signup.html', {'form': form, 'hide_nav': True})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def food_view(request):
    date_str = request.GET.get('date')
    active_date = date.today()
    if date_str:
        try: active_date = date.fromisoformat(date_str)
        except: pass
        
    if request.method == 'POST':
        form = FoodEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.date = active_date # Log to the viewed date
            entry.save()
            
            # Update DailyStats
            stats, created = DailyStats.objects.get_or_create(userid=request.user, date=entry.date)
            stats.save()
            
            messages.success(request, f"Logged {entry.food_name} successfully.")
            return redirect(f"{request.path}?date={active_date.isoformat()}")
    else:
        form = FoodEntryForm()

    food_entries = FoodEntry.objects.filter(user=request.user, date=active_date)
    
    # Group by meal types
    meals = {
        'Breakfast': {'entries': food_entries.filter(meal_type='breakfast'), 'total': 0},
        'Lunch': {'entries': food_entries.filter(meal_type='lunch'), 'total': 0},
        'Dinner': {'entries': food_entries.filter(meal_type='dinner'), 'total': 0},
        'Snacks': {'entries': food_entries.filter(meal_type='snacks'), 'total': 0},
    }
    
    for m in meals.values():
        m['total'] = m['entries'].aggregate(Sum('calories'))['calories__sum'] or 0

    total_food = food_entries.aggregate(Sum('calories'))['calories__sum'] or 0
    total_exercise = WorkoutLog.objects.filter(user=request.user, date=active_date).aggregate(Sum('calories_burned'))['calories_burned__sum'] or 0
    
    try:
        goals = request.user.goal_settings
        goal_calories = goals.daily_calorie_target
    except:
        goal_calories = 2500
        
    remaining = goal_calories - total_food + total_exercise
    
    # Water Intake
    water, _ = WaterIntake.objects.get_or_create(user=request.user, date=active_date)
    
    summary = {
        'goal': goal_calories,
        'food': total_food,
        'exercise': total_exercise,
        'remaining': remaining,
        'progress': min((total_food / goal_calories * 100), 100) if goal_calories > 0 else 0
    }
    
    # Pre-calculated values for template
    summary['progress_offset'] = 502.65 * (1 - summary['progress'] / 100)

    context = {
        'active_date': active_date,
        'today': date.today(),
        'prev_date': active_date - timedelta(days=1),
        'next_date': active_date + timedelta(days=1),
        'meals': meals,
        'form': form,
        'water': water,
        'water_liters': water.amount_ml / 1000,
        'water_glasses': min(water.amount_ml // 250, 12),
        'glass_range': range(1, 13),
        'summary': summary
    }
    return render(request, 'web/food.html', context)

@login_required(login_url='login')
def water_update(request):
    if request.method == 'POST':
        action = request.POST.get('action') # "plus" or "minus"
        date_str = request.POST.get('date')
        active_date = date.fromisoformat(date_str) if date_str else date.today()
        
        water, _ = WaterIntake.objects.get_or_create(user=request.user, date=active_date)
        if action == 'plus':
            water.amount_ml += 250 # 1 glass
        elif action == 'minus':
            water.amount_ml = max(0, water.amount_ml - 250)
        water.save()
        
        # Sync to DailyStats
        stats, _ = DailyStats.objects.get_or_create(userid=request.user, date=active_date)
        stats.save()
        
        return JsonResponse({'amount_ml': water.amount_ml})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url='login')
def food_delete(request, entry_id):
    try:
        entry = FoodEntry.objects.get(id=entry_id, user=request.user)
        entry_date = entry.date
        entry.delete()
        
        # Recalculate stats
        stats, _ = DailyStats.objects.get_or_create(userid=request.user, date=entry_date)
        stats.save()
        
        messages.success(request, "Food entry removed.")
    except:
        messages.error(request, "Error removing food entry.")
        
    return redirect(f"{request.path.replace(str(entry_id) + '/', '')}?date={entry_date.isoformat()}")

@login_required(login_url='login')
def workout_view(request):
    from web.forms import WorkoutLogForm
    from diary.models import WorkoutLog, ExerciseLogEntry, UserWeeklySchedule
    from users.models import DailyStats
    import json
    from django.utils import timezone

    if request.method == 'POST':
        form = WorkoutLogForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            
            stats, _ = DailyStats.objects.get_or_create(userid=request.user, date=workout.date)
            stats.save()
            
            # Update UserProfile
            profile = getattr(request.user, 'profile', None)
            if profile:
                profile.workouts_completed += 1
                profile.add_xp(50)
                profile.save()
            
            messages.success(request, "Workout logged successfully!")
            return redirect('workout')
        else:
            print(f"DEBUG: Form Errors: {form.errors}")
            # Fallback for session form if it's partially valid
            if 'workout_type' in request.POST and 'exercises_list' in request.POST:
                print("DEBUG: Attempting manual save for session...")
                workout_date = request.POST.get('date') or timezone.now().date()
                workout = WorkoutLog.objects.create(
                    user=request.user,
                    date=workout_date,
                    workout_type=request.POST.get('workout_type', 'Workout'),
                    calories_burned=int(request.POST.get('calories_burned', 300)),
                    duration_minutes=int(request.POST.get('duration_minutes', 45))
                )
                
                exercises_data = json.loads(request.POST.get('exercises_list', '[]'))
                for ex in exercises_data:
                    if ex.get('completed'):
                        ExerciseLogEntry.objects.create(
                            workout=workout,
                            name=ex.get('name'),
                            sets_reps=ex.get('sets_reps', '3x10'),
                            weight=ex.get('weight', '0kg'),
                            is_completed=True
                        )
                
                stats, _ = DailyStats.objects.get_or_create(userid=request.user, date=workout.date)
                stats.save()
                
                profile = request.user.profile
                profile.workouts_completed += 1
                profile.add_xp(50)
                profile.save()
                messages.success(request, "Workout logged successfully!")
                return redirect('workout')
            messages.error(request, "Error logging workout. Please check the form.") # Added error message for invalid form
    else:
        form = WorkoutLogForm()

    workouts = WorkoutLog.objects.filter(user=request.user).order_by('-date', '-created_at')
    schedule = UserWeeklySchedule.objects.filter(user=request.user).select_related('template').prefetch_related('template__exercises').order_by('day_of_week')
    
    # Fetch last 10 completed exercises
    recent_exercises = ExerciseLogEntry.objects.filter(workout__user=request.user, is_completed=True).order_by('-workout__date', '-id')[:10]
    recent_exercises_list = list(recent_exercises)

    # If no schedule exists, or if fewer than 6 training days exist, update to the 6-day plan
    if not schedule.exists() or schedule.filter(is_rest_day=False).count() < 6:
        initialize_default_workout_plan(request.user)
        schedule = UserWeeklySchedule.objects.filter(user=request.user).select_related('template').prefetch_related('template__exercises').order_by('day_of_week')

    # Fetch last 7 days for the chart (Aggregate from WorkoutLog)
    from datetime import timedelta, date
    today_date = date.today()
    chart_data = []
    
    for i in range(6, -1, -1):
        target_date_c = today_date - timedelta(days=i)
        daily_burned = WorkoutLog.objects.filter(user=request.user, date=target_date_c).aggregate(
            total=Sum('calories_burned')
        )['total'] or 0
        
        chart_data.append({
            'date': target_date_c.strftime("%M %j"), # Format for template
            'display_date': target_date_c,
            'calories_burned': daily_burned
        })

    context = {
        'workouts': workouts,
        'form': form,
        'schedule': schedule,
        'recent_exercises': recent_exercises_list,
        'chart_data': chart_data,
    }
    return render(request, 'web/workout.html', context)

@login_required(login_url='login')
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        bio = request.POST.get('bio')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        current_weight = request.POST.get('current_weight')
        
        # Update Profile
        profile.full_name = full_name
        profile.bio = bio
        profile.save()
        
        # Update User
        user = request.user
        if age: user.age = int(age)
        if gender: user.gender = gender
        if current_weight: user.current_weight = float(current_weight)
        user.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('profile')
        
    return render(request, 'web/profile.html', {'profile': profile})

@login_required(login_url='login')
def notifications_view(request):
    # Fetch from the existing notifications app
    from notifications.models import Notification
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'web/notifications.html', {'notifications': notifications})

@login_required(login_url='login')
def ai_coach_view(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '').lower()
        history = json.loads(request.POST.get('history', '[]'))
        
        # Load Trained Dataset (Matches App behavior)
        dataset_path = os.path.join(settings.BASE_DIR, 'ai_trained_model', 'dataset.json')
        ai_dataset = []
        try:
            if os.path.exists(dataset_path):
                with open(dataset_path, 'r') as f:
                    ai_dataset = json.load(f)
        except Exception as e:
            print(f"Web AI error loading dataset: {e}")

        best_match = None
        max_score = 0
        question_words = set(user_message.split())
        
        if ai_dataset:
            for item in ai_dataset:
                item_q = item.get('question', '').lower()
                item_words = set(item_q.replace('?', '').split())
                score = len(question_words.intersection(item_words))
                if score > max_score:
                    max_score = score
                    best_match = item
        
        if best_match and max_score > 0:
            final_answer = best_match['answer']
        else:
            final_answer = "To reach your goals, focus on a balanced diet of lean proteins and vegetables, drink at least 2L of water daily, and aim for 30 minutes of physical activity. Try logging your meals in the Food Diary for personalized tracking!"

        # Maintain OpenAI structure for frontend compatibility
        return JsonResponse({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": final_answer
                }
            }]
        })

    return render(request, 'web/ai_coach.html')

@login_required(login_url='login')
def ai_food_search_json(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse([], safe=False)
        
    groq_api_key = os.getenv("GROQ_API_KEY")
    prompt = f"""
    Search for food items matching: "{query}".
    The first item MUST be the most direct and common version of "{query}".
    Provide a list of the top 8 most accurate and common items.
    
    Return ONLY a JSON array of objects. 
    Each object must have:
    - name: string (e.g., "Curd / Yogurt", "Whole Milk")
    - calories: integer (per serving)
    - protein: float (grams)
    - carbs: float (grams)
    - fat: float (grams)
    - serving_size: string (e.g. "1 cup (245g)", "100g")

    No extra text or conversation.
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a specialized nutrition database. You provide precise, high-accuracy food data in JSON format only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Rigorous JSON extraction
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        results = json.loads(content)
        if isinstance(results, dict) and 'items' in results:
            results = results['items']
        elif isinstance(results, dict):
            results = [results]
            
        return JsonResponse(results, safe=False)
    except Exception as e:
        print(f"Groq API Error: {str(e)}")
        return JsonResponse([], safe=False)

@login_required(login_url='login')
def friends_view(request):
    from users.models import Friend, FriendRequest, Group, Challenge, DailyStats, User
    
    # Process actions like accept/reject/send friend requests
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'send_request':
            target_username = request.POST.get('username')
            target_user = User.objects.filter(username__iexact=target_username).first()
            if target_user and target_user != request.user:
                if Friend.objects.filter(user=request.user, friend=target_user).exists():
                    messages.info(request, "You are already friends.")
                else:
                    FriendRequest.objects.get_or_create(sender=request.user, receiver=target_user)
                    messages.success(request, f"Friend request sent to {target_user.username}!")
            else:
                messages.error(request, "User not found or invalid.")
        elif action == 'accept_request':
            req_id = request.POST.get('request_id')
            req = FriendRequest.objects.filter(id=req_id, receiver=request.user, status='pending').first()
            if req:
                req.status = 'accepted'
                req.save()
                Friend.objects.get_or_create(user=request.user, friend=req.sender)
                Friend.objects.get_or_create(user=req.sender, friend=request.user)
                messages.success(request, f"Accepted {req.sender.username}'s friend request!")
        elif action == 'reject_request':
            req_id = request.POST.get('request_id')
            req = FriendRequest.objects.filter(id=req_id, receiver=request.user, status='pending').first()
            if req:
                req.status = 'rejected'
                req.save()
                messages.info(request, "Friend request rejected.")
        elif action == 'join_group':
            group_id = request.POST.get('group_id')
            groups_q = Group.objects.filter(id=group_id).first()
            if groups_q:
                from users.models import GroupMember
                GroupMember.objects.get_or_create(group=groups_q, user=request.user, status='joined')
                messages.success(request, f"You joined {groups_q.name}!")
        return redirect('friends')

    # Handle searching for friends
    search_query = request.GET.get('search_query', '')
    search_results = []
    if search_query:
        search_results = User.objects.filter(username__icontains=search_query).exclude(id=request.user.id).select_related('profile')[:10]

    # Data fetching for Dashboard Social Layer
    friends_list = Friend.objects.filter(user=request.user).select_related('friend', 'friend__profile')
    incoming_requests = FriendRequest.objects.filter(receiver=request.user, status='pending')
    
    # Friend Suggestions
    friend_ids = list(friends_list.values_list('friend_id', flat=True))
    friend_ids.append(request.user.id)
    sent_request_ids = FriendRequest.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
    exclude_ids = list(friend_ids) + list(sent_request_ids)
    
    suggestions_f = User.objects.exclude(id__in=exclude_ids).select_related('profile')[:5]

    today_f = timezone.now().date()
    
    # Get stats for leaderboard
    all_leaderboard_ids = list(friend_ids) + [request.user.id]
    raw_leaderboard_stats = DailyStats.objects.filter(userid_id__in=all_leaderboard_ids, date=today_f).select_related('userid', 'userid__profile')
    
    leaderboard_stats_l = []
    for stat_l in raw_leaderboard_stats:
        from diary.models import WorkoutLog
        workouts_l = WorkoutLog.objects.filter(user=stat_l.userid, date=today_f)
        burned_kcal_l = workouts_l.aggregate(total=Sum('calories_burned'))['total'] or 0
        
        leaderboard_stats_l.append({
            'user': stat_l.userid,
            'steps': stat_l.steps,
            'workouts_completed': workouts_l.count(),
            'calories_burned': burned_kcal_l
        })
    leaderboard_stats_l.sort(key=lambda x: x['steps'], reverse=True)

    # Weekly Comparison Insight
    seven_days_ago_f = today_f - timedelta(days=6)
    
    my_weekly_stats_f = DailyStats.objects.filter(userid=request.user, date__gte=seven_days_ago_f).aggregate(
        total_steps=Sum('steps')
    )
    my_weekly_stats_f['total_calories'] = WorkoutLog.objects.filter(
        user=request.user, 
        date__gte=seven_days_ago_f
    ).aggregate(total=Sum('calories_burned'))['total'] or 0
    
    friend_weekly_ranking_f = []
    for f_id_f in friend_ids:
        if f_id_f == request.user.id: continue
        f_user_f = User.objects.filter(id=f_id_f).first()
        if not f_user_f: continue
        
        f_steps_f = DailyStats.objects.filter(userid_id=f_id_f, date__gte=seven_days_ago_f).aggregate(total=Sum('steps'))['total'] or 0
        f_calories_f = WorkoutLog.objects.filter(user_id=f_id_f, date__gte=seven_days_ago_f).aggregate(total=Sum('calories_burned'))['total'] or 0
        
        friend_weekly_ranking_f.append({
            'userid__username': f_user_f.username,
            'total_steps': f_steps_f,
            'total_calories': f_calories_f
        })
    
    friend_weekly_ranking_f.sort(key=lambda x: x['total_calories'], reverse=True)

    my_groups_f = request.user.groupmember_set.filter(status='joined').select_related('group')
    public_groups_f = Group.objects.filter(is_public=True).exclude(id__in=my_groups_f.values_list('group_id', flat=True))[:5]
    active_challenges_f = request.user.challengeparticipant_set.filter(is_completed=False).select_related('challenge', 'challenge__group')

    context = {
        'friends': friends_list,
        'suggestions': suggestions_f,
        'incoming_requests': incoming_requests,
        'leaderboard_stats': leaderboard_stats_l,
        'my_weekly_stats': my_weekly_stats_f,
        'friend_weekly_ranking': friend_weekly_ranking_f,
        'groups': my_groups_f,
        'public_groups': public_groups_f,
        'active_challenges': active_challenges_f,
        'search_results': search_results,
        'search_query': search_query,
    }
    return render(request, 'web/friends.html', context)

@login_required(login_url='login')
def group_detail_view(request, group_id):
    from users.models import Group, GroupMember, GroupMessage, Challenge, DailyStats
    group_q = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST' and 'message' in request.POST:
        msg_q = request.POST.get('message')
        if msg_q:
            GroupMessage.objects.create(group=group_q, sender=request.user, message=msg_q)
            return redirect('group_detail', group_id=group_id)

    members_q = group_q.members.filter(status='joined').select_related('user', 'user__profile')
    messages_q = group_q.messages.all().order_by('created_at')[:50]
    challenges_q = group_q.challenges.all()
    
    today_q = timezone.now().date()
    member_ids_q = members_q.values_list('user_id', flat=True)
    leaderboard_q = DailyStats.objects.filter(userid_id__in=member_ids_q, date=today_q).select_related('userid', 'userid__profile').order_by('-steps')

    context = {
        'group': group_q,
        'members': members_q,
        'messages': messages_q,
        'challenges': challenges_q,
        'leaderboard': leaderboard_q,
        'is_member': members_q.filter(user=request.user).exists(),
    }
    return render(request, 'web/group_detail.html', context)

@login_required(login_url='login')
def goal_settings_view(request):
    goals_q, created = UserGoalSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        # Nutritional
        goals_q.daily_calorie_target = int(request.POST.get('daily_calorie_target') or goals_q.daily_calorie_target)
        goals_q.protein_g = int(request.POST.get('protein_g') or goals_q.protein_g)
        goals_q.carbs_g = int(request.POST.get('carbs_g') or goals_q.carbs_g)
        goals_q.fats_g = int(request.POST.get('fats_g') or goals_q.fats_g)
        
        # Weight Goals
        goals_q.target_weight = float(request.POST.get('target_weight') or goals_q.target_weight or 0)
        goals_q.weekly_goal_weight = float(request.POST.get('weekly_goal_weight') or goals_q.weekly_goal_weight or 0.5)
        
        # Update User's Current Weight
        new_weight = request.POST.get('current_weight')
        if new_weight:
            request.user.current_weight = float(new_weight)
            request.user.save()
            goals_q.current_weight = float(new_weight) # Sync
            
        # Activity
        goals_q.daily_step_goal = int(request.POST.get('daily_step_goal') or goals_q.daily_step_goal)
        goals_q.workouts_per_week = int(request.POST.get('workouts_per_week') or 4)
        
        goals_q.save()
        messages.success(request, "Goal settings updated successfully!")
        return redirect('goal_settings')
    
    # Calculate Prediction
    current_w = request.user.current_weight or 72.0
    target_w = goals_q.target_weight or 72.0
    weekly_w = goals_q.weekly_goal_weight or 0.5
    
    weight_diff = abs(current_w - target_w)
    weeks_remaining = round(weight_diff / weekly_w, 1) if weekly_w > 0 else 0
    
    # Approximate completion percentage (simple version)
    # If we assume they started at a certain point, we don't have start_weight.
    # Let's mock it at a reasonable progress if they are close, or 0 if they just started.
    completion_percentage = 0
    if weight_diff == 0:
        completion_percentage = 100
    else:
        # Just a visual filler for now matching the UI's progress bar
        completion_percentage = max(5, min(95, 100 - (weight_diff * 5))) 

    context = {
        'goals': goals_q,
        'weeks_remaining': weeks_remaining,
        'completion_percentage': completion_percentage,
    }
    
    return render(request, 'web/goal_settings.html', context)

@login_required(login_url='login')
def privacy_security_view(request):
    if request.method == 'POST':
        action_p = request.POST.get('action')
        if action_p == 'change_password':
            old_p = request.POST.get('old_password')
            new_p = request.POST.get('new_password')
            conf_p = request.POST.get('confirm_password')
            if request.user.check_password(old_p):
                if new_p == conf_p:
                    request.user.set_password(new_p)
                    request.user.save()
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Password changed successfully!")
                else:
                    messages.error(request, "New passwords do not match.")
            else:
                messages.error(request, "Incorrect old password.")
            return redirect('privacy_security')
        elif action_p == 'delete_account':
            conf_d = request.POST.get('confirmation')
            if conf_d == 'DELETE':
                user_d = request.user
                logout(request)
                user_d.delete()
                return redirect('login')
            else:
                messages.error(request, "Please type DELETE to confirm.")
                return redirect('privacy_security')
                
    return render(request, 'web/privacy_security.html')

@login_required(login_url='login')
def help_support_view(request):
    return render(request, 'web/help_support.html')