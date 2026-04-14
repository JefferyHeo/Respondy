from django.contrib import admin
from .models import (
    ConversationSession,
    CaptureRequest,
    ExtractedMessage,
    AnalysisResult,
)


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "user", "platform_type", "contact_name",
        "relation_type", "goal_type", "status", "updated_at"
    )
    list_filter = ("platform_type", "relation_type", "goal_type", "status")
    search_fields = ("title", "contact_name", "conversation_key", "user__username")
    ordering = ("-updated_at",)


@admin.register(CaptureRequest)
class CaptureRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "session", "source_type", "processing_status",
        "uploaded_at", "processing_started_at", "processing_completed_at"
    )
    list_filter = ("source_type", "processing_status")
    search_fields = ("session__title", "image_url")
    ordering = ("-created_at",)


@admin.register(ExtractedMessage)
class ExtractedMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id", "session", "capture_request", "sender_type",
        "message_order", "confidence_score", "extracted_at"
    )
    list_filter = ("sender_type",)
    search_fields = ("content", "session__title")
    ordering = ("capture_request", "message_order")


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = (
        "id", "session", "capture_request", "emotion",
        "tone", "risk_level", "model_name", "created_at"
    )
    list_filter = ("emotion", "tone", "risk_level")
    search_fields = ("summary", "strategy", "session__title")
    ordering = ("-created_at",)