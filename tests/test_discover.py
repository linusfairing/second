class TestDiscoverGate:
    def test_requires_completed_onboarding(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "noob@example.com",
            "password": "password123",
        })
        token = r.json()["access_token"]
        r = client.get("/api/v1/discover", headers=auth_headers(token))
        assert r.status_code == 403
        assert "onboarding" in r.json()["detail"].lower()


class TestDiscoverResults:
    def test_returns_matching_candidates(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="d1@test.com", gender="male", gender_preference='["female"]',
        )
        user2, _ = create_user(
            email="d2@test.com", gender="female", gender_preference='["male"]',
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        ids = [u["id"] for u in data["users"]]
        assert user2.id in ids

    def test_pagination(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="pg0@test.com", gender="male", gender_preference='["female"]',
        )
        for i in range(3):
            create_user(
                email=f"pg{i + 1}@test.com", gender="female", gender_preference='["male"]',
            )

        r = client.get("/api/v1/discover?limit=2&offset=0", headers=auth_headers(token1))
        assert r.status_code == 200
        data = r.json()
        assert len(data["users"]) == 2
        assert data["total"] == 3

        r2 = client.get("/api/v1/discover?limit=2&offset=2", headers=auth_headers(token1))
        assert len(r2.json()["users"]) == 1


class TestDiscoverExcludesInactive:
    def test_deactivated_user_not_in_discover(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="di1@test.com", gender="male", gender_preference='["female"]',
        )
        user2, token2 = create_user(
            email="di2@test.com", gender="female", gender_preference='["male"]',
        )

        # Deactivate user2
        client.post("/api/v1/account/deactivate", headers=auth_headers(token2))

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        assert r.status_code == 200
        ids = [u["id"] for u in r.json()["users"]]
        assert user2.id not in ids


class TestDiscoverFiltering:
    def test_filters_by_gender_preference(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="gf1@test.com", gender="male", gender_preference='["female"]',
        )
        # Male user - should NOT appear (user1 wants females)
        user_same, _ = create_user(
            email="gf2@test.com", gender="male", gender_preference='["male"]',
        )
        # Female user - should appear
        user_match, _ = create_user(
            email="gf3@test.com", gender="female", gender_preference='["male"]',
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_match.id in ids
        assert user_same.id not in ids

    def test_excludes_already_liked_users(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="el1@test.com", gender="male", gender_preference='["female"]',
        )
        user2, _ = create_user(
            email="el2@test.com", gender="female", gender_preference='["male"]',
        )

        # Like user2
        client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user2.id not in ids

    def test_bidirectional_gender_preference(self, client, create_user, auth_headers):
        """User should not see candidates who don't want to see them."""
        _, token1 = create_user(
            email="bgp1@test.com", gender="male", gender_preference='["female"]',
        )
        # Female who ONLY wants females - should NOT appear for male user
        user_no, _ = create_user(
            email="bgp2@test.com", gender="female", gender_preference='["female"]',
        )
        # Female who wants males - should appear
        user_yes, _ = create_user(
            email="bgp3@test.com", gender="female", gender_preference='["male"]',
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_yes.id in ids
        assert user_no.id not in ids

    def test_excludes_users_without_profile_setup(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="eps1@test.com", gender="male", gender_preference='["female"]',
        )
        # User without profile_setup_complete should not appear
        user_incomplete, _ = create_user(
            email="eps2@test.com", gender="female", gender_preference='["male"]',
            profile_setup_complete=False,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_incomplete.id not in ids

    def test_excludes_blocked_users(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="eb1@test.com", gender="male", gender_preference='["female"]',
        )
        user2, _ = create_user(
            email="eb2@test.com", gender="female", gender_preference='["male"]',
        )

        # Block user2
        client.post(
            "/api/v1/block",
            json={"blocked_user_id": user2.id},
            headers=auth_headers(token1),
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user2.id not in ids
