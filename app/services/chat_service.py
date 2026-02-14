import json
import logging
import threading

from fastapi import HTTPException, status
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import ConversationMessage, ConversationState
from app.models.profile import UserProfile
from app.models.user import User

logger = logging.getLogger(__name__)

ONBOARDING_COMPLETED = "completed"
MAX_CONVERSATION_MESSAGES = 200

_openai_client = None
_openai_lock = threading.Lock()


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        with _openai_lock:
            if _openai_client is None:
                _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

TOPICS = [
    "interests",
    "deeper_interests",
    "relationship_goals",
    "dating_style",
    "life_goals",
    "communication_style",
    "summary",
]

SYSTEM_PROMPT = """You are Mutual, a dating app AI helping users build their personality profile through conversation.

Current topic: {topic}

User's profile data:
{profile_context}

Reference their name, job, location naturally when relevant. Don't start from zero.

== PERSONALITY ==

You are a sharp friend who asks unexpectedly good questions. You are actually listening. You are not trying to impress, validate, or "optimize engagement."

You are NOT a therapist, customer support agent, or enthusiastic AI assistant.

== HARD RULES — NEVER DO THESE ==

- NEVER over-validate or compliment basic preferences. "I like pizza" does not deserve "That's awesome!"
- NEVER react positively to every answer by default.
- NEVER repeat or fully summarize what the user just said.
- NEVER use therapist or customer service phrases ("That's really interesting!", "Thanks for sharing that!", "I love that for you!").
- NEVER respond to every item in a list. Pick ONE thread and pull on it.
- NEVER default to enthusiastic tone.
- NEVER use generic filler adjectives: "interesting," "awesome," "great choice," "amazing," "fantastic."
- NEVER ask "how would your friends describe you" or anything that sounds like a job interview.
- NEVER exceed 2-3 sentences per message. HARD LIMIT. This is a text conversation, not an essay.

== TONE ==

- Socially intelligent and relaxed. Like texting someone sharp.
- Short, direct questions. Prefer specificity over abstraction.
- Occasional light skepticism or playful challenge. "Really? Golf AND pottery? That's a weird combo — how'd that happen?"
- Mild opinions sometimes — without dominating. "Honestly underrated" or "Bold take" is fine.
- Brief reactions are fine. Not everything needs expansion. Sometimes "Ha, fair enough" is the right response.
- Curiosity-driven, not performance-driven.

== TEASING ==

Teasing is allowed but must feel playful and low-stakes. Never mock or diminish. Use sparingly — early conversation should build intrigue, not friction.

== TOPIC GUIDELINES ==

- For "interests": The user has already been asked to list things they like. Their first message is their response. Don't react to everything — pick the most interesting one or two and ask a short follow-up.
- For "deeper_interests": Pull on one thread from what they said. Ask for a story, a recommendation, a specific memory. This is where you learn who they actually are.
- For "relationship_goals": What are they looking for? What matters in a partner? What are their deal-breakers? Don't make it heavy — keep it direct.
- For "dating_style": What's their idea of a perfect first date? Spontaneous or planner? What's a Sunday look like with someone they're seeing?
- For "life_goals": Where do they see themselves in a few years? Travel, settle down, start something? What's on the bucket list?
- For "communication_style": Big texter or not? Calls vs texts? Need space or constant contact?
- For "summary": Brief summary of what you learned. Highlight the most specific or memorable things — not generic praise. Let them know their profile is set.

== TOPIC TRANSITIONS ==

After 2-3 exchanges on a topic, move on naturally. Include [TOPIC_COMPLETE] at the end of the transition message. When all topics are done and you give the summary, include [ONBOARDING_COMPLETE].

== PROFILE EXTRACTION ==

Extract profile data in JSON when completing each topic:
[PROFILE_UPDATE]{{"key": "value"}}[/PROFILE_UPDATE]

Keys:
- "interests": list of strings
- "values": list of strings — infer from conversation, NEVER ask directly
- "personality_traits": list of strings — infer from how they talk, what they care about. NEVER ask directly.
- "relationship_goals": string description
- "deal_breakers": list of strings
- "dating_style": string description — ideal date, spontaneous vs planner
- "life_goals": list of strings — ambitions, bucket list
- "communication_style": string description
- "conversation_highlights": list of strings — specific memorable quotes, stories, or facts that make this person interesting. E.g. "Backpacked solo through Japan for 3 months" or "Secret pottery hobby." These get surfaced to potential matches as conversation starters.
- "bio": string — their elevator pitch, written for the summary topic
"""


def get_or_create_state(db: Session, user_id: str) -> ConversationState:
    state = db.query(ConversationState).filter(ConversationState.user_id == user_id).first()
    if not state:
        state = ConversationState(user_id=user_id, topics_completed=json.dumps([]))
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_conversation_history(
    db: Session, user_id: str, limit: int | None = None, offset: int = 0
) -> list[ConversationMessage]:
    q = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at)
    )
    if offset:
        q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()


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


_LIST_FIELDS = {"values", "interests", "personality_traits", "deal_breakers", "life_goals", "conversation_highlights"}
_STRING_FIELDS = {"relationship_goals", "communication_style", "bio", "dating_style"}
_MAX_LIST_ITEMS = 50
_MAX_STRING_LENGTH = 2000


def _validate_profile_value(key: str, value) -> str | None:
    """Validate and serialize a profile value from LLM output. Returns JSON/string or None."""
    if key in _LIST_FIELDS:
        if isinstance(value, list):
            # Ensure all items are strings and cap length
            cleaned = [str(v)[:200] for v in value[:_MAX_LIST_ITEMS] if v]
            return json.dumps(cleaned) if cleaned else None
        if isinstance(value, str):
            return json.dumps([value[:200]])
        return None
    if key in _STRING_FIELDS:
        if isinstance(value, str):
            return value[:_MAX_STRING_LENGTH]
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)[:_MAX_STRING_LENGTH]
        return str(value)[:_MAX_STRING_LENGTH]
    return None


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
        "deal_breakers": "deal_breakers",
        "life_goals": "life_goals",
        "dating_style": "dating_style",
        "conversation_highlights": "conversation_highlights",
        "bio": "bio",
    }

    for key, value in updates.items():
        if key in field_map:
            validated = _validate_profile_value(key, value)
            if validated is not None:
                setattr(profile, field_map[key], validated)

    # Calculate completeness
    fields = ["bio", "interests", "values", "personality_traits", "relationship_goals",
              "communication_style", "deal_breakers", "life_goals", "dating_style", "conversation_highlights"]
    filled = sum(1 for f in fields if getattr(profile, f, None) is not None)
    profile.profile_completeness = filled / len(fields)

    db.commit()


def _advance_topic(db: Session, state: ConversationState, ai_response: str) -> None:
    try:
        topics_completed = json.loads(state.topics_completed) if state.topics_completed else []
    except (json.JSONDecodeError, TypeError):
        topics_completed = []

    if "[TOPIC_COMPLETE]" in ai_response or "[ONBOARDING_COMPLETE]" in ai_response:
        if state.current_topic not in topics_completed:
            topics_completed.append(state.current_topic)
        state.topics_completed = json.dumps(topics_completed)

        # Move to next topic
        current_idx = TOPICS.index(state.current_topic) if state.current_topic in TOPICS else -1
        if current_idx + 1 < len(TOPICS):
            state.current_topic = TOPICS[current_idx + 1]

    if "[ONBOARDING_COMPLETE]" in ai_response:
        state.onboarding_status = ONBOARDING_COMPLETED

    db.commit()


_CONTROL_MARKERS = ["[PROFILE_UPDATE]", "[/PROFILE_UPDATE]", "[TOPIC_COMPLETE]", "[ONBOARDING_COMPLETE]"]


def _sanitize_user_message(message: str) -> str:
    """Strip control markers that could allow prompt injection."""
    sanitized = message
    for marker in _CONTROL_MARKERS:
        sanitized = sanitized.replace(marker, "")
    return sanitized.strip()


def _build_profile_context(db: Session, user_id: str) -> str:
    """Build a summary of the user's profile data for the chatbot to reference."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return "No profile data available yet."
    parts = []
    if user.display_name:
        parts.append(f"Name: {user.display_name}")
    if user.location:
        parts.append(f"Location: {user.location}")
    if user.home_town:
        parts.append(f"Home town: {user.home_town}")
    if user.job_title:
        parts.append(f"Job: {user.job_title}")
    if user.college_university:
        parts.append(f"College: {user.college_university}")
    if user.gender:
        parts.append(f"Gender: {user.gender}")
    if user.languages:
        try:
            langs = json.loads(user.languages) if isinstance(user.languages, str) else user.languages
            parts.append(f"Languages: {', '.join(langs)}")
        except (json.JSONDecodeError, TypeError):
            pass
    if user.religion:
        parts.append(f"Religion: {user.religion}")
    return "\n".join(parts) if parts else "No profile data available yet."


def process_message(db: Session, user_id: str, user_message: str, state: ConversationState | None = None) -> str:
    if state is None:
        state = get_or_create_state(db, user_id)

    # Sanitize to prevent prompt injection via control markers
    safe_message = _sanitize_user_message(user_message)

    # Save user message
    user_msg = ConversationMessage(
        user_id=user_id,
        role="user",
        content=safe_message,
        topic=state.current_topic,
    )
    db.add(user_msg)
    db.commit()

    # Build messages for OpenAI (cap history to avoid unbounded growth)
    profile_context = _build_profile_context(db, user_id)
    history = get_conversation_history(db, user_id)
    recent_history = history[-MAX_CONVERSATION_MESSAGES:]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(topic=state.current_topic, profile_context=profile_context)},
    ]
    for msg in recent_history:
        messages.append({"role": msg.role, "content": msg.content})

    # Call OpenAI
    client = _get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            max_completion_tokens=500,
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
    if not ai_content:
        logger.error("OpenAI returned empty content for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service returned an empty response. Please try again.",
        )

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
