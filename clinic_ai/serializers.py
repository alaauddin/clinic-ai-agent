from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Appointment, Doctor

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.ReadOnlyField(source='doctor.name')
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Appointment
        fields = ['id', 'user_name', 'doctor_name', 'appointment_date', 'status']
