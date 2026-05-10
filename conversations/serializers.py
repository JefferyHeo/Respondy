from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Avatar,
    ConversationSession,
    CaptureRequest,
    ExtractedMessage,
    AnalysisResult,
)


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"]
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("현재 비밀번호가 올바르지 않습니다.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({
                "new_password_confirm": "새 비밀번호가 일치하지 않습니다."
            })
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class AvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avatar
        fields = [
            "id",
            "name",
            "age_group",
            "current_relation",
            "target_relation",
            "relation_type",
            "age",
            "gender",
            "personality",
            "speech_style",
            "background",
            "memo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class CaptureRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaptureRequest
        fields = [
            "id",
            "session",
            "image_url",
            "image_file",
            "image_base64",
            "source_type",
            "processing_status",
            "detected_at",
            "uploaded_at",
            "processing_started_at",
            "processing_completed_at",
            "error_message",
            "gemini_extract_raw",
            "gemini_analyze_raw",
            "screen_context",
            "retry_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "session",
            "uploaded_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "image_base64": {"write_only": True},
        }

    def validate(self, attrs):
        has_image = attrs.get("image_url") or attrs.get("image_file") or attrs.get("image_base64")
        if not has_image and not self.instance:
            raise serializers.ValidationError(
                "image_url, image_file, image_base64 중 하나는 필요합니다."
            )
        return attrs


class ExtractedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedMessage
        fields = [
            "id",
            "capture_request",
            "session",
            "sender_type",
            "content",
            "message_order",
            "confidence_score",
            "raw_metadata",
            "extracted_at",
        ]
        read_only_fields = ["id", "capture_request", "session", "extracted_at"]


class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = [
            "id",
            "session",
            "capture_request",
            "summary",
            "emotion",
            "tone",
            "risk_level",
            "strategy",
            "recommended_replies",
            "caution_points",
            "follow_up_suggestions",
            "model_name",
            "raw_result",
            "created_at",
        ]
        read_only_fields = ["id", "session", "capture_request", "created_at"]


class ManualAnalysisRequestSerializer(serializers.Serializer):
    avatar_id = serializers.PrimaryKeyRelatedField(
        source="avatar",
        queryset=Avatar.objects.none(),
        required=True,
    )
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    platform_type = serializers.ChoiceField(
        choices=ConversationSession.PlatformType.choices,
        default=ConversationSession.PlatformType.UNKNOWN,
        required=False,
    )
    goal_type = serializers.ChoiceField(
        choices=ConversationSession.GoalType.choices,
        default=ConversationSession.GoalType.GENERAL,
        required=False,
    )
    situation_context = serializers.CharField(required=False, allow_blank=True)
    analysis_goal = serializers.CharField(required=False, allow_blank=True)
    received_message = serializers.CharField(required=True, allow_blank=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields["avatar_id"].queryset = Avatar.objects.filter(user=request.user)


class ConversationSessionSerializer(serializers.ModelSerializer):
    avatar = AvatarSerializer(read_only=True)
    avatar_id = serializers.PrimaryKeyRelatedField(
        source="avatar",
        queryset=Avatar.objects.none(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields["avatar_id"].queryset = Avatar.objects.filter(user=request.user)

    class Meta:
        model = ConversationSession
        fields = [
            "id",
            "avatar",
            "avatar_id",
            "title",
            "platform_type",
            "contact_name",
            "conversation_key",
            "relation_type",
            "relationship_context",
            "goal_type",
            "analysis_goal",
            "situation_context",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ConversationSessionDetailSerializer(serializers.ModelSerializer):
    avatar = AvatarSerializer(read_only=True)
    captures = CaptureRequestSerializer(many=True, read_only=True)
    analysis_results = AnalysisResultSerializer(many=True, read_only=True)

    class Meta:
        model = ConversationSession
        fields = [
            "id",
            "avatar",
            "title",
            "platform_type",
            "contact_name",
            "conversation_key",
            "relation_type",
            "relationship_context",
            "goal_type",
            "analysis_goal",
            "situation_context",
            "status",
            "created_at",
            "updated_at",
            "captures",
            "analysis_results",
        ]
