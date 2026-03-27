from rest_framework import serializers
from .models import Food

class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = [
            'id', 'name', 'calories', 'protein', 'carbs', 'fat', 'category',
            'serving_size', 'servings_per_container', 'saturated_fat', 'trans_fat',
            'polyunsaturated_fat', 'monounsaturated_fat', 'cholesterol', 'sodium',
            'dietary_fiber', 'total_sugars', 'added_sugars', 'vitamin_d', 'calcium',
            'iron', 'potassium'
        ]
