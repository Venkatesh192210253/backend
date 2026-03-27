from django.db import models

class Food(models.Model):
    name = models.CharField(max_length=255)
    calories = models.IntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    category = models.CharField(max_length=100, blank=True, null=True)
    
    # Detailed Nutrition Fields
    serving_size = models.CharField(max_length=100, default="1 serving")
    servings_per_container = models.CharField(max_length=100, default="1")
    
    saturated_fat = models.FloatField(default=0.0)
    trans_fat = models.FloatField(default=0.0)
    polyunsaturated_fat = models.FloatField(default=0.0)
    monounsaturated_fat = models.FloatField(default=0.0)
    
    cholesterol = models.FloatField(default=0.0)
    sodium = models.FloatField(default=0.0)
    dietary_fiber = models.FloatField(default=0.0)
    total_sugars = models.FloatField(default=0.0)
    added_sugars = models.FloatField(default=0.0)
    
    vitamin_d = models.FloatField(default=0.0)
    calcium = models.FloatField(default=0.0)
    iron = models.FloatField(default=0.0)
    potassium = models.FloatField(default=0.0)

    def __str__(self):
        return self.name
