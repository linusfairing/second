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
        assert r.json()["detail"] == "Registration failed"

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
