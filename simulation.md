# Simulation: House of Games — End-to-End Flow Analysis

## What This Code Does

House of Games is a Discord bot that hosts competitive multiplayer game shows.
It manages sessions (lobby → in_progress → completed), supports 3 game modes
(Campaign, Standalone, Local), and implements 4 distinct games.

### Architecture

```
main.py → HouseOfGamesBot (discord.ext.commands.Bot)
  ├── cogs/        — Slash command handlers
  │   ├── session_cog  — /create, /join, /leave, /start, /end, /status
  │   ├── game_cog     — /play majority|mafia|trivia|trust, /play ask
  │   ├── admin_cog    — /ping, /sync, /force_end, /leaderboard
  │   ├── help_cog     — /help (paginated)
  │   ├── dev_cog      — /dev echo|permissions|user_info|server_info|uptime
  │   ├── fun_cog      — /fun roll|flip|choose|random|avatar|8ball|rate
  │   └── test_cog     — /test embed|fill|question
  ├── engine/
  │   ├── session.py   — GameSession + SessionManager (in-memory)
  │   ├── modes.py     — GameMode enum, mode config, mode_from_string
  │   ├── timer.py     — RoundTimer (asyncio-based per-session timers)
  │   ├── leaderboard.py — LeaderboardManager (DB-backed + session cache)
  │   ├── base.py      — BaseGame ABC with run() lifecycle
  │   └── errors.py    — Exception hierarchy
  ├── games/
  │   ├── majority_rules.py — 10 rounds, 2 tables, predict majority
  │   ├── one_night_mafia.py — 1 round, night actions, vote, winner eval
  │   ├── trivia.py         — N rounds, last standing wins, bottom-2 elim
  │   └── trust_game.py     — 8 rounds, questioning + guessing phases
  ├── db/
  │   ├── models.py    — SQLAlchemy ORM models + init_db()
  │   ├── repository.py — SessionRepo, PlayerRepo, LeaderboardRepo
  │   └── ... unused: SessionRepo and PlayerRepo are defined but never called
  ├── colors.py        — Theme color constants
  ├── emojis.py        — Custom Discord emoji IDs
  └── ui.py            — PaginatorView (prev/next embed pagination)
```

### Session Lifecycle

1. **`/create [mode] [game]`** — Creates `GameSession` in `SessionManager._sessions`
   - Sets `host_id`, `guild_id`, `channel_id`, `mode`, `game_type`
   - Sends embed with session ID, player count 0/N
2. **`/join`** — Adds player to session
   - Validates: not full, not started, not duplicate
3. **`/leave`** — Removes player from session
   - Validates: not started, player exists
4. **`/start`** — Transitions `lobby → in_progress`
   - Validates: host match, ≥min_players, not already started
   - Calls `_create_game(session)` → instantiates a `BaseGame` subclass
   - Runs `game.run()` → `on_start()` → `on_round()` loops → `on_end()` → `session.end_game()`
5. **`/end`** — Host manually ends session
   - Calls `session.end_game()` → status=`completed`, cancels timers
   - `SessionManager.end_session()` removes from `_sessions` dict

### Game Flows

#### Majority Rules (`/create ... majority_rules`)
- **on_start**: Shuffle players into 2 tables of 5; shuffle 10 questions
- **on_round** (×10): Send channel embed with vote buttons for table, DM each player for minority vote; 30s countdown; calculate majority; score +1 to majority voters
- **on_end**: Top 4 get +1 campaign point; bottom 6 eliminated in Campaign mode

#### One Night Mafia (`/create ... one_night_mafia`)
- **on_start**: Deal 13 roles from 13-card deck to 10 players + 3 center; DM roles; run night actions (Mafia sight, Henchman, Investigator, Robber, Troublemaker, Insomniac, Seer, Masons)
- **on_round** (×1): DM each player a dropdown to vote; 60s countdown; resolve votes; evaluate winner (Mafia/Civilian/Tanner); score winners +3 or +7
- **on_end**: Show final scores

#### Trivia Challenge (`/create ... trivia`)
- **on_start**: Shuffle question bank; init correct_counts
- **on_round**: Show question in channel; DM each player answer buttons; 20s; score +1 for correct; eliminate bottom 2 by `(score, correct_count, random)`
- **on_end**: Campaign mode: award 5/4/3/2/1/0 pts to remaining players

#### The Trust Game (`/create ... trust`)
- **on_start**: Deal 12 cards from J♥–K♠ deck to 10 players + 2 center; DM each player "card face down"
- **on_round** (×8): Questioning phase (90s, can ask 3 questions via `/play ask`, optionally use Truth Token) → Guess phase (30s, pick card from dropdown)
- **Reveal**: Score +3 for correct guess; Campaign mode awards campaign points
- **on_end**: Campaign mode: top 2 advance, rest eliminated

---

## What This Code SHOULD Do (vs What It Actually Does)

### The Big Differences

| Aspect | Current Behavior | Intended Behavior |
|--------|-----------------|-------------------|
| Session persistence | In-memory only; DB models exist but SessionRepo/PlayerRepo never used | Should persist sessions and players to SQLite/Postgres |
| `/play ask` command | NEVER works — checks `session.game` which is never set | Should relay DMs between players for Trust Game questioning |
| Standalone eliminations | `eliminate_player` has no mode guard; games eliminate regardless of mode | Should respect `eliminations_enabled` config flag |
| Error handling | No try/except around `game.run()`; exception leaves session stuck `in_progress` | Should catch errors, report to channel, end session cleanly |
| Hardcoded colors | All 4 games use raw hex values (0x5865F2, 0xED4245, 0x57F287, etc.) | Should use `bot.colors` constants (BLUE_PRIMARY, RED, GREEN, etc.) |
| Hardcoded emoji IDs | `session_cog.py:169` hardcodes emoji IDs directly | Should import from `bot.emojis` |
| RoundTimer usage | Timer is started but never actually controls flow; manual `asyncio.sleep` loops drive timing | Timer should enforce timeout and trigger callbacks |
| DB blocking | Repos use sync SQLAlchemy inside async methods — blocks event loop | Should use `run_in_executor` or async SQLAlchemy |
| Leaderboard cache leak | `_session_cache` is never cleaned up; accumulates forever | Should call `clear_session_cache` on session end |
| Mafia Investigator center peek | `"center_1"` string used as player ID → role lookup returns None | Should look up `self._center_cards[0]` directly |
| Bot structure | `main.py` runs health server + bot in same process | Should be fine for Railway; no issues |
| `/leaderboard standalone` | Shows session leaderboard via `session.leaderboard.get_standings()` | Works but leaderboard-manager-per-query pattern is wasteful |
| README docs | `/create [mode]` doesn't show `[game]` param | Should document the required `game` parameter |

### User Simulation Walkthrough

```
User: /create mode=campaign game=trivia
  → Bot: "Session Created — Game: Trivia Challenge / Mode: Campaign / Host: @user
          Session ID: abc-123 / Players: 0/10"
  → Manager creates GameSession in memory
  → session.game_type = "trivia", session.mode = GameMode.CAMPAIGN

User A: /join
  → Bot: "Player A has joined! (1/10)"
  → session.add_player(A)

Users B–J: /join (9 more times)
  → Bot: "...joined!" (2/10 → 10/10)
  → Last join: "Ready to Start! Host can use /start"

Host: /start
  → Bot: "Game Started! Campaign mode with 10 players!"
  → session.start_game(host_id) → status = "in_progress"
  → game = TriviaChallenge(session)
  → game.run() calls:
       on_start()  → shuffle questions, init scores
       on_round(1) → send question, 20s timer, collect answers,
                      score +1 for correct, eliminate bottom 2
       on_round(2) → repeat with 8 remaining players
       ...loop until 1 remains or questions exhausted
       on_end()    → show final standings, record campaign points

Host or any: /status
  → Bot: "Mode: Campaign / Status: In Progress / Players: 10/10 / Host: @host"
  → Shows player list with scores and elimination status

Host: /end (or session auto-ends when game.run() completes)
  → Bot: "Session Ended"
  → session.end_game() → status = "completed", timers cancelled
```

### Bugs Encountered During This Flow

See `issues.md` for the complete list.

### What's Missing / Would Fail

1. **`/play ask` is completely broken** (C-GAME-1)
2. **Standalone mode eliminates players anyway** (C-ENGINE-1)
3. **If any game throws, session is stuck `in_progress` forever** (C-ENGINE-5)
4. **Mafia center-card investigation is buggy** (C-MAFIA-1)
5. **Timers are started but never drive game flow** (C-ENGINE-3)
