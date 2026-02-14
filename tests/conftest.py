import json
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.user import User
from app.models.profile import UserProfile
from app.models.conversation import ConversationState
from app.services.auth_service import hash_password, create_access_token


@pytest.fixture()
def _test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield Session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(_test_db):
    session = _test_db()
    yield session
    session.close()


@pytest.fixture()
def client(_test_db):
    def _override():
        s = _test_db()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    from app.utils.rate_limiter import chat_rate_limiter, auth_rate_limiter, auth_ip_rate_limiter, message_rate_limiter
    for limiter in (chat_rate_limiter, auth_rate_limiter, auth_ip_rate_limiter, message_rate_limiter):
        if hasattr(limiter, "_requests"):
            limiter._requests.clear()


@pytest.fixture()
def mock_openai():
    mock_client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello! Tell me about yourself."
    mock_client.chat.completions.create.return_value = response
    with patch("app.services.chat_service._get_openai_client", return_value=mock_client):
        yield mock_client


@pytest.fixture()
def auth_headers():
    def _make(token):
        return {"Authorization": f"Bearer {token}"}
    return _make


def _create_onboarded_user(session, **kwargs):
    email = kwargs.get("email", "user@example.com")
    display_name = kwargs.get("display_name", "Test User")
    gender = kwargs.get("gender", "female")
    gender_preference = kwargs.get("gender_preference", '["male"]')
    location = kwargs.get("location", "New York")
    dob = kwargs.get("dob", date(1995, 6, 15))
    age_min = kwargs.get("age_min", 18)
    age_max = kwargs.get("age_max", 50)
    interests = kwargs.get("interests", '["hiking", "reading"]')
    values = kwargs.get("values", '["honesty", "kindness"]')

    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        display_name=display_name,
        gender=gender,
        gender_preference=gender_preference,
        location=location,
        date_of_birth=dob,
        age_range_min=age_min,
        age_range_max=age_max,
        height_inches=kwargs.get("height_inches", 68),
        home_town=kwargs.get("home_town", "Test City"),
        sexual_orientation=kwargs.get("sexual_orientation", "Straight"),
        job_title=kwargs.get("job_title", "Engineer"),
        college_university=kwargs.get("college_university", "Test University"),
        education_level=kwargs.get("education_level", "Bachelor's"),
        languages=kwargs.get("languages", '["English"]'),
        religion=kwargs.get("religion", "None"),
        children=kwargs.get("children", "No"),
        family_plans=kwargs.get("family_plans", "Not sure"),
        drinking=kwargs.get("drinking", "Socially"),
        smoking=kwargs.get("smoking", "Never"),
        marijuana=kwargs.get("marijuana", "Never"),
        drugs=kwargs.get("drugs", "Never"),
        hidden_fields=kwargs.get("hidden_fields", "[]"),
        profile_setup_complete=kwargs.get("profile_setup_complete", True),
    )
    session.add(user)
    session.flush()

    profile = UserProfile(
        user_id=user.id,
        bio="Test bio",
        interests=interests,
        values=values,
        personality_traits='["adventurous", "creative"]',
        relationship_goals="Long-term relationship",
        communication_style="Direct and open",
        profile_completeness=1.0,
    )
    session.add(profile)

    state = ConversationState(
        user_id=user.id,
        current_topic="summary",
        topics_completed=json.dumps([
            "greeting", "values", "relationship_goals",
            "interests", "personality", "communication_style", "summary",
        ]),
        onboarding_status="completed",
    )
    session.add(state)
    session.commit()
    session.refresh(user)

    token = create_access_token(user.id)
    return user, token


@pytest.fixture()
def create_user(db):
    def _create(**kwargs):
        return _create_onboarded_user(db, **kwargs)
    return _create
