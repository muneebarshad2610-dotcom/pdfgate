# House of Games — Development Phases

## Phase 1: Game Engine & Session Management ✅

### Goals
- Build the core game abstraction layer.
- Implement session lifecycle (create, join, start, end).
- Implement all three play modes (Campaign, Standalone, Local).

### Tasks
- [x] Define abstract `BaseGame` class with lifecycle hooks (`on_start`, `on_round`, `on_end`) and `run()` orchestrator.
- [x] Implement `GameSession` — session creation, player join/leave, min/max player checks.
- [x] Implement `SessionManager` — in-memory session registry with channel/guild lookup methods.
- [x] Implement `GameMode` enum and `MODE_CONFIG` dict for mode-specific behavior (leaderboard persistence, eliminations).
- [x] Build `RoundTimer` system for round timeouts using `asyncio.create_task`.
- [x] Implement `LeaderboardManager` wrapping `LeaderboardRepo` (cumulative for Campaign, session-only for Standalone, disabled for Local).
- [x] Implement elimination logic for Campaign Mode.
- [x] Implement custom exception hierarchy (17 exception types in `bot/engine/errors.py`).
- [x] Write unit tests (27 tests in `test_session.py` + 8 tests in `test_modes.py` = 35 total).

### Deliverables
- [x] `/create` command with mode selection (`@app_commands.choices`).
- [x] `/join`, `/leave`, `/start`, `/end`, `/status` commands.
- [x] Session lifecycle (lobby → in_progress → completed).
- [x] Leaderboard CRUD with Campaign (persistent), Standalone (session), Local (disabled).
- [x] 35 unit tests covering session lifecycle, scoring, elimination, timer, modes, and mode parsing.

---

## Phase 2: Game 1 — Majority Rules ✅

### Goals
- Fully implement Majority Rules game.
- Test with 10-player simulated sessions.

### Tasks
- [x] Implement question bank (`bot/data/questions/majority.json`) with 20 opinion-based questions (4-6 options each).
- [x] Implement table splitting logic (2 tables of 5, random assignment).
- [x] Implement round loop: question → ephemeral DM voting → majority calculation → scoring.
- [x] Implement tie-breaking (first encountered option wins).
- [x] Implement end-of-game logic: top 4 advance to leaderboard, bottom 6 eliminated in Campaign mode.
- [x] Add ephemeral answer submission via DMs (`MinorityVoteDMView`).
- [x] Add public table vote distribution display.
- [x] Write unit tests for `calculate_majority`, `format_vote_distribution`, and question bank integrity.
- [x] `/play majority` and `/play majority local` commands (via `GameCog` group).

### Deliverables
- [x] `/play majority` command (with optional `local` flag).
- [x] Fully playable Majority Rules in all three modes.
- [x] 9 unit tests (6 scoring/tie logic + 3 question bank).

---

## Phase 3: Game 2 — One Night Mafia ✅

### Goals
- Fully implement One Night Mafia.
- Handle complex role interactions and phase timers.

### Tasks
- [x] Implement role definitions (`bot/games/mafia_roles.py` — 10 role types, 13-card deck).
- [x] Implement `build_deck()` and `evaluate_winner()` utilities.
- [x] Implement night phase system with sequential wake-ups in correct order (Mafia → Investigator → Seer → Robber → Insomniac → Troublemaker → Masons → Henchman).
- [x] Implement all 8 night actions: `see_team`, `see_mafia`, `see_masons`, `investigate`, `rob`, `trouble`, `check_self`, `seer`.
- [x] Implement voting phase with timeout, tie resolution (no elimination on tie).
- [x] Implement win-condition evaluation: Mafia team (3), Civilian team (3), Tanner (7).
- [x] Role reveal and center card reveal at end of game.
- [x] Write unit tests for deck distribution, win conditions, night action coverage, and role fields.
- [x] `/play mafia` and `/play mafia local` commands (via `GameCog` group).

### Deliverables
- [x] `/play mafia` command (with optional `local` flag).
- [x] Fully playable One Night Mafia in all three modes.
- [x] 13 unit tests (6 deck/roles + 7 win conditions + 1 night actions).

---

## Phase 4: Game 3 — Trivia Challenge ✅

### Goals
- Fully implement Trivia Challenge.
- Build a question database with multiple categories.

### Tasks
- [x] Implement question bank (`bot/data/questions/trivia.json`) — 236 questions across 7 categories (Science, Geography, History, Literature, Pop Culture, Sports, Nature).
- [x] Implement round loop: question → ephemeral DM answer buttons (20s timeout) → scoring → elimination.
- [x] Implement elimination of bottom 2 players per round (tie-breaking by total correct answers).
- [x] Implement void-turn handling for unanswered questions (counts as incorrect, 0 points).
- [x] Override `BaseGame.run()` with dynamic round loop until 1 player remains.
- [x] Implement end-of-game logic: last player standing wins, Campaign mode awards points by placement.
- [x] Write unit tests for question bank integrity, scoring, elimination logic, and standings.
- [x] Register `/play trivia` command with optional `local` flag.
- [x] Add trivia game routing to `session_cog._create_game()`.

### Deliverables
- [x] `/play trivia` command (with optional `local` flag).
- [x] Fully playable Trivia Challenge in all three modes.
- [x] 22 unit tests (5 question bank + 5 scoring + 7 elimination + 5 standings).

---

## Phase 5: Game 4 — The Trust Game ✅

### Goals
- Fully implement The Trust Game.
- Handle complex social deduction mechanics.

### Tasks
- [x] Implement face-card deck (12 cards) and hidden dealing.
- [x] Implement questioning phase: 3 questions per round, 1 Truth Token.
- [x] Implement answering flow: truth-teller mode (host-verified) vs. liar mode (free-form).
- [x] Implement guess-lock phase after questioning.
- [x] Implement scoring: correct guess = points, wrong guess = 0 + elimination risk.
- [x] Implement 8-round loop with top-2 advancement and bottom elimination.
- [x] Write unit tests for Truth Token logic and scoring.
- [x] Write integration test for full 8-round game.

### Deliverables
- [x] `/play trust` command.
- [x] Fully playable The Trust Game in all three modes.

---

## Phase 6: Polish & Deployment 🔜

### Goals
- End-to-end testing.
- Performance optimization.
- Deployment documentation and CI/CD.

### Tasks
- [ ] Full regression test across all four games and three modes.
- [ ] Load test with 5 concurrent sessions.
- [x] Add `/help` command with embed documentation for all commands and game modes.
- [x] Implement basic admin commands (`/ping`, `/sync`, `/force_end`).
- [ ] Set up CI/CD pipeline (GitHub Actions).
- [ ] Write deployment guide (Docker, Railway, or self-host).
- [ ] Performance profiling and optimization.
- [ ] Configure Alembic for database migrations.

### Deliverables
- [ ] Production-ready bot.
- [ ] CI/CD pipeline.
- [ ] Deployment and usage documentation.

### Currently Implemented (partial)
- `/help` — Available commands, modes, and game descriptions.
- `/ping` — Bot latency check.
- `/sync` — Global slash command sync (admin only).
- `/force_end` — Force-end all sessions on a server (admin only).
