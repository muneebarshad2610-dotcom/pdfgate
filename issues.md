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

**✅ FIXED** — `session_cog.py:128`: `session.game = game` assigned before `game.run()`.

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

**✅ FIXED** — `session_cog.py:127-139`: try/except log + error embed + finally end_session.

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

**✅ FIXED** — All 4 games + `get_team_color()` now import from `bot.colors`.

---

## C-GAMES-2 (MEDIUM): `session_cog.py` status command hardcodes emoji IDs

**File:** `bot/cogs/session_cog.py:169`

```python
players_list = "\n".join(
    f"{'<:205150heart951:1531870116587900928>' if not p.eliminated else '<:73190blueasterisk:1531870110896226344>'} {p.display_name} — {p.score} pts"
```

Should import `HEART` and `ASTERISK` from `bot.emojis` instead.

**✅ FIXED** — Now uses `config.emojis.heart` / `config.emojis.asterisk`. Same fix applied to `fun_cog.py`, `dev_cog.py`, `admin_cog.py`, `bot/emojis.py`.

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

---

## C-GAME-2 (CRITICAL): `/play ask` crashes with `discord.Member` in DMs

**File:** `bot/cogs/game_cog.py:82`

```python
async def ask(self, interaction, target: discord.Member, question: str, tt: bool = False):
```

`discord.Member` requires a guild context to resolve. When used in a DM (which the command requires at line 86), discord.py **cannot resolve `discord.Member`** because there is no guild. The command raises an exception before the handler ever runs.

**Impact:** The `/play ask` command is completely broken. Any attempt to use it in DMs crashes immediately.

**Fix:** Change `target: discord.Member` to `target: str` (accept display name or ID) or `target: discord.User` (resolves globally).

---

## C-GAME-3 (CRITICAL): `/play ask` guild_id is `None` in DMs

**File:** `bot/cogs/game_cog.py:89`

```python
session = session_manager.get_player_session(interaction.guild_id, interaction.user.id)
```

`interaction.guild_id` is `None` when the command is used in DMs. `get_player_session` checks `session.guild_id == guild_id` — since all sessions have a real guild ID, `None == actual_guild_id` is always `False`. The command **never** finds the player's session and always responds "You're not in an active game."

**Fix:** Add `get_player_session_by_user(discord_id)` to `SessionManager` that searches across all guilds, and use it in DM-based commands.

---

## C-ENGINE-10 (MEDIUM): `end_game()` called multiple times per session

**File:** `bot/engine/base.py:41`, `bot/games/trivia.py:40`, `bot/games/trust_game.py:41`, `bot/cogs/session_cog.py:138`

`end_game()` is called at multiple points for every game:
1. `BaseGame.run()` calls `self.session.end_game()` after `on_end()` returns
2. `TriviaChallenge.run()` and `TrustGame.run()` (which override `BaseGame.run()`) call `self.session.end_game()` themselves
3. `SessionCog.start()` calls `session_manager.end_session()` in the `finally` block, which calls `session.end_game()` again

**Impact:** For MajorityRules and OneNightMafia: 2 calls. For Trivia and Trust: 3 calls. `end_game()` sets `status = "completed"` and cancels timers — both are idempotent, so the double/triple calls are harmless but indicate design confusion.

**Fix:** Remove `end_game()` calls from individual games' `run()` methods and `BaseGame.run()`. Let `SessionCog.start()`'s `finally` block be the sole caller.

---

## C-ENGINE-11 (MEDIUM): Dev guild auto-sync has no error handling

**File:** `bot/main.py:38-42`

```python
DEV_GUILD_ID = 1522345099181297704
guild = discord.Object(id=DEV_GUILD_ID)
self.tree.clear_commands(guild=guild)
self.tree.copy_global_to(guild=guild)
await self.tree.sync(guild=guild)
```

If any of these calls fail (rate limited, Discord API error, invalid guild ID), the exception propagates and crashes `setup_hook`. The bot may still start but with stale or no commands synced.

**Impact:** Stale slash commands cached in Discord; users see old command signatures.

**Fix:** Wrap dev guild sync in try/except, log the error, and continue.

---

## C-MODES-1 (MEDIUM): All modes require exactly 10 players

**File:** `bot/engine/modes.py`

```python
CAMPAIGN: {"min_players": 10, "max_players": 10, ...}
STANDALONE: {"min_players": 10, "max_players": 10, ...}
LOCAL: {"min_players": 10, "max_players": 10, ...}
```

All three modes mandate exactly 10 players. Standalone and Local modes are documented as flexible "play any game" modes, but the player limit prevents smaller groups from using them.

**Impact:** Cannot play with fewer than 10 players even in Local mode. This contradicts the docs which describe Local as "ideal for practice, private groups, or casual play."

**Fix:** Reduce min_players for STANDALONE and LOCAL to 3 or 4. Ensure all 4 games handle <10 players gracefully.

---

## C-CONFIG-1 (LOW): `config.game.min_players`/`max_players` are unused

**File:** `bot/config.py`

```python
"game": {"min_players": 10, "max_players": 10}
```

These values are defined in `bot/config.py` but **never read by any code**. The mode configs in `bot/engine/modes.py` are used instead.

**Fix:** Either remove from `config.py` or document that they exist as overrides. Currently dead config.

---

## C-ENGINE-12 (LOW): Exception hierarchy mismatch — docs claim 17 types, code has 14

**File:** `docs/architecture-design.md:53`, `bot/engine/errors.py`

The architecture doc claims "17 exception types" but `bot/engine/errors.py` defines only 14:
- `HouseOfGamesError`, `SessionFullError`, `SessionLockedError`, `PlayerNotInSessionError`,
  `NotEnoughPlayersError`, `NotSessionHostError`, `GameAlreadyStartedError`, `InvalidGameTypeError`,
  `InvalidPhaseError`, `PlayerAlreadyVotedError`, `RoleNotFoundError`, `DeckEmptyError`,
  `QuestionNotFoundError`, `TimerExpiredError`

**Impact:** Doc/code inconsistency. No runtime impact.

**Fix:** Update doc to say 14 exception types, or add 3 more exception types to match the doc.

---

## C-COLORS-1 (LOW): `TEAL` color doesn't match UX palette

**File:** `bot/colors.py`, `docs/ux.md:16`

The UX palette in `docs/ux.md` describes:
| Time-sensitive | Yellow (#FEE75C) | Warning, last 10 seconds |

But `bot/colors.py` defines `TEAL = 0x00C9A7` which is a teal/cyan color. The yellow `0xFEE75C` is defined as `AMBER` (separate from TEAL). The naming is confusing — "TEAL" suggests a blue-green color, but it's used for time-sensitive warnings in `dev_cog.py:29` where `TEAL` is the embed color.

**Impact:** Minor naming inconsistency. No runtime impact but confusing for developers.

**Fix:** Add `YELLOW = AMBER` alias, or rename `TEAL` to match its usage.
