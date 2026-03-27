from django import forms
from users.models import User
from django.contrib.auth import password_validation

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email is already registered.')
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        password_validation.validate_password(password)
        return password

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        return confirm_password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = self.cleaned_data['password']
        if commit:
            user.save()
        return user

from diary.models import FoodEntry, WorkoutLog

class FoodEntryForm(forms.ModelForm):
    class Meta:
        model = FoodEntry
        fields = ['meal_type', 'food_name', 'quantity', 'calories', 'protein', 'carbs', 'fat']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select rounded-pill'}),
            'food_name': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'e.g. Scrambled Eggs'}),
            'quantity': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'e.g. 2 large eggs'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '0'}),
            'protein': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '0.0', 'step': '0.1'}),
            'carbs': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '0.0', 'step': '0.1'}),
            'fat': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '0.0', 'step': '0.1'}),
        }

class WorkoutLogForm(forms.ModelForm):
    class Meta:
        model = WorkoutLog
        fields = ['date', 'workout_type', 'calories_burned', 'duration_minutes']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control rounded-pill', 'type': 'date'}),
            'workout_type': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'e.g. Running'}),
            'calories_burned': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '0'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['calories_burned'].required = False
        self.fields['duration_minutes'].required = False
        self.fields['calories_burned'].initial = 0
        self.fields['duration_minutes'].initial = 0
