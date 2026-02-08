import json
import logging

from fastapi import HTTPException, status
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import ConversationMessage, ConversationState
from app.models.profile import UserProfile

logger = logging.getLogger(__name__)

MAX_CONVERSATION_MESSAGES = 200

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

TOPICS = [
    "greeting",
    "values",
    "relationship_goals",
    "interests",
    "personality",
    "communication_style",
    "summary",
]

SYSTEM_PROMPT = """You are a friendly dating app AI assistant helping users build their personality profile.
You're having a natural conversation to learn about the user across several topics.
Be warm, engaging, and ask follow-up questions.

Current topic: {topic}

Topics to cover: values, relationship goals, interests, personality traits, communication style.

Guidelines:
- For "greeting": Welcome the user and ask them to tell you about themselves.
- For "values": Ask about what they value most in life and relationships.
- For "relationship_goals": Ask about what they're looking for in a partner and relationship.
- For "interests": Ask about hobbies, passions, and how they spend their time.
- For "personality": Ask about how friends would describe them, their social style.
- For "communication_style": Ask about how they prefer to communicate in relationships.
- For "summary": Summarize what you've learned and let them know their profile is complete.

When you feel a topic has been sufficiently explored (after 2-3 exchanges), naturally transition to the next topic.
When transitioning, include the marker [TOPIC_COMPLETE] at the end of your message.
When all topics are done and you give the summary, include [ONBOARDING_COMPLETE] at the end.

Also extract profile data in JSON when completing each topic. Include the marker:
[PROFILE_UPDATE]{{"key": "value"}}[/PROFILE_UPDATE]

Keys to extract:
- "values": list of strings for values topic
- "relationship_goals": string description for relationship_goals topic
- "interests": list of strings for interests topic
- "personality_traits": list of strings for personality topic
- "communication_style": string description for communication_style topic
- "bio": string summary for summary topic
"""


def get_or_create_state(db: Session, user_id: str) -> ConversationState:
    state = db.query(ConversationState).filter(ConversationState.user_id == user_id).first()
    if not state:
        state = ConversationState(user_id=user_id, topics_completed=json.dumps([]))
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_conversation_history(db: Session, user_id: str) -> list[ConversationMessage]:
    return (
        db.query(ConversationMessage)
        .filter(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at)
        .all()
    )


def _extract_profile_updates(content: str) -> dict:
    updates = {}
    marker_start = "[PROFILE_UPDATE]"
    marker_end = "[/PROFILE_UPDATE]"
    start = content.find(marker_start)
    while start != -1:
        end = content.find(marker_end, start)
        if end == -1:
            break
        json_str = content[start + len(marker_start):end]
        try:
            data = json.loads(json_str)
            updates.update(data)
        except json.JSONDecodeError:
            pass
        start = content.find(marker_start, end)
    return updates


def _clean_response(content: str) -> str:
    """Remove markers from the response shown to the user."""
    result = content
    # Remove PROFILE_UPDATE blocks
    while "[PROFILE_UPDATE]" in result:
        start = result.find("[PROFILE_UPDATE]")
        end = result.find("[/PROFILE_UPDATE]")
        if end == -1:
            break
        result = result[:start] + result[end + len("[/PROFILE_UPDATE]"):]
    # Remove other markers
    result = result.replace("[TOPIC_COMPLETE]", "").replace("[ONBOARDING_COMPLETE]", "")
    return result.strip()


def _apply_profile_updates(db: Session, user_id: str, updates: dict) -> None:
    if not updates:
        return

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    field_map = {
        "values": "values",
        "interests": "interests",
        "personality_traits": "personality_traits",
        "relationship_goals": "relationship_goals",
        "communication_style": "communication_style",
        "bio": "bio",
    }

    for key, value in updates.items():
        if key in field_map:
            attr = field_map[key]
            if isinstance(value, (list, dict)):
                setattr(profile, attr, json.dumps(value))
            else:
                setattr(profile, attr, str(value))

    # Calculate completeness
    fields = ["bio", "interests", "values", "personality_traits", "relationship_goals", "communication_style"]
    filled = sum(1 for f in fields if getattr(profile, f, None) is not None)
    profile.profile_completeness = filled / len(fields)

    db.commit()


def _advance_topic(db: Session, state: ConversationState, ai_response: str) -> None:
    topics_completed = json.loads(state.topics_completed) if state.topics_completed else []

    if "[TOPIC_COMPLETE]" in ai_response or "[ONBOARDING_COMPLETE]" in ai_response:
        if state.current_topic not in topics_completed:
            topics_completed.append(state.current_topic)
        state.topics_completed = json.dumps(topics_completed)

        # Move to next topic
        current_idx = TOPICS.index(state.current_topic) if state.current_topic in TOPICS else -1
        if current_idx + 1 < len(TOPICS):
            state.current_topic = TOPICS[current_idx + 1]

    if "[ONBOARDING_COMPLETE]" in ai_response:
        state.onboarding_status = "completed"

    db.commit()


def process_message(db: Session, user_id: str, user_message: str) -> str:
    state = get_or_create_state(db, user_id)

    # Save user message
    user_msg = ConversationMessage(
        user_id=user_id,
        role="user",
        content=user_message,
        topic=state.current_topic,
    )
    db.add(user_msg)
    db.commit()

    # Build messages for OpenAI (cap history to avoid unbounded growth)
    history = get_conversation_history(db, user_id)
    recent_history = history[-MAX_CONVERSATION_MESSAGES:]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(topic=state.current_topic)},
    ]
    for msg in recent_history:
        messages.append({"role": msg.role, "content": msg.content})

    # Call OpenAI
    client = _get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.8,
            timeout=30.0,
        )
    except OpenAIError as e:
        logger.error("OpenAI API call failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service is temporarily unavailable. Please try again.",
        )

    ai_content = response.choices[0].message.content

    # Extract and apply profile updates
    updates = _extract_profile_updates(ai_content)
    _apply_profile_updates(db, user_id, updates)

    # Capture the topic this response belongs to BEFORE advancing
    response_topic = state.current_topic

    # Advance topic if needed
    _advance_topic(db, state, ai_content)

    # Clean response for user
    clean_content = _clean_response(ai_content)

    # Save assistant message (clean version)
    assistant_msg = ConversationMessage(
        user_id=user_id,
        role="assistant",
        content=clean_content,
        topic=response_topic,
    )
    db.add(assistant_msg)
    db.commit()

    return clean_content
