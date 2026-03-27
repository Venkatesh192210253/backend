from django.db import models
from django.conf import settings

class WaterIntake(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='water_intake')
    date = models.DateField()
    glasses_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.glasses_count} glasses for {self.user.username} on {self.date}"
