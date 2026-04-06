from django.urls import path
from .views import (
    health_check,
    db_check,
    SignupView,
    LoginView,
    LogoutView,
    MeView,
    ConversationSessionListCreateView,
    ConversationSessionDetailView,
    MessageListCreateView,
    AnalyzeView,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("db-check/", db_check, name="db-check"),

    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),

    path("sessions/", ConversationSessionListCreateView.as_view(), name="session-list-create"),
    path("sessions/<int:pk>/", ConversationSessionDetailView.as_view(), name="session-detail"),
    path("sessions/<int:session_id>/messages/", MessageListCreateView.as_view(), name="message-list-create"),
    path("sessions/<int:session_id>/analyze/", AnalyzeView.as_view(), name="session-analyze"),
]