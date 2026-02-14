from app.models.block import BlockedUser


def _create_match(client, create_user, auth_headers):
    user1, token1 = create_user(email="msg1@test.com")
    user2, token2 = create_user(email="msg2@test.com")

    client.post("/api/v1/matches/like", json={"liked_user_id": user2.id}, headers=auth_headers(token1))
    r = client.post("/api/v1/matches/like", json={"liked_user_id": user1.id}, headers=auth_headers(token2))
    match_id = r.json()["match_id"]

    return user1, token1, user2, token2, match_id


class TestMessageValidation:
    def test_too_long_message_returns_422(self, client, create_user, auth_headers):
        _, token1, _, _, match_id = _create_match(client, create_user, auth_headers)
        r = client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": "x" * 5001},
            headers=auth_headers(token1),
        )
        assert r.status_code == 422


class TestSendMessage:
    def test_send_message(self, client, create_user, auth_headers):
        _, token1, _, _, match_id = _create_match(client, create_user, auth_headers)

        r = client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": "Hey there!"},
            headers=auth_headers(token1),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["content"] == "Hey there!"
        assert data["match_id"] == match_id

    def test_send_to_nonexistent_match_returns_404(self, client, create_user, auth_headers):
        _, token1 = create_user(email="nfm@test.com")
        r = client.post(
            "/api/v1/matches/fake-id/messages",
            json={"content": "Hi"},
            headers=auth_headers(token1),
        )
        assert r.status_code == 404


class TestGetMessages:
    def test_returns_messages_in_order(self, client, create_user, auth_headers):
        _, token1, _, token2, match_id = _create_match(client, create_user, auth_headers)

        client.post(f"/api/v1/matches/{match_id}/messages", json={"content": "Hi"}, headers=auth_headers(token1))
        client.post(f"/api/v1/matches/{match_id}/messages", json={"content": "Hello"}, headers=auth_headers(token2))

        r = client.get(f"/api/v1/matches/{match_id}/messages", headers=auth_headers(token1))
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) == 2
        assert msgs[0]["content"] == "Hi"
        assert msgs[1]["content"] == "Hello"


class TestMessageBlockCheck:
    def test_blocked_user_cannot_message(self, client, create_user, auth_headers, db):
        user1, token1, user2, _, match_id = _create_match(client, create_user, auth_headers)

        # Insert block directly to keep the match intact for testing
        block = BlockedUser(blocker_id=user2.id, blocked_id=user1.id)
        db.add(block)
        db.commit()

        r = client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": "Hi"},
            headers=auth_headers(token1),
        )
        assert r.status_code == 403
        assert "blocked" in r.json()["detail"].lower()

    def test_blocked_user_cannot_read_messages(self, client, create_user, auth_headers, db):
        user1, token1, user2, token2, match_id = _create_match(client, create_user, auth_headers)

        # Send a message first
        client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": "Before block"},
            headers=auth_headers(token1),
        )

        # Block user1
        block = BlockedUser(blocker_id=user2.id, blocked_id=user1.id)
        db.add(block)
        db.commit()

        r = client.get(
            f"/api/v1/matches/{match_id}/messages",
            headers=auth_headers(token1),
        )
        assert r.status_code == 403


class TestMessageMatchMembership:
    def test_non_member_cannot_send_message(self, client, create_user, auth_headers):
        _, _, _, _, match_id = _create_match(client, create_user, auth_headers)
        _, token3 = create_user(email="nm1@test.com")

        r = client.post(
            f"/api/v1/matches/{match_id}/messages",
            json={"content": "Hi"},
            headers=auth_headers(token3),
        )
        assert r.status_code == 403

    def test_non_member_cannot_read_messages(self, client, create_user, auth_headers):
        _, _, _, _, match_id = _create_match(client, create_user, auth_headers)
        _, token3 = create_user(email="nm2@test.com")

        r = client.get(
            f"/api/v1/matches/{match_id}/messages",
            headers=auth_headers(token3),
        )
        assert r.status_code == 403
