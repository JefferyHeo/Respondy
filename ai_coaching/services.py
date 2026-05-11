import requests
from django.conf import settings

from .models import AIChatMessage


GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RECENT_MESSAGE_LIMIT = 12
AI_CHAT_TIMEOUT_SECONDS = 10
AI_CHAT_MAX_OUTPUT_TOKENS = 120


class AIChatReplyGenerationError(Exception):
    def __init__(self, user_message, assistant_message, original_error):
        super().__init__("AI reply generation failed.")
        self.user_message = user_message
        self.assistant_message = assistant_message
        self.original_error = original_error


def generate_avatar_reply(chat_session, user_message):
    user_chat_message = AIChatMessage.objects.create(
        chat_session=chat_session,
        sender_type=AIChatMessage.SenderType.USER,
        content=user_message,
        status=AIChatMessage.MessageStatus.COMPLETED,
    )
    return generate_avatar_reply_for_message(chat_session, user_chat_message)


def generate_avatar_reply_for_message(chat_session, user_chat_message):
    try:
        payload = _build_gemini_payload(chat_session)
        response_data = _call_gemini(payload)
        reply = _extract_text_response(response_data)
    except Exception as exc:
        assistant_message = AIChatMessage.objects.create(
            chat_session=chat_session,
            sender_type=AIChatMessage.SenderType.ASSISTANT,
            content="",
            status=AIChatMessage.MessageStatus.FAILED,
            error_message=str(exc),
        )
        chat_session.save(update_fields=["updated_at"])
        raise AIChatReplyGenerationError(
            user_chat_message,
            assistant_message,
            exc,
        ) from exc

    assistant_message = AIChatMessage.objects.create(
        chat_session=chat_session,
        sender_type=AIChatMessage.SenderType.ASSISTANT,
        content=reply,
        status=AIChatMessage.MessageStatus.COMPLETED,
        raw_response=response_data,
    )

    chat_session.save(update_fields=["updated_at"])
    return user_chat_message, assistant_message


def _build_gemini_payload(chat_session):
    avatar = chat_session.avatar
    if not avatar:
        raise ValueError("AI chat session requires an avatar.")

    recent_messages = chat_session.messages.filter(
        status=AIChatMessage.MessageStatus.COMPLETED,
    ).exclude(content="").order_by("-created_at", "-id")[:RECENT_MESSAGE_LIMIT]
    conversation_history = "\n".join(
        f"{message.sender_type}: {message.content}"
        for message in reversed(list(recent_messages))
    )

    prompt = f"""
You are Respondy's avatar chat engine.
The user is practicing a real conversation with the avatar below.
Reply as the avatar, not as an assistant. Stay consistent with the avatar's relationship, personality, speech style, and background.
Use natural Korean unless the user's message strongly implies another language.
Do not mention that you are AI. Do not give analysis unless the user directly asks.
Reply like a real KakaoTalk message.
Keep it brief, usually 1-2 short Korean sentences.
Do not over-explain.
Do not sound like a counselor unless the user asks for advice.
If the relationship is awkward or distant, keep an appropriate distance.

Avatar:
- name: {avatar.name}
- age group: {avatar.age_group}
- current relationship: {avatar.current_relation}
- target relationship: {avatar.target_relation}
- relationship type: {avatar.relation_type}
- age: {avatar.age or "unknown"}
- gender: {avatar.gender}
- personality: {avatar.personality}
- speech style: {avatar.speech_style}
- background with user: {avatar.background}
- memo: {avatar.memo}

Current situation:
{chat_session.situation_context}

Conversation so far:
{conversation_history}

Return only the avatar's next message.
"""
    return {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}],
        }],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": AI_CHAT_MAX_OUTPUT_TOKENS,
        },
    }


def _call_gemini(payload):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    url = GEMINI_ENDPOINT.format(model=settings.GEMINI_MODEL)
    response = requests.post(
        url,
        params={"key": settings.GEMINI_API_KEY},
        json=payload,
        timeout=AI_CHAT_TIMEOUT_SECONDS,
    )
    if not response.ok:
        raise RuntimeError(
            f"Gemini API request failed with status {response.status_code}: "
            f"{response.text[:500]}"
        )
    return response.json()


def _extract_text_response(response_data):
    candidates = response_data.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("Gemini API returned an empty response.")
    return text
