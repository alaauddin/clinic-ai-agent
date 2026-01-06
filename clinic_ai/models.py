from django.db import models
from django.contrib.auth.models import User

class Clinic(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name

class Doctor(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='doctors', null=True, blank=True)
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.specialty}) - {self.clinic.name if self.clinic else 'No Clinic'}"

class DoctorAvailability(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.doctor.name} - {self.get_day_of_week_display()} ({self.start_time} to {self.end_time})"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # New Fields
    patient_name = models.CharField(max_length=150, blank=True)
    patient_dob = models.DateField(null=True, blank=True)
    patient_phone = models.CharField(max_length=20, blank=True)
    patient_email = models.EmailField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.patient_name if self.patient_name else self.user.username
        return f"{name} at {self.clinic.name if self.clinic else 'N/A'} - {self.doctor.name} on {self.appointment_date}"

class ClinicInfo(models.Model):
    # This might become redundant or serve as "Center Information"
    working_hours = models.TextField()
    location = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)

    class Meta:
        verbose_name_plural = "Clinic Info"

    def __str__(self):
        return "Center General Information"

class ChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_logs', null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat by {self.user.username if self.user else 'Guest'} at {self.created_at}"
