from langchain.tools import tool
from clinic_ai.models import Doctor, ClinicInfo, Appointment, Clinic, DoctorAvailability
from django.db.models import Q
from datetime import datetime
from clinic_ai.context import current_user
from django.conf import settings
import os
import uuid
import openpyxl
from openpyxl.styles import Font as XLFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image, PageTemplate, BaseDocTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

# Register Arabic Fonts
try:
    pdfmetrics.registerFont(TTFont('Arabic', '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Arabic-Bold', '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf'))
except:
    pass

def fix_arabic(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

@tool
def list_clinics(query: str):
    """List all available clinics in the medical center."""
    clinics = Clinic.objects.all()
    return "\n".join([f"العيادة: {c.name}, الموقع: {c.location}" for c in clinics])

@tool
def list_all_doctors(query: str):
    """
    استرجاع قائمة بجميع الأطباء في المركز الطبي مع تخصصاتهم وعياداتهم.
    استخدم هذه الأداة عندما يطلب المستخدم تقريراً أو قائمة عامة لجميع الأطباء.
    """
    docs = Doctor.objects.select_related('clinic').all()
    if not docs.exists():
        return "لا يوجد أطباء مسجلون حالياً."
    
    results = []
    for d in docs:
        results.append({
            "اسم الطبيب": d.name,
            "التخصص": d.specialty,
            "العيادة": d.clinic.name if d.clinic else "غير محدد"
        })
    import json
    return json.dumps(results, ensure_ascii=False)

@tool
def get_doctor_availability(doctor_info: str):
    """
    البحث عن توافر الأطباء في المركز. 
    يمكنك البحث باستخدام: اسم الطبيب (مثلاً: 'د. أحمد')، أو التخصص (مثلاً: 'جلدية')، أو اسم العيادة (مثلاً: 'عيادة الأسنان').
    نصيحة: إذا لم تجد طبيباً، استخدم list_clinics أولاً لمعرفة أسماء العيادات الصحيحة.
    """
    parts = [p.strip() for p in doctor_info.replace('،', ',').split(',')]
    query = parts[0]
    clinic_name = parts[1] if len(parts) > 1 else None

    def search_with_keywords(model, search_query, extra_filter=None):
        words = search_query.split()
        q_obj = Q()
        for word in words:
            clean_word = word[2:] if word.startswith('ال') and len(word) > 3 else word
            # Handle specialty/name/clinic name in one go for doctors
            if model == Doctor:
                q_obj &= (Q(name__icontains=clean_word) | Q(specialty__icontains=clean_word) | Q(clinic__name__icontains=clean_word))
            else:
                q_obj &= Q(name__icontains=clean_word)
        
        results = model.objects.filter(q_obj)
        if extra_filter:
            results = results.filter(extra_filter)
        return results

    doctors = search_with_keywords(Doctor, query)
    if clinic_name:
        doctors = doctors.filter(clinic__name__icontains=clinic_name)

    if not doctors.exists():
        return "لا يوجد أطباء بهذا الوصف حالياً."
    
    results = []
    for doc in doctors:
        clinic_str = f"في {doc.clinic.name}" if doc.clinic else ""
        avail_list = doc.availabilities.all()
        if avail_list.exists():
            from datetime import timedelta
            now = datetime.now()
            days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
            sched_parts = []
            for a in avail_list:
                day_name = days_ar[a.day_of_week]
                # Calculate next 2 dates for this day_of_week
                upcoming_dates = []
                days_ahead = a.day_of_week - now.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                
                # Next occurrence
                next_date = now + timedelta(days=days_ahead)
                upcoming_dates.append(next_date.strftime('%Y-%m-%d'))
                # Occurrence after that
                second_date = next_date + timedelta(days=7)
                upcoming_dates.append(second_date.strftime('%Y-%m-%d'))
                
                dates_str = " (" + ", ".join(upcoming_dates) + ")"
                sched_parts.append(f"{day_name}: {a.start_time.strftime('%I:%M %p (%H:%M)')} - {a.end_time.strftime('%I:%M %p (%H:%M)')}{dates_str}")
            sched_str = " | ".join(sched_parts)
        else:
            sched_str = "لا توجد مواعيد محددة حالياً"
        
        results.append(f"الطبيب: {doc.name}, التخصص: {doc.specialty}, {clinic_str}, الجدول: {sched_str}")
    
    return "\n".join(results)

@tool
def get_clinic_general_info(query: str):
    """Get general clinic information like working hours, location, and phone."""
    info = ClinicInfo.objects.first()
    if not info:
        return "لا تتوفر معلومات عامة عن العيادة حالياً."
    
    return f"ساعات العمل: {info.working_hours}\nالموقع: {info.location}\nالهاتف: {info.phone}"

@tool
def book_appointment(appointment_info: str):
    """
    حجز موعد جديد للمريض. 
    المدخل يجب أن يكون سلسلة نصية تحتوي على: 'اسم العيادة، اسم الطبيب، التاريخ والوقت YYYY-MM-DD HH:MM'.
    مثال: 'عيادة الأسنان، د. سارة محمد، 2026-05-20 14:00'.
    ملاحظة هامة: لا تقرر بنفسك إذا كان الموظف متاحاً أم لا؛ اطلب الموعد دائماً ودع النظام يتحقق من الجدول. 4 مساءً هي 16:00 وهي موعد صالح دائماً إذا كان الطبيب متاحاً حتى 6 مساءً.
    تحذير: تأكد من أن الموعد في المستقبل وضمن ساعات العمل (9 ص - 9 م).
    """
    user = current_user.get()
    if user is None or not user.is_authenticated:
        return "يجب عليك تسجيل الدخول أولاً لحجز موعد. يرجى استخدام أزرار الدخول في الأعلى."
    
    try:
        parts = [p.strip() for p in appointment_info.replace('،', ',').split(',')]
        if len(parts) < 3:
            return "يرجى تقديم اسم العيادة، اسم الطبيب، والموعد (YYYY-MM-DD HH:MM)."
        
        cl_name, doc_name, date_str = parts[0], parts[1], parts[2]
        
        clinic = Clinic.objects.filter(name__icontains=cl_name).first()
        if not clinic:
            # Try keyword search for clinic
            words = cl_name.split()
            q_cl = Q()
            for w in words:
                cw = w[2:] if w.startswith('ال') and len(w) > 3 else w
                q_cl &= Q(name__icontains=cw)
            clinic = Clinic.objects.filter(q_cl).first()
            if not clinic:
                return f"لم يتم العثور على عيادة باسم '{cl_name}'."

        # Flexible doctor search
        words_doc = doc_name.split()
        q_doc = Q(clinic=clinic)
        for w in words_doc:
            cw = w[2:] if w.startswith('ال') and len(w) > 3 else w
            q_doc &= Q(name__icontains=cw)
        doctor = Doctor.objects.filter(q_doc).first()
        if not doctor:
            return f"لم يتم العثور على طبيب باسم '{doc_name}' في {clinic.name}."
        
        from datetime import datetime
        appt_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        
        # 1. Check if date is in the future
        if appt_date <= datetime.now():
            return "عذراً، يجب أن يكون الموعد في المستقبل. لا يمكن حجز مواعيد سابقة."
            
        # 2. Check if within working hours (9 AM - 9 PM)
        if appt_date.hour < 9 or appt_date.hour >= 21:
            return "عذراً، المواعيد المتاحة فقط من 9 صباحاً حتى 9 مساءً."

        # 3. Check doctor availability schedule
        # day_of_week in python is 0=Mon to 6=Sun, same as our choices
        day_val = appt_date.weekday()
        time_val = appt_date.time()
        
        available_slots = DoctorAvailability.objects.filter(
            doctor=doctor, 
            day_of_week=day_val,
            start_time__lte=time_val,
            end_time__gte=time_val
        )
        
        if not available_slots.exists():
            days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
            day_name_ar = days_ar[day_val]
            
            all_slots = DoctorAvailability.objects.filter(doctor=doctor, day_of_week=day_val)
            if all_slots.exists():
                slots_str = " | ".join([f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" for s in all_slots])
                return f"عذراً، {doctor.name} غير متاح في هذا الوقت. المواعيد المتاحة في يوم {day_name_ar} هي: {slots_str}."
            else:
                return f"عذراً، {doctor.name} لا يعمل في يوم {day_name_ar}. يرجى اختيار يوم آخر."

        appointment = Appointment.objects.create(
            user=user,
            clinic=clinic,
            doctor=doctor,
            appointment_date=appt_date
        )
        
        return f"تم حجز الموعد بنجاح في {clinic.name}! رقم الموعد: {appointment.id}. الموعد: {appt_date.strftime('%Y-%m-%d %H:%M')} مع {doctor.name}."
    except Exception as e:
        return f"حدث خطأ أثناء حجز الموعد: {str(e)}"

@tool
def list_user_appointments(query: str):
    """List appointments for the current user."""
    user = current_user.get()
    if user is None or not user.is_authenticated:
        return "يجب عليك تسجيل الدخول أولاً لعرض مواعيدك."
    
    appts = Appointment.objects.filter(user=user).order_by('-appointment_date')
    if not appts.exists():
        return "ليس لديك أي مواعيد محجوزة حالياً."
    
    results = []
    for appt in appts:
        results.append(f"موعد #{appt.id}: {appt.appointment_date} - {appt.doctor.name} - الحالة: {appt.get_status_display()}")
    
    return "\n".join(results)

@tool
def generate_excel_report(data_json: str):
    """
    إنشاء ملف Excel من البيانات المقدمة.
    يجب أن تكون المدخلات عبارة عن JSON يمثل قائمة من القواميس (List of Dictionaries).
    مثال: '[{"اسم المريض": "أحمد", "الموعد": "2026-01-01"}]'
    ستقوم هذه الأداة بحفظ الملف وإرجاع رابط التحميل.
    """
    import json
    try:
        data = json.loads(data_json)
        if not data or not isinstance(data, list):
            return "يجب أن تكون البيانات قائمة من القواميس."
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report"
        
        # Extract headers from the first row
        headers = list(data[0].keys())
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = XLFont(bold=True)
            
        # Add data rows
        for row_num, entry in enumerate(data, 2):
            for col_num, header in enumerate(headers, 1):
                ws.cell(row=row_num, column=col_num, value=str(entry.get(header, "")))
        
        # Save file to media root
        filename = f"report_{uuid.uuid4().hex[:8]}.xlsx"
        filepath = os.path.join(settings.MEDIA_ROOT, filename)
        wb.save(filepath)
        
        file_url = f"{settings.MEDIA_URL}{filename}"
        return f"تم إنشاء ملف Excel بنجاح. يمكنك تحميله من الرابط التالي: {file_url}"
    except Exception as e:
        return f"حدث خطأ أثناء إنشاء ملف Excel: {str(e)}"

@tool
def generate_pdf_report(data_json: str):
    """
    إنشاء ملف PDF استثنائي واحترافي بتصميم Dashboard حديث.
    يجب أن تكون المدخلات عبارة عن JSON يمثل قائمة من القواميس.
    """
    import json
    try:
        data = json.loads(data_json)
        if not data or not isinstance(data, list):
            return "يجب أن تكون البيانات قائمة من القواميس."
        
        filename = f"premium_report_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join(settings.MEDIA_ROOT, filename)
        logo_path = os.path.join(settings.MEDIA_ROOT, 'assets/logo.png')
        
        # Color Palette - Premium Navy & Cyan
        NAVY = colors.HexColor("#0F172A")
        LIGHT_NAVY = colors.HexColor("#1E293B")
        CYAN = colors.HexColor("#38BDF8")
        BG_LIGHT = colors.HexColor("#F8FAFC")
        
        class PremiumDoc(BaseDocTemplate):
            def __init__(self, filename, **kw):
                super().__init__(filename, **kw)
                frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height - 100, id='normal')
                self.addPageTemplates([PageTemplate(id='First', frames=frame, onPage=self.on_page)])

            def on_page(self, canvas, doc):
                canvas.saveState()
                # Background color for header
                canvas.setFillColor(NAVY)
                canvas.rect(0, A4[1]-120, A4[0], 120, fill=1)
                
                # Draw Logo if exists
                if os.path.exists(logo_path):
                    canvas.drawImage(logo_path, 40, A4[1]-100, width=80, height=80, mask='auto')
                
                # Header Text
                canvas.setFillColor(colors.white)
                canvas.setFont('Arabic-Bold', 22)
                canvas.drawRightString(A4[0]-40, A4[1]-60, fix_arabic("المركز الطبي الذكي"))
                canvas.setFont('Arabic', 10)
                canvas.drawRightString(A4[0]-40, A4[1]-85, fix_arabic("Smart Clinic Center - Premium AI Intelligence"))
                
                # Bottom Decorative Line
                canvas.setStrokeColor(CYAN)
                canvas.setLineWidth(3)
                canvas.line(40, A4[1]-120, A4[0]-40, A4[1]-120)
                
                # Footer
                canvas.setFillColor(colors.grey)
                canvas.setFont('Arabic', 9)
                canvas.drawString(40, 20, fix_arabic(f"تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d')}"))
                canvas.drawRightString(A4[0]-40, 20, fix_arabic(f"صفحة {canvas.getPageNumber()}"))
                canvas.restoreState()

        doc = PremiumDoc(filepath, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=140, bottomMargin=40)
        elements = []
        styles = getSampleStyleSheet()
        
        # Dashboard Style Title
        title_style = ParagraphStyle(
            'TitleDash',
            fontName='Arabic-Bold',
            fontSize=16,
            textColor=LIGHT_NAVY,
            spaceAfter=30,
            alignment=TA_RIGHT
        )
        elements.append(Paragraph(fix_arabic("تقرير تحليل البيانات والفرق الطبية"), title_style))
        
        # Summary Area (Mini Cards)
        summary_data = [
            [
                Paragraph(fix_arabic(f"إجمالي السجلات: {len(data)}"), ParagraphStyle('S1', fontName='Arabic', fontSize=12, textColor=NAVY)),
                Paragraph(fix_arabic("الحالة: تقرير رسمي"), ParagraphStyle('S2', fontName='Arabic', fontSize=12, textColor=colors.HexColor("#10B981"))) # Emerald
            ]
        ]
        summary_table = Table(summary_data, colWidths=[150, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 40))
        
        # Main Data Table
        headers = [fix_arabic(h) for h in list(data[0].keys())]
        table_data = [headers]
        for entry in data:
            row = [fix_arabic(str(entry.get(h, ""))) for h in list(data[0].keys())]
            table_data.append(row)
            
        main_table = Table(table_data, hAlign='CENTER', repeatRows=1)
        main_table.setStyle(TableStyle([
            # Modern Header
            ('BACKGROUND', (0, 0), (-1, 0), LIGHT_NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Arabic-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Subtle Body
            ('FONTNAME', (0, 1), (-1, -1), 'Arabic'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('GRID', (0, 0), (-1, -1), 0.1, colors.HexColor("#CBD5E1")),
            ('LINEBELOW', (0, 0), (-1, 0), 2, CYAN),
        ]))
        
        elements.append(main_table)
        elements.append(Spacer(1, 50))
        
        # Stamp / Signature Area
        stamp_style = ParagraphStyle('Stamp', fontName='Arabic', fontSize=10, textColor=colors.lightgrey, alignment=TA_CENTER)
        elements.append(Paragraph(fix_arabic("تمت المصادقة الرقمية بواسطة نظام ذكاء المركز الطبي"), stamp_style))
        
        doc.build(elements)
        
        file_url = f"{settings.MEDIA_URL}{filename}"
        return f"تم إنشاء تقرير PDF استثنائي بنجاح. يمكنك تحميله من الرابط التالي: {file_url}"
    except Exception as e:
        import traceback
        return f"حدث خطأ أثناء إنشاء ملف PDF الاستثنائي: {str(e)}\n{traceback.format_exc()}"
