
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myfitnessbuddy_backend.settings')
django.setup()

from water.models import WaterIntake

records = WaterIntake.objects.all().order_by('-date')
print(f"Total records: {records.count()}")
for r in records[:10]:
    print(f"User: {r.user.username}, Date: {r.date}, Glasses: {r.glasses_count}")
