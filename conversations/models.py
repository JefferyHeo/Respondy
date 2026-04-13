from django.db import models
from django.contrib.auth.models import User


class ConversationSession(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="conversation_sessions"
    )
    title = models.CharField(max_length=100)
    relation_type = models.CharField(max_length=30, blank=True)
    situation_type = models.CharField(max_length=30, blank=True)
    goal_type = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.title


class Message(models.Model):
    SENDER_CHOICES = [
        ("user", "나"),
        ("other", "상대"),
    ]

    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    order_index = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order_index", "id"]

    def __str__(self):
        return f"{self.session_id} - {self.sender_type} - {self.order_index}"


        