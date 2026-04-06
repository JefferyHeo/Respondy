from django.contrib import admin
from .models import ConversationSession, Message

admin.site.register(ConversationSession)
admin.site.register(Message)