# Found Issues

---

## C-GAME-1 (CRITICAL): `/play ask` always says "not in an active game"

**File:** `bot/cogs/game_cog.py:90`

```python
session = session_manager.get_player_session(interaction.guild_id, interaction.user.id)
if not session or not session.game:   # ← session.game is ALWAYS None
```

`GameSession` has no `.game` attribute. The game instance (e.g. `TrustGame(session)`)
is created in `SessionCog.start()` but never stored on `session.game`. So `session.game`
always evaluates to `None`/falsy, and the command never proceeds.

**Fix:** Assign `session.game = self._create_game(session)` in `SessionCog.start()`
(or pass the game instance to the session constructor).

---

## C-ENGINE-1 (HIGH): Eliminations fire in Standalone/Local mode

**File:** `bot/engine/session.py:113-118`

`eliminate_player` has no guard checking `mode_config.eliminations_enabled`. The
mode config sets `eliminations_enabled: False` for STANDALONE and LOCAL, but no
game checks it before calling `eliminate_player`. All four games call
`eliminate_player` unconditionally.

**Files affected:**
- `bot/games/majority_rules.py:190` (campaign-only elim, called inside `if self.session.mode == GameMode.CAMPAIGN:` — actually OK)
- `bot/games/trivia.py:174-175` (`_eliminate_bottom_two` runs in ALL modes)
- `bot/games/trust_game.py:433` (inside `if self.session.mode == GameMode.CAMPAIGN:` — actually OK)
- `bot/games/one_night_mafia.py` (no eliminations called — OK)

**Fix:** Trivia `_eliminate_bottom_two` needs `if self.session.mode == GameMode.CAMPAIGN:` guard.
Also add a guard in `GameSession.eliminate_player()` itself.

---

## C-ENGINE-2 (HIGH): Repos use sync SQLAlchemy inside async methods

**File:** `bot/db/repository.py` (all methods)

Every repo method is `async def` but calls synchronous `SessionLocal()` and
`db.query(...)` without `asyncio.to_thread` or an async engine. The event loop
blocks during every DB operation. This is invisible in tests (no real DB) but
will degrade bot responsiveness under load.

**Fix:** Either wrap DB calls in `asyncio.to_thread()`, use `sqlalchemy[asyncio]`
with `AsyncSession`, or make repo methods synchronous and call them with
`run_in_executor`.

---

## C-ENGINE-3 (MEDIUM): `RoundTimer` is redundant — games use manual `asyncio.sleep` loops

**File:** `bot/engine/timer.py`, `bot/games/*.py`

Every game starts a `RoundTimer` but never checks its state. The actual timing
is driven by manual `for remaining in range(timeout, 0, -1): await asyncio.sleep(1)`
loops. The timer callbacks are `lambda: None` (no-ops). The timer creates extra
`asyncio.Task` objects that do nothing useful.

**Impact:** Timer resources are wasted; if games want cancellation support, the
manual sleep loops don't respond to `timer.cancel()` — they keep running until
the loop completes.

**Fix:** Either remove `RoundTimer` usage from games and rely on the sleep loops,
or refactor games to use the timer's `callback` to trigger phase transitions
instead of polling.

---

## C-ENGINE-4 (MEDIUM): Leaderboard `_session_cache` never cleaned up

**File:** `bot/engine/leaderboard.py:56-59`

`clear_session_cache` exists but is never called. Each STANDALONE game adds
entries to `_session_cache` (keyed by `(discord_id, session_id)`). Memory grows
indefinitely as sessions are played.

**Fix:** Call `session.leaderboard.clear_session_cache(session.id)` in
`SessionManager.end_session()`.

---

## C-ENGINE-5 (MEDIUM): No error handling around `game.run()`

**File:** `bot/cogs/session_cog.py:124-126`

```python
game = self._create_game(session)
if game:
    await game.run()
```

If `game.run()` raises any exception (e.g. `ValueError` from empty question bank,
`KeyError` from state access, network error from Discord API), the session is
permanently stuck in `in_progress` status. There's no `try/except/finally` to
catch errors and call `session.end_game()`.

**Fix:** Wrap `await game.run()` in try/except, log the error, send error embed
to channel, and call `session.end_game()` in `finally`.

---

## C-GAMES-1 (MEDIUM): All 4 games hardcode embed colors instead of using `bot.colors`

**File:** All `bot/games/*.py` files

Each game uses raw hex values for embed colors. Examples:
- `0x5865F2` (Discord blurple) instead of `BLUE_PRIMARY`
- `0x57F287` (Discord green) instead of `GREEN`
- `0xED4245` (Discord red) instead of `RED`
- `0xFEE75C` (Discord yellow) instead of `TEAL` or a new `YELLOW`
- `0x808080` (grey) instead of `GREY`

**Fix:** Import from `bot.colors` and replace all hardcoded values.

| File | Line(s) |
|------|---------|
| `majority_rules.py` | 56, 79, 98, 142, 168 |
| `one_night_mafia.py` | 43, 61, 83, 87, 111, 134, 158, 183, 186, 207, 229, 243, 247, 269, 273, 311, 315, 373, 377, 431, 481-485 |
| `trivia.py` | 51, 54, 83, 86, 101, 143, 145, 187, 213 |
| `trust_game.py` | 55, 59, 75, 97, 101, 135, 138, 160, 174, 191, 233, 236, 241, 252, 262, 267, 303, 307, 319, 323, 378, 382, 417, 441 |

Also `get_team_color()` in `one_night_mafia.py:480-485` is a function that does
this mapping and should use `bot.colors`.

---

## C-GAMES-2 (MEDIUM): `session_cog.py` status command hardcodes emoji IDs

**File:** `bot/cogs/session_cog.py:169`

```python
players_list = "\n".join(
    f"{'<:205150heart951:1531870116587900928>' if not p.eliminated else '<:73190blueasterisk:1531870110896226344>'} {p.display_name} — {p.score} pts"
```

Should import `HEART` and `ASTERISK` from `bot.emojis` instead.

---

## C-MAFIA-1 (MEDIUM): Investigator and Seer center-card peeks are broken

**File:** `bot/games/one_night_mafia.py:172-176, 259-266`

When the Investigator or Seer randomly chooses to peek a center card,
`target_id` is set to the string `"center_1"` or `"center_2"`. Then:
```python
result = self._player_roles.get(str(target_id), {}).get("name", "Unknown")
```
`str("center_1")` is `"center_1"`, which is never a key in `_player_roles`
(those keys are stringified Discord IDs like `"123456789"`). The lookup
returns `{}`, and the player sees `"Unknown"`.

**Fix:** Check if `target_id` starts with `"center_"` and index into
`self._center_cards[int(target_id[-1]) - 1]` directly.

---

## C-ENGINE-6 (LOW): `Trivia._eliminate_bottom_two` double-filters active players

**File:** `bot/games/trivia.py:156`

```python
remaining = [p for p in self.active_players if p not in [pid for pid in self.session.state.eliminated]]
```

`self.active_players` already excludes eliminated players. The `if p not in
self.session.state.eliminated` filter is redundant (always True). Minor inefficiency.

---

## C-ENGINE-7 (LOW): `LeaderboardManager` instantiated fresh in `/leaderboard campaign`

**File:** `bot/cogs/admin_cog.py:116-119`

```python
async def _get_campaign_leaderboard(self, guild_id: int):
    from bot.engine.leaderboard import LeaderboardManager
    lbm = LeaderboardManager()
    return await lbm.get_campaign_standings(guild_id)
```

Each call creates a new `LeaderboardManager` with a new `LeaderboardRepo`. A
singleton or class-level instance would be more appropriate (though functionally
correct since the repo queries the DB each call).

---

## C-ENGINE-8 (LOW): `SessionRepo` and `PlayerRepo` are dead code

**File:** `bot/db/repository.py`

`SessionRepo` and `PlayerRepo` are fully implemented but never imported or used
by any cog. Only `LeaderboardRepo` is used (via `LeaderboardManager`).

**Impact:** Sessions and players are never persisted to database. A bot restart
loses all in-progress session data.

---

## C-ENGINE-9 (LOW): `game_type` missing from `to_dict()`

**File:** `bot/engine/session.py:134-148`

`to_dict()` doesn't include `game_type`. If this dict is used for serialization,
the game type information is lost.

---

## C-DOCS-1 (LOW): README documents `/create [mode]` without `[game]` parameter

**File:** `README.md:70`

Shows `/create [mode]` but the command now requires `game` parameter. Should be
`/create [mode] [game]`.
