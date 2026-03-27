import os
import traceback
from datetime import datetime
from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import WaterIntake
from .serializers import WaterIntakeSerializer

class WaterIntakeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'Date parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        record = WaterIntake.objects.filter(user=request.user, date=date_str).first()
        if record:
            serializer = WaterIntakeSerializer(record)
            return Response(serializer.data)
        
        return Response({'date': date_str, 'glasses_count': 0})

    def post(self, request):
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_debug.log")
        
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now()}] WATER REQUEST FROM {request.user.username}: {request.data}")

        # Check for ping
        if request.data.get('ping') == True:
            return Response({"message": "Pong! Water app is reachable"})

        date_str = request.data.get('date')
        glasses = request.data.get('glasses')

        if not date_str or glasses is None:
            return Response({'error': 'Date and glasses fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            glasses_count = int(glasses)
            date_obj = parse_date(date_str) if isinstance(date_str, str) else date_str
            
            if not date_obj:
                raise ValueError(f"Invalid date format: {date_str}")

            record, created = WaterIntake.objects.update_or_create(
                user=request.user, 
                date=date_obj,
                defaults={'glasses_count': glasses_count}
            )
            
            with open(log_file, "a") as f:
                f.write(f"\n[{datetime.now()}] WATER SUCCESS: glasses={record.glasses_count}")

            return Response({
                "message": "Water intake updated successfully",
                "date": str(record.date),
                "glasses_count": record.glasses_count
            }, status=status.HTTP_200_OK)
        except Exception as e:
            err_msg = traceback.format_exc()
            with open(log_file, "a") as f:
                f.write(f"\n[{datetime.now()}] WATER EXCEPTION: {err_msg}")
            return Response({'error': str(e), 'traceback': err_msg}, status=status.HTTP_400_BAD_REQUEST)
