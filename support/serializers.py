from rest_framework import serializers
from .models import FAQ, SupportTicket

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer']

class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['id', 'subject', 'message', 'category', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']
