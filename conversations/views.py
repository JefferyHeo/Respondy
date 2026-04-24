from django.http import JsonResponse
from django.contrib.auth import authenticate, get_user_model

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import (
    ConversationSession,
    CaptureRequest,
    ExtractedMessage,
    AnalysisResult,
)
from .serializers import (
    SignupSerializer,
    UserSerializer,
    ConversationSessionSerializer,
    ConversationSessionDetailSerializer,
    CaptureRequestSerializer,
    ExtractedMessageSerializer,
    AnalysisResultSerializer,
    get_tokens_for_user,
)
from .services import analyze_capture

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
            tokens = get_tokens_for_user(user)

            return Response({
                "success": True,
                "message": "signup successful",
                "data": {
                    "user": UserSerializer(user).data,
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                }
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
            tokens = get_tokens_for_user(user)

            return Response({
                "success": True,
                "message": "login successful",
                "data": {
                    "user": UserSerializer(user).data,
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                }
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "invalid username or password"
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
        return ConversationSession.objects.filter(user=self.request.user).order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationSessionDetailView(generics.RetrieveAPIView):
    serializer_class = ConversationSessionDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConversationSession.objects.filter(user=self.request.user)


class CaptureRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = CaptureRequestSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        session = ConversationSession.objects.filter(
            id=session_id,
            user=self.request.user
        ).first()

        if not session:
            raise PermissionDenied("해당 세션에 접근할 수 없습니다.")

        return CaptureRequest.objects.filter(session=session).order_by("-created_at")

    def perform_create(self, serializer):
        session_id = self.kwargs["session_id"]
        session = ConversationSession.objects.filter(
            id=session_id,
            user=self.request.user
        ).first()

        if not session:
            raise PermissionDenied("해당 세션에 접근할 수 없습니다.")

        serializer.save(session=session)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        capture = serializer.instance

        try:
            analyze_capture(capture)
        except Exception:
            pass

        data = CaptureRequestSerializer(capture, context=self.get_serializer_context()).data
        data["messages"] = ExtractedMessageSerializer(
            capture.extracted_messages.all(),
            many=True,
            context=self.get_serializer_context(),
        ).data
        data["analysis_results"] = AnalysisResultSerializer(
            capture.analysis_results.all(),
            many=True,
            context=self.get_serializer_context(),
        ).data
        return Response({
            "success": capture.processing_status == CaptureRequest.ProcessingStatus.COMPLETED,
            "data": data,
        }, status=status.HTTP_201_CREATED)


class ExtractedMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = ExtractedMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        capture_id = self.kwargs["capture_id"]
        capture = CaptureRequest.objects.filter(
            id=capture_id,
            session__user=self.request.user
        ).first()

        if not capture:
            raise PermissionDenied("해당 캡처에 접근할 수 없습니다.")

        return ExtractedMessage.objects.filter(capture_request=capture).order_by("message_order", "id")

    def perform_create(self, serializer):
        capture_id = self.kwargs["capture_id"]
        capture = CaptureRequest.objects.filter(
            id=capture_id,
            session__user=self.request.user
        ).first()

        if not capture:
            raise PermissionDenied("해당 캡처에 접근할 수 없습니다.")

        serializer.save(
            session=capture.session,
            capture_request=capture
        )


class AnalysisResultListCreateView(generics.ListCreateAPIView):
    serializer_class = AnalysisResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        capture_id = self.kwargs["capture_id"]
        capture = CaptureRequest.objects.filter(
            id=capture_id,
            session__user=self.request.user
        ).first()

        if not capture:
            raise PermissionDenied("해당 캡처에 접근할 수 없습니다.")

        return AnalysisResult.objects.filter(capture_request=capture).order_by("-created_at")

    def perform_create(self, serializer):
        capture_id = self.kwargs["capture_id"]
        capture = CaptureRequest.objects.filter(
            id=capture_id,
            session__user=self.request.user
        ).first()

        if not capture:
            raise PermissionDenied("해당 캡처에 접근할 수 없습니다.")

        serializer.save(
            session=capture.session,
            capture_request=capture
        )   
