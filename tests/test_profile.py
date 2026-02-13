import io
import json
import struct
import zlib


def _make_png_bytes():
    """Minimal valid PNG (1x1 transparent pixel)."""
    def _chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = b"\x00" + b"\x00\x00\x00\x00"
    idat = zlib.compress(raw)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _make_jpeg_bytes():
    """Minimal JPEG-like header bytes."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


class TestUpdateProfile:
    def test_update_display_name(self, client, create_user, auth_headers):
        _, token = create_user(email="up1@test.com")
        r = client.put(
            "/api/v1/profile/me",
            json={"display_name": "New Name"},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["display_name"] == "New Name"

    def test_update_gender_preference(self, client, create_user, auth_headers):
        _, token = create_user(email="up2@test.com")
        r = client.put(
            "/api/v1/profile/me",
            json={"gender_preference": ["male", "female"]},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        assert set(r.json()["gender_preference"]) == {"male", "female"}

    def test_update_location(self, client, create_user, auth_headers):
        _, token = create_user(email="up3@test.com")
        r = client.put(
            "/api/v1/profile/me",
            json={"location": "Los Angeles"},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["location"] == "Los Angeles"

    def test_update_age_range(self, client, create_user, auth_headers):
        _, token = create_user(email="up4@test.com")
        r = client.put(
            "/api/v1/profile/me",
            json={"age_range_min": 25, "age_range_max": 40},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["age_range_min"] == 25
        assert r.json()["age_range_max"] == 40

    def test_get_profile(self, client, create_user, auth_headers):
        _, token = create_user(email="gp@test.com", display_name="My Name")
        r = client.get("/api/v1/profile/me", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["display_name"] == "My Name"
        assert data["profile"] is not None
        assert data["profile"]["bio"] == "Test bio"


class TestPhotoUpload:
    def test_upload_valid_png(self, client, create_user, auth_headers):
        _, token = create_user(email="pu1@test.com")
        png = _make_png_bytes()
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("test.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["is_primary"] is True
        assert data["order_index"] == 0

    def test_upload_valid_jpeg(self, client, create_user, auth_headers):
        _, token = create_user(email="pu2@test.com")
        jpeg = _make_jpeg_bytes()
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("photo.jpg", io.BytesIO(jpeg), "image/jpeg")},
            headers=auth_headers(token),
        )
        assert r.status_code == 201

    def test_upload_rejects_non_image_extension(self, client, create_user, auth_headers):
        _, token = create_user(email="pu3@test.com")
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("malware.exe", io.BytesIO(b"not an image"), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 400

    def test_upload_rejects_non_image_content_type(self, client, create_user, auth_headers):
        _, token = create_user(email="pu4@test.com")
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("test.png", io.BytesIO(b"data"), "text/plain")},
            headers=auth_headers(token),
        )
        assert r.status_code == 400

    def test_upload_rejects_invalid_magic_bytes(self, client, create_user, auth_headers):
        _, token = create_user(email="pu5@test.com")
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("test.png", io.BytesIO(b"this is not a png"), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 400
        assert "not a valid image" in r.json()["detail"]

    def test_upload_rejects_oversized_file(self, client, create_user, auth_headers):
        _, token = create_user(email="pu6@test.com")
        png_header = b"\x89PNG\r\n\x1a\n"
        big_content = png_header + b"\x00" * (6 * 1024 * 1024)
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("big.png", io.BytesIO(big_content), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 413

    def test_second_photo_not_primary(self, client, create_user, auth_headers):
        _, token = create_user(email="pu7@test.com")
        png = _make_png_bytes()
        client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("p1.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token),
        )
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("p2.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 201
        assert r.json()["is_primary"] is False
        assert r.json()["order_index"] == 1


class TestPhotoDelete:
    def test_delete_own_photo(self, client, create_user, auth_headers):
        _, token = create_user(email="pd1@test.com")
        png = _make_png_bytes()
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("test.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token),
        )
        photo_id = r.json()["id"]
        r = client.delete(f"/api/v1/profile/me/photos/{photo_id}", headers=auth_headers(token))
        assert r.status_code == 204

    def test_delete_nonexistent_photo_returns_404(self, client, create_user, auth_headers):
        _, token = create_user(email="pd2@test.com")
        r = client.delete("/api/v1/profile/me/photos/fake-id", headers=auth_headers(token))
        assert r.status_code == 404

    def test_cannot_delete_others_photo(self, client, create_user, auth_headers):
        _, token1 = create_user(email="pd3@test.com")
        _, token2 = create_user(email="pd4@test.com")
        png = _make_png_bytes()
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("test.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token1),
        )
        photo_id = r.json()["id"]
        r = client.delete(f"/api/v1/profile/me/photos/{photo_id}", headers=auth_headers(token2))
        assert r.status_code == 404


class TestPhotoOrderIndexAfterDeletion:
    def test_no_duplicate_order_index_after_delete_and_upload(self, client, create_user, auth_headers):
        _, token = create_user(email="oi1@test.com")
        png = _make_png_bytes()

        # Upload 3 photos (indexes 0, 1, 2)
        ids = []
        for i in range(3):
            r = client.post(
                "/api/v1/profile/me/photos",
                files={"file": (f"p{i}.png", io.BytesIO(png), "image/png")},
                headers=auth_headers(token),
            )
            assert r.status_code == 201
            ids.append(r.json()["id"])

        # Delete the middle photo (index 1)
        r = client.delete(f"/api/v1/profile/me/photos/{ids[1]}", headers=auth_headers(token))
        assert r.status_code == 204

        # Upload a new photo — should get index 3, not 2
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": ("new.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 201
        assert r.json()["order_index"] == 3


class TestProfileDetailsUpdate:
    def test_update_bio(self, client, create_user, auth_headers):
        _, token = create_user(email="pdu1@test.com")
        r = client.put(
            "/api/v1/profile/me/profile",
            json={"bio": "Updated bio"},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["bio"] == "Updated bio"

    def test_update_interests(self, client, create_user, auth_headers):
        _, token = create_user(email="pdu2@test.com")
        r = client.put(
            "/api/v1/profile/me/profile",
            json={"interests": ["cooking", "yoga"]},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["interests"] == ["cooking", "yoga"]

    def test_update_recalculates_completeness(self, client, auth_headers):
        # New user with no profile
        r = client.post("/api/v1/auth/signup", json={
            "email": "pdu3@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        r = client.put(
            "/api/v1/profile/me/profile",
            json={"bio": "Hi", "interests": ["a"], "values": ["b"]},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        # 3 of 6 fields filled → 0.5
        assert r.json()["profile_completeness"] == 0.5

    def test_partial_update_preserves_existing(self, client, create_user, auth_headers):
        _, token = create_user(email="pdu4@test.com")
        # The create_user fixture sets bio="Test bio" and interests=["hiking","reading"]
        r = client.put(
            "/api/v1/profile/me/profile",
            json={"bio": "New bio"},
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["bio"] == "New bio"
        # interests should be preserved from fixture
        assert data["interests"] == ["hiking", "reading"]


class TestBlockedLikePass:
    def test_cannot_like_blocked_user(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="bl1@test.com")
        user2, token2 = create_user(email="bl2@test.com")

        client.post("/api/v1/block", json={"blocked_user_id": user2.id}, headers=auth_headers(token1))

        r = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 403
        assert "blocked" in r.json()["detail"].lower()

    def test_cannot_like_user_who_blocked_you(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="bl3@test.com")
        user2, token2 = create_user(email="bl4@test.com")

        client.post("/api/v1/block", json={"blocked_user_id": user1.id}, headers=auth_headers(token2))

        r = client.post(
            "/api/v1/matches/like",
            json={"liked_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 403

    def test_cannot_pass_blocked_user(self, client, create_user, auth_headers):
        user1, token1 = create_user(email="bp1@test.com")
        user2, token2 = create_user(email="bp2@test.com")

        client.post("/api/v1/block", json={"blocked_user_id": user2.id}, headers=auth_headers(token1))

        r = client.post(
            "/api/v1/matches/pass",
            json={"passed_user_id": user2.id},
            headers=auth_headers(token1),
        )
        assert r.status_code == 403


def _setup_payload(**overrides):
    """Return a valid profile setup payload with optional overrides."""
    base = {
        "display_name": "Test User",
        "date_of_birth": "1995-06-15",
        "height_inches": 68,
        "location": "New York",
        "home_town": "Boston",
        "gender": "Woman",
        "sexual_orientation": "Straight",
        "job_title": "Engineer",
        "college_university": "MIT",
        "education_level": "Bachelor's",
        "languages": ["English", "Spanish"],
        "religion": "None",
        "children": "No",
        "family_plans": "Want someday",
        "drinking": "Socially",
        "smoking": "Never",
        "marijuana": "Never",
        "drugs": "Never",
        "hidden_fields": [],
    }
    base.update(overrides)
    return base


def _upload_photos(client, token, auth_headers, count=3):
    """Upload `count` valid PNG photos and return their IDs."""
    png = _make_png_bytes()
    ids = []
    for i in range(count):
        r = client.post(
            "/api/v1/profile/me/photos",
            files={"file": (f"p{i}.png", io.BytesIO(png), "image/png")},
            headers=auth_headers(token),
        )
        assert r.status_code == 201
        ids.append(r.json()["id"])
    return ids


class TestProfileSetup:
    def test_setup_happy_path(self, client, auth_headers):
        # Sign up a fresh user
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup1@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        _upload_photos(client, token, auth_headers, 3)

        payload = _setup_payload()
        r = client.post(
            "/api/v1/profile/me/setup",
            json=payload,
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["profile_setup_complete"] is True
        assert data["display_name"] == "Test User"
        assert data["height_inches"] == 68
        assert data["home_town"] == "Boston"
        assert data["languages"] == ["English", "Spanish"]
        assert data["hidden_fields"] == []

    def test_setup_fewer_than_3_photos(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup2@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        _upload_photos(client, token, auth_headers, 2)

        r = client.post(
            "/api/v1/profile/me/setup",
            json=_setup_payload(),
            headers=auth_headers(token),
        )
        assert r.status_code == 400
        assert "3 photos" in r.json()["detail"]

    def test_setup_underage(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup3@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        _upload_photos(client, token, auth_headers, 3)

        r = client.post(
            "/api/v1/profile/me/setup",
            json=_setup_payload(date_of_birth="2015-01-01"),
            headers=auth_headers(token),
        )
        assert r.status_code == 422

    def test_setup_invalid_hidden_field(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup4@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        _upload_photos(client, token, auth_headers, 3)

        r = client.post(
            "/api/v1/profile/me/setup",
            json=_setup_payload(hidden_fields=["email"]),
            headers=auth_headers(token),
        )
        assert r.status_code == 422

    def test_chat_gated_without_setup(self, client, auth_headers, mock_openai):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup5@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        r = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers=auth_headers(token),
        )
        assert r.status_code == 403
        assert "profile setup" in r.json()["detail"].lower()

    def test_hidden_fields_in_discover(self, client, create_user, auth_headers):
        # Create user with hidden gender
        # gender_preference must allow each other's gender for discover to return results
        user1, token1 = create_user(
            email="hf1@test.com",
            gender="Woman",
            gender_preference='["Man"]',
            hidden_fields=json.dumps(["gender"]),
        )

        # Create a second user to discover user1
        _, token2 = create_user(
            email="hf2@test.com",
            gender="Man",
            gender_preference='["Woman"]',
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token2))
        assert r.status_code == 200
        users = r.json()["users"]

        # Find user1 in results — must be found for the test to be meaningful
        found = [u for u in users if u["id"] == user1.id]
        assert len(found) == 1, "user1 should appear in discover results"
        assert found[0]["gender"] is None  # hidden

    def test_education_level_always_null_in_discover(self, client, create_user, auth_headers):
        # gender_preference must allow each other's gender for discover to return results
        user1, token1 = create_user(
            email="edu1@test.com",
            gender="Woman",
            gender_preference='["Man"]',
            education_level="PhD",
        )

        _, token2 = create_user(
            email="edu2@test.com",
            gender="Man",
            gender_preference='["Woman"]',
        )

        r = client.get("/api/v1/discover", headers=auth_headers(token2))
        assert r.status_code == 200
        users = r.json()["users"]
        found = [u for u in users if u["id"] == user1.id]
        assert len(found) == 1, "user1 should appear in discover results"
        # education_level is not in discover response at all (AI-only)
        assert "education_level" not in found[0]

    def test_setup_with_hidden_fields(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup6@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        _upload_photos(client, token, auth_headers, 3)

        r = client.post(
            "/api/v1/profile/me/setup",
            json=_setup_payload(hidden_fields=["gender", "religion"]),
            headers=auth_headers(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert set(data["hidden_fields"]) == {"gender", "religion"}

    def test_profile_setup_complete_in_chat_status(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup7@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        r = client.get("/api/v1/chat/status", headers=auth_headers(token))
        assert r.status_code == 200
        assert r.json()["profile_setup_complete"] is False

    def test_setup_idempotent(self, client, auth_headers):
        r = client.post("/api/v1/auth/signup", json={
            "email": "setup8@test.com", "password": "password123",
        })
        token = r.json()["access_token"]

        _upload_photos(client, token, auth_headers, 3)

        payload = _setup_payload()
        r = client.post("/api/v1/profile/me/setup", json=payload, headers=auth_headers(token))
        assert r.status_code == 200

        # Call again with different name
        payload["display_name"] = "Updated Name"
        r = client.post("/api/v1/profile/me/setup", json=payload, headers=auth_headers(token))
        assert r.status_code == 200
        assert r.json()["display_name"] == "Updated Name"
