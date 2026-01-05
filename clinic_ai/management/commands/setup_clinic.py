from django.core.management.base import BaseCommand
from clinic_ai.models import Doctor, ClinicInfo, Clinic, Appointment, DoctorAvailability

class Command(BaseCommand):
    help = 'Populate initial clinic data'

    def handle(self, *args, **kwargs):
        # Clear existing data to avoid confusion
        DoctorAvailability.objects.all().delete()
        Doctor.objects.all().delete()
        Clinic.objects.all().delete()
        Appointment.objects.all().delete()

        # Create Clinics
        dental_clinic, _ = Clinic.objects.get_or_create(
            name="عيادة الأسنان",
            location="الطابق الثاني، الجناح أ",
            description="نقدم جميع خدمات العناية بالأسنان واللثة."
        )
        pedia_clinic, _ = Clinic.objects.get_or_create(
            name="عيادة الأطفال",
            location="الطابق الأول، الجناح ب",
            description="رعاية صحية شاملة للأطفال من جميع الأعمار."
        )
        derma_clinic, _ = Clinic.objects.get_or_create(
            name="عيادة الجلدية",
            location="الطابق الثالث، الجناح ج",
            description="نقدم أرقى الخدمات التجميلية والعلاجية للجلد."
        )

        # Create Doctors
        doc_ahmed, _ = Doctor.objects.get_or_create(name="د. أحمد علي", specialty="جلدية", clinic=derma_clinic)
        doc_sara, _ = Doctor.objects.get_or_create(name="د. سارة محمد", specialty="أسنان", clinic=dental_clinic)
        doc_khaled, _ = Doctor.objects.get_or_create(name="د. خالد حسن", specialty="أطفال", clinic=pedia_clinic)

        # Create Availabilities (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
        from datetime import time
        # Ahmed: Sun, Mon, Wed (9 AM - 5 PM)
        for day in [6, 0, 2]:
            DoctorAvailability.objects.create(doctor=doc_ahmed, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0))
        
        # Sara: Tue, Thu (10 AM - 6 PM)
        for day in [1, 3]:
            DoctorAvailability.objects.create(doctor=doc_sara, day_of_week=day, start_time=time(10, 0), end_time=time(18, 0))
            
        # Khaled: Sat, Sun, Mon (12 PM - 8 PM)
        for day in [5, 6, 0]:
            DoctorAvailability.objects.create(doctor=doc_khaled, day_of_week=day, start_time=time(12, 0), end_time=time(20, 0))

        # Create Clinic Info
        ClinicInfo.objects.get_or_create(
            working_hours="من السبت إلى الخميس، 9 صباحاً - 9 مساءً",
            location="الرياض، حي العليا",
            phone="011-1234567"
        )

        self.stdout.write(self.style.SUCCESS('Successfully fixed and populated multi-clinic data with full availability schedules'))
