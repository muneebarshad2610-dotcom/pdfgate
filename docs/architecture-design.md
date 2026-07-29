# House of Games — Architecture Design

## 1. System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Discord Client                        │
│   (User interactions via Slash Commands / Buttons)       │
└────────────────────────┬────────────────────────────────┘
                         │ Gateway & HTTP (discord.py)
┌────────────────────────▼────────────────────────────────┐
│                  Bot Process (Python)                     │
│  ┌───────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │   Cogs    │  │   Session    │  │  Game Engine    │   │
│  │ session_cog│◄─►│  Manager    │◄─►│  ┌──────────┐ │   │
│  │ game_cog  │  │              │   │  │ BaseGame │ │   │
│  │ admin_cog │  │  (in-memory  │   │  ├──────────┤ │   │
│  │ help_cog  │  │   dict)      │   │  │Majority  │ │   │
│  └───────────┘  └──────────────┘   │  │ Rules    │ │   │
│                                    │  │OneNight  │ │   │
│                                    │  │ Mafia    │ │   │
│                                    │  └──────────┘ │   │
│                                    └────────────────┘   │
│  ┌────────────────────────┐  ┌──────────────────────┐    │
│  │   Database Layer       │  │  Timer / RoundTimer   │    │
│  │  (SQLAlchemy + SQLite)  │  │  (asyncio tasks)      │    │
│  │  Models → Repository   │  └──────────────────────┘    │
│  └────────────────────────┘                               │
└──────────────────────────────────────────────────────────┘
```

## 2. Component Architecture

### 2.1 Bot Core (`bot/`)
- `__init__.py` — Package init.
- `config.py` — Environment-based configuration (`.env`) via `AttrDict`.
- `utils.py` — `AttrDict` helper class for nested dict attribute access.
- `errors.py` — Re-exports custom exception hierarchy from `bot/engine/errors.py`.
- `main.py` — `HouseOfGamesBot` class (discord.py `commands.Bot` subclass), cog loading, `on_ready`.

### 2.2 Cogs (`bot/cogs/`)
- `session_cog.py` — `/create`, `/join`, `/leave`, `/start`, `/end`, `/status` commands.
- `game_cog.py` — `/play majority`, `/play mafia` commands (group cog).
- `admin_cog.py` — `/ping`, `/sync`, `/force_end` admin utilities.
- `help_cog.py` — `/help` command with embed documentation.

### 2.3 Game Engine (`bot/engine/`)
- `base.py` — `BaseGame` abstract class with `on_start`, `on_round`, `on_end` lifecycle hooks.
- `session.py` — `GameSession` class managing players, mode, state; `SessionManager` for CRUD across sessions.
- `modes.py` — `GameMode` enum (CAMPAIGN, STANDALONE, LOCAL) + `MODE_CONFIG` dict.
- `leaderboard.py` — `LeaderboardManager` wrapping `LeaderboardRepo`.
- `timer.py` — `RoundTimer` using `asyncio.create_task`.
- `errors.py` — Custom exception hierarchy (17 exception types).

### 2.4 Games (`bot/games/`)
- `majority_rules.py` — Fully implemented (10 rounds, table splitting, ephemeral voting).
- `one_night_mafia.py` — Fully implemented (13-card deck, night phase, voting, role reveal).
- `mafia_roles.py` — Role definitions, deck builder, win-condition evaluator.
- `trivia.py` — Fully implemented (236 questions, dynamic rounds, ephemeral DM answers).
- `trust_game.py` — **Not yet implemented.**

### 2.5 Database (`bot/db/`)
- `models.py` — SQLAlchemy ORM models (`SessionModel`, `PlayerModel`, `LeaderboardEntryModel`), engine/session helpers, `init_db()`.
- `repository.py` — Data access layer (`SessionRepo`, `PlayerRepo`, `LeaderboardRepo`).
- `migrations/` — **Not yet created** (Alembic is in dependencies but not configured).

### 2.6 Data (`bot/data/`)
- `questions/majority.json` — 20 opinion-based questions for Majority Rules.
- `questions/trivia.json` — 236 questions across 7 categories for Trivia Challenge.
- `roles.json` / `cards.json` — **Not yet created** (role/card data is inline in `mafia_roles.py`).

## 3. Data Models

### 3.1 Session (in-memory `GameSession`)
```
GameSession (in-memory)
├── id: str (UUID4)
├── guild_id: int
├── channel_id: int
├── host_id: int
├── mode: GameMode enum (campaign | standalone | local)
├── game_type: str | None (majority_rules | one_night_mafia)
├── state.status: str (lobby | in_progress | completed)
├── state.current_round: int
├── state.total_rounds: int
├── state.players: dict[str, AttrDict]
├── state.player_order: list[int]
├── state.eliminated: list[int]
├── leaderboard: LeaderboardManager
├── timer: RoundTimer
├── bot: discord.Client | None
└── mode_config: AttrDict
```

### 3.2 Player (in-memory — `AttrDict` within `GameSession.state.players`)
```
Player (AttrDict)
├── discord_id: int
├── display_name: str
├── score: int (default 0)
├── eliminated: bool (default false)
├── eliminated_at_round: int (nullable)
└── joined_at: None
```

### 3.3 Database Models (`bot/db/models.py`)

**SessionModel** (DB-persisted)
```
SessionModel
├── id: String (PK)
├── guild_id: BigInteger
├── channel_id: BigInteger
├── host_id: BigInteger
├── mode: String(20)
├── game_type: String(50) (nullable)
├── status: String(20)
├── created_at: DateTime (server_default)
└── ended_at: DateTime (nullable)
```

**PlayerModel**
```
PlayerModel
├── id: String (PK)
├── session_id: String
├── discord_id: BigInteger
├── display_name: String(100)
├── score: Integer (default 0)
├── eliminated: Boolean (default false)
├── eliminated_at_round: Integer (nullable)
└── joined_at: DateTime (server_default)
```

**LeaderboardEntryModel**
```
LeaderboardEntryModel
├── id: String (PK)
├── guild_id: BigInteger
├── discord_id: BigInteger
├── display_name: String(100)
├── campaign_points: Integer (default 0)
├── session_points: Integer (default 0)
├── games_played: Integer (default 0)
└── updated_at: DateTime (server_default, onupdate)
```

## 4. Game State Machine

```
                    ┌─────────┐
                    │  LOBBY  │
                    └────┬────┘
                         │ /start (min 10 players)
                    ┌────▼────┐
                    │ STARTED │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        [Round 1]   [Round 1]   [Round 1]   ... (per game)
              │          │          │
              └──────────┼──────────┘
                         ▼
                    ┌─────────┐
                    │  ROUND  │  (Repeat N times)
                    │  N+1    │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  ENDED  │
                    └─────────┘
```

## 5. Interaction Flow (Example: Majority Rules)

```
User: /create mode:campaign
Bot: [Embed] Session Created — Mode: Campaign
Users: /join (×9 more)
User: /start
Bot: [Embed] Game Started! — Campaign mode with 10 players
Bot: [Embed] Tables Assigned! — Table 1: @Alice, @Bob, ... / Table 2: ...
Bot: [Embed] Round 1/10 — Table 1 + [MajorityVoteView buttons]
Bot: [DM to each player] Your Vote — [MinorityVoteDMView buttons]
Bot: (30s timer)
Bot: [Embed] Table 1 Results — Majority: Blue, +1 to @Alice, @Bob
Bot: ... (repeat 10 rounds across both tables)
Bot: [Embed] Final Standings — ranked list with scores
Bot: [Embed] Eliminations — bottom 6 eliminated from house (Campaign mode)
```

## 6. Technology Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Runtime | Python 3.11+ | ✅ |
| Discord Library | discord.py 2.4+ | ✅ |
| Database | PostgreSQL (prod) / SQLite (dev) | ✅ (SQLite active, Postgres configured) |
| ORM | SQLAlchemy 2.0 | ✅ |
| Migrations | Alembic 1.13+ | ⏳ (in deps, not configured) |
| Task Scheduling | asyncio | ✅ |
| Testing | pytest 8+ / pytest-asyncio | ✅ (57 tests) |
| CI/CD | GitHub Actions | ❌ (not set up) |
| Deployment | Docker + Railway | ❌ (not set up) |

## 7. Security & Performance

- All Discord interactions validated (command permissions, ephemeral responses for private data).
- Timer callbacks use asyncio — no blocking I/O in the event loop.
- Database connection pooling configured via SQLAlchemy engine.
- Rate limiting on command execution — **not yet implemented**.
- Session data stored in-memory (`GameSession` in `SessionManager._sessions` dict) with DB persistence via `SessionRepo`/`PlayerRepo` at game end.
