class TestLike:
    def test_like_no_mutual(self, client, create_user, auth_headers):
        _, token1 = create_user(email="l1@test.com")
        user2, _ = create_user(email="l2@test.com")

        r = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["liked_user_id"] == user2.id
        assert data["is_match"] is False
        assert data["match_id"] is None

    def test_like_self_returns_400(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="self@test.com")
        r = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user1.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 400

    def test_duplicate_like_returns_409(self, client, create_user, auth_headers):
        _, token1 = create_user(email="dup1@test.com")
        user2, _ = create_user(email="dup2@test.com")

        client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        r = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 409


class TestPass:
    def test_pass_user(self, client, create_user, auth_headers):
        _, token1 = create_user(email="p1@test.com")
        user2, _ = create_user(email="p2@test.com")

        r = client.post(
            "/api/v1/matches/pass",
            json={"passed_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 200
        assert r.json()["passed_user_id"] == user2.id


class TestMutualMatch:
    def test_mutual_like_creates_match(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="m1@test.com")
        user2, token2 = create_user(email="m2@test.com")

        r1 = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r1.json()["is_match"] is False

        r2 = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user1.id},
            headers=auth_headers(token2),
        )
        assert r2.json()["is_match"] is True
        assert r2.json()["match_id"] is not None

    def test_list_matches(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="lm1@test.com")
        user2, token2 = create_user(email="lm2@test.com")

        client.post("/api/v1/matches/like", json={"liked_user_id": user2.id}, headers=auth_headers(token1))
        client.post("/api/v1/matches/like", json={"liked_user_id": user1.id}, headers=auth_headers(token2))

        r = client.get("/api/v1/matches", headers=auth_headers(token1))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert len(data["matches"]) == 1
        assert data["matches"][0]["other_user"]["id"] == user2.id


class TestUnmatch:
    def test_unmatch_deletes_match(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="um1@test.com")
        user2, token2 = create_user(email="um2@test.com")

        client.post("/api/v1/matches/like", json={"liked_user_id": user2.id}, headers=auth_headers(token1))
        r = client.post("/api/v1/matches/like", json={"liked_user_id": user1.id}, headers=auth_headers(token2))
        match_id = r.json()["match_id"]

        r = client.delete(f"/api/v1/matches/{match_id}", headers=auth_headers(token1))
        assert r.status_code == 204

        r = client.get("/api/v1/matches", headers=auth_headers(token1))
        assert r.json()["total"] == 0

    def test_unmatch_nonexistent_returns_404(self, client, create_user, auth_headers):
        _, token1 = create_user(email="unf@test.com")
        r = client.delete("/api/v1/matches/nonexistent-id", headers=auth_headers(token1))
        assert r.status_code == 404
