class TestBlockUser:
    def test_block_user(self, client, create_user, auth_headers):
        _, token1 = create_user(email="b1@test.com")
        user2, _ = create_user(email="b2@test.com")

        r = client.post(
            "/api/v1/block",
            json={"blocked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["blocked_user_id"] == user2.id
        assert data["auto_unmatched"] is False

    def test_block_self_returns_400(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="bs@test.com")
        r = client.post(
            "/api/v1/block",
            json={"blocked_user_id": user1.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 400

    def test_block_already_blocked_returns_409(self, client, create_user, auth_headers):
        _, token1 = create_user(email="bb1@test.com")
        user2, _ = create_user(email="bb2@test.com")

        client.post("/api/v1/block", json={"blocked_user_id": user2.id}, headers=auth_headers(token1))
        r = client.post("/api/v1/block", json={"blocked_user_id": user2.id}, headers=auth_headers(token1))
        assert r.status_code == 409


class TestBlockAutoUnmatch:
    def test_blocking_auto_unmatches(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="au1@test.com")
        user2, token2 = create_user(email="au2@test.com")

        # Create a match
        client.post("/api/v1/matches/like", json={"liked_user_id": user2.id}, headers=auth_headers(token1))
        client.post("/api/v1/matches/like", json={"liked_user_id": user1.id}, headers=auth_headers(token2))

        # Verify match exists
        r = client.get("/api/v1/matches", headers=auth_headers(token1))
        assert r.json()["total"] == 1

        # Block -> should auto-unmatch
        r = client.post(
            "/api/v1/block",
            json={"blocked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 201
        assert r.json()["auto_unmatched"] is True

        # Match should be gone
        r = client.get("/api/v1/matches", headers=auth_headers(token1))
        assert r.json()["total"] == 0


class TestUnblock:
    def test_unblock_user(self, client, create_user, auth_headers):
        _, token1 = create_user(email="ub1@test.com")
        user2, _ = create_user(email="ub2@test.com")

        client.post("/api/v1/block", json={"blocked_user_id": user2.id}, headers=auth_headers(token1))
        r = client.delete(f"/api/v1/block/{user2.id}", headers=auth_headers(token1))
        assert r.status_code == 204

    def test_unblock_nonexistent_returns_404(self, client, create_user, auth_headers):
        _, token1 = create_user(email="unf@test.com")
        r = client.delete("/api/v1/block/fake-id", headers=auth_headers(token1))
        assert r.status_code == 404


class TestListBlocked:
    def test_list_blocked_users(self, client, create_user, auth_headers):
        _, token1 = create_user(email="lb1@test.com")
        user2, _ = create_user(email="lb2@test.com")
        user3, _ = create_user(email="lb3@test.com")

        client.post("/api/v1/block", json={"blocked_user_id": user2.id}, headers=auth_headers(token1))
        client.post("/api/v1/block", json={"blocked_user_id": user3.id}, headers=auth_headers(token1))

        r = client.get("/api/v1/block", headers=auth_headers(token1))
        assert r.status_code == 200
        blocked = r.json()
        assert len(blocked) == 2
        blocked_ids = [b["blocked_user_id"] for b in blocked]
        assert user2.id in blocked_ids
        assert user3.id in blocked_ids
