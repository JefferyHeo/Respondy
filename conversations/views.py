from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout, get_user_model

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import ConversationSession, Message
from .serializers import (
    SignupSerializer,
    UserSerializer,
    ConversationSessionSerializer,
    ConversationSessionDetailSerializer,
    MessageSerializer,
)

User = get_user_model()


def health_check(request):
    return JsonResponse({
        "success": True,
        "message": "server is running"
    })


def db_check(request):
    user_count = User.objects.count()
    return JsonResponse({
        "success": True,
        "message": "database connection is working",
        "user_count": user_count
    })


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return Response({
                "success": True,
                "message": "signup successful",
                "data": UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "message": "signup failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({
                "success": True,
                "message": "login successful",
                "data": UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "invalid username or password"
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({
            "success": True,
            "message": "logout successful"
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "success": True,
            "data": UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)


class ConversationSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConversationSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationSessionDetailView(generics.RetrieveAPIView):
    serializer_class = ConversationSessionDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConversationSession.objects.filter(user=self.request.user)


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        return Message.objects.filter(
            session_id=session_id,
            session__user=self.request.user
        )

    def perform_create(self, serializer):
        session_id = self.kwargs["session_id"]
        session = ConversationSession.objects.get(
            id=session_id,
            user=self.request.user
        )
        serializer.save(session=session)


class AnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = ConversationSession.objects.get(
                id=session_id,
                user=request.user
            )
        except ConversationSession.DoesNotExist:
            return Response({
                "success": False,
                "message": "session not found"
            }, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(session=session)
        last_message = messages.last().content if messages.exists() else ""

        return Response({
            "success": True,
            "message": "analysis complete",
            "data": {
                "session_id": session.id,
                "summary": "상대의 감정을 신중하게 살피며 차분하게 답장하는 것이 좋아 보입니다.",
                "tone": "careful",
                "last_message": last_message,
                "recommended_replies": [
                    "답장이 늦어서 미안해. 일부러 그런 건 아니었어.",
                    "혹시 서운했다면 미안해. 네 기분을 더 듣고 싶어.",
                    "지금 괜찮다면 차분하게 이야기해보고 싶어."
                ]
            }
        }, status=status.HTTP_200_OK)