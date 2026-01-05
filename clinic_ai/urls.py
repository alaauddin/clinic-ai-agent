from django.urls import path
from django.views.generic import TemplateView
from .views import ChatAPIView, SignupView, LoginView, LogoutView, ChatHistoryView, ChatMessagesView, landing_view, chat_ui_view, dashboard_view, appointments_view

urlpatterns = [
    path('', landing_view, name='landing'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('appointments/', appointments_view, name='appointments'),
    path('chat/', chat_ui_view, name='chat-ui'),
    path('api/chat/', ChatAPIView.as_view(), name='api-chat'),
    path('api/signup/', SignupView.as_view(), name='api-signup'),
    path('api/login/', LoginView.as_view(), name='api-login'),
    path('api/logout/', LogoutView.as_view(), name='api-logout'),
    path('api/history/', ChatHistoryView.as_view(), name='api-history'),
    path('api/history/<str:session_id>/', ChatMessagesView.as_view(), name='api-messages'),
]
