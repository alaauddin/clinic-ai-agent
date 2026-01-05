from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, authentication
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate, login, logout
from .serializers import UserSerializer, AppointmentSerializer
from .ai_engine.chains import get_ai_chat
from .models import ChatLog
from .context import current_user
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'clinic_ai/landing.html')

@login_required(login_url='/')
def chat_ui_view(request):
    return render(request, 'clinic_ai/chat.html')

@login_required(login_url='/')
def dashboard_view(request):
    from .models import Clinic, Doctor
    clinics = Clinic.objects.all()
    doctors = Doctor.objects.all().select_related('clinic')
    return render(request, 'clinic_ai/dashboard.html', {
        'clinics': clinics,
        'doctors': doctors
    })

@login_required(login_url='/')
def appointments_view(request):
    from .models import Appointment
    appointments = Appointment.objects.filter(user=request.user).order_by('appointment_date')
    return render(request, 'clinic_ai/appointments.html', {
        'appointments': appointments
    })

class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return Response({"message": "تم تسجيل الدخول بنجاح", "username": user.username})
        return Response({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "تم تسجيل الخروج"})

from langchain_core.messages import HumanMessage, AIMessage

@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(APIView):
    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get("query")
        session_id = request.data.get("session_id")
        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = request.user
            
            # Retrieve recent chat history for the user and specific session
            recent_logs = []
            if session_id:
                recent_logs = ChatLog.objects.filter(user=user, session_id=session_id).order_by('-created_at')[:20]
            
            chat_history = []
            # Reversed to get chronological order [oldest -> newest] for the AI
            for log in reversed(recent_logs):
                chat_history.append(HumanMessage(content=log.question))
                chat_history.append(AIMessage(content=log.answer))
            
            # Set user context for tools
            token = current_user.set(user)
            try:
                ai_chat = get_ai_chat()
                answer = ai_chat.ask(query, user=user, chat_history=chat_history)
            finally:
                current_user.reset(token)
            
            # Log the Q&A with the user and session linked
            ChatLog.objects.create(user=user, session_id=session_id, question=query, answer=answer)
            
            return Response({
                "status": "success",
                "answer": answer,
                "is_authenticated": True
            })
        except Exception as e:
            logger.error(f"Error in ChatAPIView: {str(e)}")
            return Response({
                "status": "error",
                "message": "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة لاحقاً."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        # Get unique sessions for this user, ordered by latest activity
        sessions = ChatLog.objects.filter(user=user).values('session_id').annotate(
            latest=models.Max('created_at'),
            title=models.Min('question') # Use first question as title
        ).order_by('-latest')
        
        return Response(list(sessions))

class ChatMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, session_id):
        user = request.user
        messages = ChatLog.objects.filter(user=user, session_id=session_id).order_by('created_at')
        result = []
        for msg in messages:
            result.append({"type": "human", "text": msg.question})
            result.append({"type": "ai", "text": msg.answer})
        return Response(result)
