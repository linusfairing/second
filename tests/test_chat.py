from unittest.mock import MagicMock

from app.models.user import User


def _signup(client, db, email="chat@example.com"):
    r = client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "password123",
    })
    token = r.json()["access_token"]
    # Mark profile setup complete so chat isn't gated
    user = db.query(User).filter(User.email == email).first()
    user.profile_setup_complete = True
    db.commit()
    return token


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _set_ai_response(mock_openai, content):
    mock_openai.chat.completions.create.return_value.choices[0].message.content = content


class TestSendMessage:
    def test_returns_reply(self, client, db, mock_openai):
        token = _signup(client, db)
        r = client.post("/api/v1/chat", json={"message": "Hello!"}, headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert data["current_topic"] == "greeting"
        assert data["onboarding_status"] == "in_progress"

    def test_topic_advances_on_topic_complete(self, client, db, mock_openai):
        token = _signup(client, db)
        _set_ai_response(mock_openai, "Welcome! Great start. [TOPIC_COMPLETE]")

        r = client.post("/api/v1/chat", json={"message": "Hi"}, headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["current_topic"] == "interests"
        assert "[TOPIC_COMPLETE]" not in data["reply"]

    def test_profile_update_extracted(self, client, db, mock_openai):
        token = _signup(client, db)
        _set_ai_response(
            mock_openai,
            'Great values! [PROFILE_UPDATE]{"values": ["honesty", "loyalty"]}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
        )

        r = client.post(
            "/api/v1/chat", json={"message": "I value honesty"}, headers=_headers(token),
        )
        assert r.status_code == 200
        assert "[PROFILE_UPDATE]" not in r.json()["reply"]

        # Verify profile was updated via chat status
        r = client.get("/api/v1/chat/status", headers=_headers(token))
        assert r.json()["profile_completeness"] > 0


class TestOnboardingFlow:
    def test_full_flow_completes(self, client, db, mock_openai):
        token = _signup(client, db)
        headers = _headers(token)

        # Responses must align with topic flow:
        # greeting -> interests -> deeper_interests -> relationship_goals ->
        # dating_style -> life_goals -> communication_style -> summary
        responses = [
            'Hey! [TOPIC_COMPLETE]',
            'Cool. [PROFILE_UPDATE]{"interests": ["hiking", "cooking"]}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
            'Got it. [PROFILE_UPDATE]{"values": ["honesty"], "personality_traits": ["kind"], "conversation_highlights": ["loves solo hiking"]}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
            'Makes sense. [PROFILE_UPDATE]{"relationship_goals": "long-term", "deal_breakers": ["dishonesty"]}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
            'Nice. [PROFILE_UPDATE]{"dating_style": "spontaneous"}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
            'Cool. [PROFILE_UPDATE]{"life_goals": ["travel more"]}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
            'Got it. [PROFILE_UPDATE]{"communication_style": "direct"}[/PROFILE_UPDATE] [TOPIC_COMPLETE]',
            'All set. [PROFILE_UPDATE]{"bio": "Adventurous and direct."}[/PROFILE_UPDATE] [ONBOARDING_COMPLETE]',
        ]

        mock_resps = []
        for content in responses:
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = content
            mock_resps.append(resp)
        mock_openai.chat.completions.create.side_effect = mock_resps

        for i in range(len(responses)):
            r = client.post("/api/v1/chat", json={"message": f"msg {i}"}, headers=headers)
            assert r.status_code == 200

        assert r.json()["onboarding_status"] == "completed"

        # Verify status endpoint agrees
        r = client.get("/api/v1/chat/status", headers=headers)
        assert r.json()["onboarding_status"] == "completed"
        assert r.json()["profile_completeness"] == 1.0


class TestChatHistory:
    def test_returns_messages(self, client, db, mock_openai):
        token = _signup(client, db)
        headers = _headers(token)
        client.post("/api/v1/chat", json={"message": "Hello!"}, headers=headers)

        r = client.get("/api/v1/chat/history", headers=headers)
        assert r.status_code == 200
        messages = r.json()
        assert len(messages) >= 2
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles


class TestPostOnboardingGuard:
    def test_chat_rejected_after_onboarding_complete(self, client, create_user, auth_headers, mock_openai):
        # create_user fixture creates a user with onboarding already completed
        _, token = create_user(email="guard@test.com")
        r = client.post(
            "/api/v1/chat", json={"message": "Hello again"}, headers=auth_headers(token),
        )
        assert r.status_code == 400
        assert "already completed" in r.json()["detail"].lower()


class TestChatStatus:
    def test_initial_status(self, client, mock_openai):
        token = _signup_raw(client)
        r = client.get("/api/v1/chat/status", headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["onboarding_status"] == "in_progress"
        assert data["current_topic"] == "greeting"
        assert isinstance(data["topics_completed"], list)


def _signup_raw(client, email="chatstatus@example.com"):
    """Signup without marking profile_setup_complete — for status-only tests."""
    r = client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "password123",
    })
    return r.json()["access_token"]
