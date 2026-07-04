from django.contrib import admin
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_datetime', 'name', 'phone_number', 'user_type', 'reminder_sent', 'taste_results', 'created_at')
    list_filter = ('reservation_datetime', 'user_type', 'reminder_sent')
    search_fields = ('name', 'phone_number')