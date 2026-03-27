from django.contrib import admin
from .models import FAQ, SupportTicket

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'created_at')
    list_editable = ('order',)
    search_fields = ('question', 'answer')

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'category', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('subject', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
