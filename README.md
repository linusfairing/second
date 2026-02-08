# AI Dating App Backend

A Hinge-style AI-powered dating app backend. Users complete an AI-guided onboarding conversation that builds their dating profile, then discover compatible matches ranked by a weighted Jaccard similarity algorithm. Built with FastAPI and OpenAI GPT.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI 0.104
- **ORM / Database:** SQLAlchemy 2.0 with SQLite (swap to PostgreSQL via `DATABASE_URL`)
- **Auth:** JWT tokens (python-jose) + bcrypt password hashing (passlib)
- **AI:** OpenAI GPT for conversational profile onboarding
- **Validation:** Pydantic v2

## Setup

```bash
# Clone and install
git clone <repo-url> && cd second
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `.env` and fill in the required values:

- **`SECRET_KEY`** — a random string used to sign JWT tokens (generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- **`OPENAI_API_KEY`** — your OpenAI API key for the AI onboarding chat

```bash
# Run the server
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`. Interactive API docs are at `/docs`.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/health` | No | Health check |
| **Auth** | | | |
| `POST` | `/api/v1/auth/signup` | No | Register a new account |
| `POST` | `/api/v1/auth/login` | No | Log in and get a JWT token |
| **Profile** | | | |
| `GET` | `/api/v1/profile/me` | Yes | Get your profile |
| `PUT` | `/api/v1/profile/me` | Yes | Update basic info (name, gender, location, etc.) |
| `PUT` | `/api/v1/profile/me/profile` | Yes | Update profile details (bio, interests, values, etc.) |
| `POST` | `/api/v1/profile/me/photos` | Yes | Upload a photo (max 6, max 5 MB each) |
| `DELETE` | `/api/v1/profile/me/photos/{photo_id}` | Yes | Delete a photo |
| **Chat** | | | |
| `POST` | `/api/v1/chat` | Yes | Send a message to the AI onboarding chat |
| `GET` | `/api/v1/chat/history` | Yes | Get chat history |
| `GET` | `/api/v1/chat/status` | Yes | Get onboarding progress |
| **Discover** | | | |
| `GET` | `/api/v1/discover` | Yes | Discover compatible users (requires completed onboarding) |
| **Matches** | | | |
| `POST` | `/api/v1/matches/like` | Yes | Like a user |
| `POST` | `/api/v1/matches/pass` | Yes | Pass on a user |
| `GET` | `/api/v1/matches` | Yes | List your matches |
| `DELETE` | `/api/v1/matches/{match_id}` | Yes | Unmatch a user |
| **Messages** | | | |
| `GET` | `/api/v1/matches/{match_id}/messages` | Yes | Get messages in a match |
| `POST` | `/api/v1/matches/{match_id}/messages` | Yes | Send a message in a match |
| **Block** | | | |
| `POST` | `/api/v1/block` | Yes | Block a user (auto-unmatches) |
| `DELETE` | `/api/v1/block/{blocked_user_id}` | Yes | Unblock a user |
| `GET` | `/api/v1/block` | Yes | List blocked users |
| **Account** | | | |
| `POST` | `/api/v1/account/deactivate` | Yes | Deactivate your account |
| `POST` | `/api/v1/account/reactivate` | Yes | Reactivate your account |
| `GET` | `/api/v1/account/status` | Yes | Get account status |

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite database and mock the OpenAI client, so no external services are needed.

## Project Structure

```
app/
  main.py              # FastAPI app, lifespan, router registration
  config.py            # Pydantic settings (loads .env)
  database.py          # SQLAlchemy engine and session
  dependencies.py      # Auth dependency (JWT + is_active gating)
  models/              # SQLAlchemy ORM models
    user.py            #   User, UserPhoto
    profile.py         #   UserProfile
    conversation.py    #   ConversationState, ConversationMessage
    match.py           #   Like, Match
    message.py         #   DirectMessage
    block.py           #   BlockedUser
  routers/             # API route handlers
    auth.py            #   Signup, login
    profile.py         #   Profile CRUD, photo upload/delete
    chat.py            #   AI onboarding conversation
    discover.py        #   Discover compatible users
    matches.py         #   Like, pass, match list, unmatch
    messages.py        #   Direct messages within matches
    block.py           #   Block/unblock users
    account.py         #   Deactivate/reactivate account
  schemas/             # Pydantic request/response models
  services/            # Business logic
    auth_service.py    #   Password hashing, JWT creation
    chat_service.py    #   OpenAI integration, topic flow, profile extraction
    matching_service.py #  Weighted Jaccard compatibility scoring
  utils/
    profile_builder.py #   Shared user/profile serialization helpers
    rate_limiter.py    #   In-memory chat rate limiter
tests/
  conftest.py          # Fixtures (client, db, auth, mock OpenAI)
  test_auth.py
  test_block.py
  test_chat.py
  test_discover.py
  test_matches.py
  test_matching.py     # Unit tests for compatibility scoring
  test_messages.py
  test_profile.py
```
