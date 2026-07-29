# House of Games — UX Design

## 1. Design Principles

- **Ephemeral by default** — Private information (cards, roles, scores) is sent via ephemeral messages visible only to the player.
- **Buttons over dropdowns** — Essential actions use Discord buttons. Dropdowns are used only when options exceed 5 (e.g., player selection in Mafia voting).
- **Rich embeds** — All game state, round info, and results are presented in styled Discord embeds with consistent color coding.
- **Clear call-to-action** — Every interaction clearly labels what the user needs to do and the remaining time.

## 2. Color Palette (Embeds)

| State | Color | Usage |
|-------|-------|-------|
| Lobby | Blue (#5865F2) | Waiting for players, session info |
| Active | Green (#57F287) | Round in progress, correct answers |
| Time-sensitive | Yellow (#FEE75C) | Warning, last 10 seconds |
| Danger | Red (#ED4245) | Elimination, wrong answer, timeout |
| Neutral | Grey (#808080) | Results, information, end-of-game |

## 3. Command Interface

### 3.1 Session Management

| Command | Description |
|---------|-------------|
| `/create` | Create a new game session (mode selection via `@app_commands.choices`: Campaign / Standalone / Local) |
| `/join` | Join an open session in the current channel |
| `/leave` | Leave the current session |
| `/start` | Start the game (host only, min 10 players) |
| `/end` | End the current session (host only) |
| `/status` | Show current session state and players |

### 3.2 Game Launch

| Command | Description | Status |
|---------|-------------|--------|
| `/play majority` | Start a Majority Rules game (Standalone/Local) | ✅ |
| `/play mafia` | Start a One Night Mafia game | ✅ |
| `/play trivia` | Start a Trivia Challenge game | ✅ |
| `/play trust` | Start a The Trust Game | 🔜 Planned |

## 4. Interaction Patterns

### 4.1 Answer Submission (Majority Rules, Trivia)
```
┌─────────────────────────────────────┐
│  Round 3/10 — Majority Rules        │
│                                     │
│  "Which fruit do you think most     │
│   players will pick?"               │
│                                     │
│  ⏱ Time remaining: 20s             │
│                                     │
│  [🍎 Apple] [🍌 Banana] [🍇 Grape] │
│  [🍊 Orange] [🍓 Strawberry]        │
│                                     │
│  (Ephemeral — only you see this)    │
└─────────────────────────────────────┘
```

### 4.2 Role Reveal (Mafia Night Phase)
```
┌─────────────────────────────────────┐
│  🌙 Night Phase                     │
│                                     │
│  You are the: **Investigator**      │
│                                     │
│  Choose a player to investigate:    │
│                                     │
│  [Select Player ──────────────]  ▼  │
│  ┌────────────────────────────┐     │
│  │ @Alice                      │     │
│  │ @Bob                        │     │
│  │ @Charlie                    │     │
│  │ ...                         │     │
│  └────────────────────────────┘     │
│                                     │
│  ⏱ Time remaining: 30s             │
└─────────────────────────────────────┘
```

### 4.3 Voting Phase (Mafia)
```
┌─────────────────────────────────────┐
│  🗳 Voting Phase — Round 1          │
│                                     │
│  Who do you think is the Mafia?     │
│                                     │
│  [@Alice] [@Bob] [@Charlie]         │
│  [@Diana] [@Eve] [@Frank]           │
│  [@Grace] [@Hank] [@Ivy] [@Jack]   │
│                                     │
│  ⏱ Time remaining: 60s             │
│                                     │
│  (Vote is final once submitted)     │
└─────────────────────────────────────┘
```

### 4.4 Questioning Phase (The Trust Game)
```
┌─────────────────────────────────────┐
│  Round 1/8 — The Trust Game         │
│                                     │
│  Your card is face-down.            │
│  Use your 3 questions to identify   │
│  it.                                │
│                                     │
│  ❓ Question 1 (Truth Token avail):  │
│  [Ask a question...]                │
│                                     │
│  ❓ Question 2:                      │
│  [Ask a question...]                │
│                                     │
│  ❓ Question 3:                      │
│  [Ask a question...]                │
│                                     │
│  🔒 [Lock in my guess]              │
│                                     │
│  (Modal input — one question at     │
│   a time to reduce chaos)           │
└─────────────────────────────────────┘
```

### 4.5 Leaderboard Display
```
┌─────────────────────────────────────┐
│  🏆 Campaign Leaderboard            │
│                                     │
│  #1  @Alice    ██████████  120 pts  │
│  #2  @Bob      ████████░░   95 pts  │
│  #3  @Charlie  ██████░░░░   72 pts  │
│  #4  @Diana    █████░░░░░   60 pts  │
│  #5  @Eve      ████░░░░░░   48 pts  │
│  ─────────────────────────────      │
│  ❌ @Frank    Eliminated R3         │
│  ❌ @Grace    Eliminated R5         │
└─────────────────────────────────────┘
```

### 3.3 Admin Commands

| Command | Description | Status |
|---------|-------------|--------|
| `/ping` | Check bot latency | ✅ |
| `/sync` | Sync slash commands globally (admin only) | ✅ |
| `/force_end` | Force-end all sessions on this server (admin only) | ✅ |

## 5. Error & Edge Case Handling

| Scenario | UX Behavior |
|----------|-------------|
| Player doesn't answer in time | Void turn, shown as "Did not answer" in public round summary |
| Player tries to join a full session | Ephemeral error: "Session is full (10/10)" |
| Player tries to /start with <10 players | Ephemeral error: "Need 10 players to start (currently X)" |
| Player disconnects mid-game | Bot marks them as AFK, treats subsequent turns as void, allows rejoin within 2 rounds |
| Tie in elimination | Bot breaks tie by: (1) most recent correct answer wins, (2) random selection |
| Player attempts invalid action (e.g., voting for self in Mafia) | Button disabled or ephemeral error |

## 6. Accessibility

- All game-critical information is communicated via text (not images/emotes alone).
- Button labels are descriptive (not just emoji).
- Timers have visible countdown updates every 10 seconds.
- Players can use `/help` at any time to see game rules.
