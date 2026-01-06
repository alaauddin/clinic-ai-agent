from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Clinic)
class DoctorAvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 1

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'clinic')
    inlines = [DoctorAvailabilityInline]

admin.site.register(ClinicInfo)
admin.site.register(ChatLog)
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'user', 'doctor', 'appointment_date', 'status')
    list_filter = ('status', 'appointment_date', 'doctor')
    search_fields = ('patient_name', 'patient_phone', 'patient_email', 'user__username')
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_name', 'patient_dob', 'patient_phone', 'patient_email')
        }),
        ('Appointment Details', {
            'fields': ('user', 'clinic', 'doctor', 'appointment_date', 'status')
        }),
    )

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('doctor', 'day_of_week')

