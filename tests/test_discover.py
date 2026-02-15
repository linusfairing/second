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


class TestDiscoverDistanceFiltering:
    def test_filters_out_far_users(self, client, create_user, auth_headers):
        """User in NYC should not see user in LA with 50km max distance."""
        _, token1 = create_user(
            email="dist1@test.com", gender="male", gender_preference='["female"]',
            latitude=40.7128, longitude=-74.0060, max_distance_km=50,
        )
        user_far, _ = create_user(
            email="dist2@test.com", gender="female", gender_preference='["male"]',
            latitude=34.0522, longitude=-118.2437,
        )
        user_near, _ = create_user(
            email="dist3@test.com", gender="female", gender_preference='["male"]',
            latitude=40.7580, longitude=-73.9855,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_near.id in ids
        assert user_far.id not in ids

    def test_distance_shown_on_card(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="distd1@test.com", gender="male", gender_preference='["female"]',
            latitude=40.7128, longitude=-74.0060, max_distance_km=100,
        )
        user2, _ = create_user(
            email="distd2@test.com", gender="female", gender_preference='["male"]',
            latitude=40.7580, longitude=-73.9855,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        found = [u for u in r.json()["users"] if u["id"] == user2.id]
        assert len(found) == 1
        assert found[0]["distance_km"] is not None
        assert found[0]["distance_km"] < 10

    def test_user_without_gps_still_visible(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="nogps1@test.com", gender="male", gender_preference='["female"]',
            latitude=40.7128, longitude=-74.0060,
        )
        user_no_gps, _ = create_user(
            email="nogps2@test.com", gender="female", gender_preference='["male"]',
            latitude=None, longitude=None,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_no_gps.id in ids

    def test_searcher_without_gps_sees_everyone(self, client, create_user, auth_headers):
        _, token1 = create_user(
            email="nogps3@test.com", gender="male", gender_preference='["female"]',
            latitude=None, longitude=None,
        )
        user_far, _ = create_user(
            email="nogps4@test.com", gender="female", gender_preference='["male"]',
            latitude=34.0522, longitude=-118.2437,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_far.id in ids

    def test_user_at_boundary_included(self, client, create_user, auth_headers):
        """User within max distance should be included."""
        _, token1 = create_user(
            email="bnd1@test.com", gender="male", gender_preference='["female"]',
            latitude=40.0, longitude=-74.0, max_distance_km=100,
        )
        # ~85km north (within 100km)
        user_in, _ = create_user(
            email="bnd2@test.com", gender="female", gender_preference='["male"]',
            latitude=40.77, longitude=-74.0,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_in.id in ids


class TestDiscoverHeightFiltering:
    def test_height_pref_filters_candidates(self, client, create_user, auth_headers):
        """User with height pref 60-72 should see 66" candidate, not 58"."""
        _, token1 = create_user(
            email="hf1@test.com", gender="male", gender_preference='["female"]',
            height_pref_min=60, height_pref_max=72,
        )
        user_in, _ = create_user(
            email="hf2@test.com", gender="female", gender_preference='["male"]',
            height_inches=66,
        )
        user_out, _ = create_user(
            email="hf3@test.com", gender="female", gender_preference='["male"]',
            height_inches=58,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_in.id in ids
        assert user_out.id not in ids

    def test_no_height_pref_sees_everyone(self, client, create_user, auth_headers):
        """User with no height preference should see all candidates."""
        _, token1 = create_user(
            email="hf4@test.com", gender="male", gender_preference='["female"]',
        )
        user_short, _ = create_user(
            email="hf5@test.com", gender="female", gender_preference='["male"]',
            height_inches=50,
        )
        user_tall, _ = create_user(
            email="hf6@test.com", gender="female", gender_preference='["male"]',
            height_inches=80,
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_short.id in ids
        assert user_tall.id in ids


class TestDiscoverReligionFiltering:
    def test_religion_pref_filters_candidates(self, client, create_user, auth_headers):
        """User with religion pref [Christian, Catholic] sees Catholic, not Muslim."""
        import json
        _, token1 = create_user(
            email="rf1@test.com", gender="male", gender_preference='["female"]',
            religion_preference=json.dumps(["Christian", "Catholic"]),
        )
        user_in, _ = create_user(
            email="rf2@test.com", gender="female", gender_preference='["male"]',
            religion="Catholic",
        )
        user_out, _ = create_user(
            email="rf3@test.com", gender="female", gender_preference='["male"]',
            religion="Muslim",
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_in.id in ids
        assert user_out.id not in ids

    def test_no_religion_pref_sees_everyone(self, client, create_user, auth_headers):
        """User with no religion preference sees all candidates."""
        _, token1 = create_user(
            email="rf4@test.com", gender="male", gender_preference='["female"]',
        )
        user_a, _ = create_user(
            email="rf5@test.com", gender="female", gender_preference='["male"]',
            religion="Muslim",
        )
        user_b, _ = create_user(
            email="rf6@test.com", gender="female", gender_preference='["male"]',
            religion="Christian",
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token1))
        ids = [u["id"] for u in r.json()["users"]]
        assert user_a.id in ids
        assert user_b.id in ids
