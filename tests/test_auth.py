class TestRateLimiting:
    def test_auth_rate_limit(self, client):
        # Auth endpoints have 10 req/min per email
        for i in range(10):
            client.post("/api/v1/auth/login", json={
                "email": "ratelimit@example.com",
                "password": "wrong",
            })

        r = client.post("/api/v1/auth/login", json={
            "email": "ratelimit@example.com",
            "password": "wrong",
        })
        assert r.status_code == 429
        assert "rate limit" in r.json()["detail"].lower()


class TestSignup:
    def test_success(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "new@example.com",
            "password": "password123",
        })
        assert r.status_code == 201
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"]
        assert data["is_active"] is True

    def test_duplicate_email_returns_409(self, client):
        payload = {"email": "dup@example.com", "password": "password123"}
        client.post("/api/v1/auth/signup", json=payload)
        r = client.post("/api/v1/auth/signup", json=payload)
        assert r.status_code == 409
        assert r.json()["detail"] == "An account with this email already exists"

    def test_short_password_returns_422(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "short@example.com",
            "password": "short",
        })
        assert r.status_code == 422


class TestLogin:
    def test_success(self, client):
        client.post("/api/v1/auth/signup", json={
            "email": "login@example.com",
            "password": "password123",
        })
        r = client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "password123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["is_active"] is True

    def test_wrong_password_returns_401(self, client):
        client.post("/api/v1/auth/signup", json={
            "email": "wrong@example.com",
            "password": "password123",
        })
        r = client.post("/api/v1/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword",
        })
        assert r.status_code == 401

    def test_nonexistent_email_returns_401(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "nope@example.com",
            "password": "password123",
        })
        assert r.status_code == 401


class TestAccountDeletion:
    def test_delete_account(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "del1@example.com",
            "password": "password123",
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.delete("/api/v1/account", headers=headers)
        assert r.status_code == 204

        # Token should no longer work (user deleted)
        r = client.get("/api/v1/profile/me", headers=headers)
        assert r.status_code == 401

    def test_delete_account_cascades_matches(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="del2@test.com")
        user2, token2 = create_user(email="del3@test.com")

        # Create a match with messages
        client.post("/api/v1/matches/like", json={"liked_user_id": user2.id}, headers=auth_headers(token1))
        r = client.post("/api/v1/matches/like", json={"liked_user_id": user1.id}, headers=auth_headers(token2))
        match_id = r.json()["match_id"]
        client.post(f"/api/v1/matches/{match_id}/messages", json={"content": "Hi"}, headers=auth_headers(token1))

        # Delete user1's account
        r = client.delete("/api/v1/account", headers=auth_headers(token1))
        assert r.status_code == 204

        # User2 should no longer see the match
        r = client.get("/api/v1/matches", headers=auth_headers(token2))
        assert r.json()["total"] == 0

    def test_deactivated_user_can_delete(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "del4@example.com",
            "password": "password123",
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/account/deactivate", headers=headers)

        # Deactivated users should still be able to delete
        r = client.delete("/api/v1/account", headers=headers)
        assert r.status_code == 204


class TestTokenInvalidation:
    def test_token_issued_before_invalidation_is_rejected(self, client, db, auth_headers):
        from datetime import datetime, timezone, timedelta
        from app.models.user import User
        from app.services.auth_service import create_access_token

        r = client.post("/api/v1/auth/signup", json={
            "email": "inv1@example.com",
            "password": "password123",
        })
        old_token = r.json()["access_token"]
        user_id = r.json()["user_id"]

        # Set token_invalidated_at to 1 second in the future so both old and new-in-same-second tokens are rejected
        # Then test that a token issued after that is accepted
        import time
        user = db.query(User).filter(User.id == user_id).first()
        user.token_invalidated_at = datetime.now(timezone.utc)
        db.commit()

        # Old token should be rejected (iat <= invalidated_at)
        r = client.get("/api/v1/profile/me", headers=auth_headers(old_token))
        assert r.status_code == 401
        assert "revoked" in r.json()["detail"].lower()

        # Set invalidation to 2 seconds in the past so a newly-issued token has iat > invalidated_at
        user.token_invalidated_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        db.commit()

        new_token = create_access_token(user_id)
        r = client.get("/api/v1/profile/me", headers=auth_headers(new_token))
        assert r.status_code == 200


class TestEmailCaseInsensitive:
    def test_login_with_different_case(self, client):
        client.post("/api/v1/auth/signup", json={
            "email": "CaseTest@Example.COM",
            "password": "password123",
        })
        r = client.post("/api/v1/auth/login", json={
            "email": "casetest@example.com",
            "password": "password123",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_duplicate_signup_different_case(self, client):
        client.post("/api/v1/auth/signup", json={
            "email": "DupCase@Example.COM",
            "password": "password123",
        })
        r = client.post("/api/v1/auth/signup", json={
            "email": "dupcase@example.com",
            "password": "password123",
        })
        assert r.status_code == 409


class TestDeactivatedUser:
    def test_deactivated_user_gets_403(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "deact@example.com",
            "password": "password123",
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Deactivate
        client.post("/api/v1/account/deactivate", headers=headers)

        # Any normal endpoint should return 403
        r = client.get("/api/v1/discover", headers=headers)
        assert r.status_code == 403
        assert "deactivated" in r.json()["detail"].lower()

    def test_deactivated_user_can_check_status(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "deact2@example.com",
            "password": "password123",
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/account/deactivate", headers=headers)

        r = client.get("/api/v1/account/status", headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_deactivated_user_can_reactivate(self, client):
        r = client.post("/api/v1/auth/signup", json={
            "email": "deact3@example.com",
            "password": "password123",
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/api/v1/account/deactivate", headers=headers)

        r = client.post("/api/v1/account/reactivate", headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is True
