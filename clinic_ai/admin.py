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
admin.site.register(Appointment)

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('doctor', 'day_of_week')

