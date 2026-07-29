# House of Games — Product Requirements Document (PRD)

## 1. Overview

**House of Games** is a Discord bot that hosts a competitive multi-game show experience. It supports three distinct play modes and four unique games. The bot is built in Python and designed for server communities seeking structured, replayable game-night entertainment.

## 2. Goals & Objectives

- Provide a turnkey game-show bot requiring zero manual host intervention.
- Support a minimum of **10 players** per campaign session.
- Deliver three play modes: Campaign, Standalone, and Local.
- Offer four distinct games: Majority Rules, One Night Mafia, Trivia Challenge, and The Trust Game.
- Maintain a leaderboard system for Campaign and Standalone modes.
- Ensure all games are fully automated via Discord interactions (buttons, modals, ephemeral messages).

## 3. Target Audience

- Discord server owners and moderators looking for community-building activities.
- Groups of 10+ players seeking structured, competitive play.
- Casual players wanting quick, standalone games without commitment.

## 4. Functional Requirements

### 4.1 Game Modes

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-01 | Bot shall support Campaign Mode with persistent leaderboard across games | P0 | ✅ |
| FR-02 | Bot shall support Standalone Mode with session-only leaderboard | P0 | ✅ |
| FR-03 | Bot shall support Local Mode with no leaderboard tracking | P0 | ✅ |
| FR-04 | Campaign Mode shall require minimum 10 players to start | P0 | ✅ |
| FR-05 | Campaign Mode shall eliminate bottom players across a season | P1 | ✅ (Majority Rules only) |
| FR-06 | Mode selection shall be available at session creation | P0 | ✅ |

### 4.2 Game-Specific Requirements

| FR-ID | Requirement | Priority | Status |
|-------|-------------|----------|--------|
| FR-07 | Majority Rules shall split 10 players into 2 tables of 5 | P0 | ✅ |
| FR-08 | Majority Rules shall run 10 rounds of majority-vote questions | P0 | ✅ |
| FR-09 | One Night Mafia shall deal 13 roles from a randomized deck | P0 | ✅ |
| FR-10 | One Night Mafia shall execute night phases and a voting phase | P0 | ✅ |
| FR-11 | Trivia Challenge shall present general knowledge questions | P0 | ✅ |
| FR-12 | Trivia Challenge shall eliminate bottom 2 players per round | P1 | ✅ |
| FR-13 | The Trust Game shall deal hidden face cards to each player | P0 | ✅ |
| FR-14 | The Trust Game shall provide 3 questions per round (1 Truth Token) | P0 | ✅ |
| FR-15 | The Trust Game shall run 8 rounds per session | P0 | ✅ |

### 4.3 Non-Functional Requirements

| NFR-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| NFR-01 | Bot shall respond to interactions within 2 seconds | P1 | ✅ |
| NFR-02 | Bot shall handle up to 5 concurrent game sessions | P1 | ✅ (in-memory dict) |
| NFR-03 | All persistent data shall be stored in a database (SQLite/PostgreSQL) | P0 | ✅ (SQLite active) |
| NFR-04 | Bot shall use Discord slash commands and components exclusively | P0 | ✅ |
| NFR-05 | Round timers shall be enforced server-side | P0 | ✅ (`RoundTimer` via asyncio) |

## 5. Out of Scope

- Web dashboard or mobile app.
- Custom user-created games.
- Voice/video integration beyond Discord's native capabilities.
- Real-time spectator mode.

## 6. Success Metrics

- Average session completion rate > 80%.
- Average player retention across a campaign season > 60%.
- < 1% error rate on game state transitions.

## 7. Current Implementation Status

| Component | Status |
|-----------|--------|
| Game Engine & Session Management | ✅ Complete (Phase 1) |
| Majority Rules | ✅ Complete (Phase 2) |
| One Night Mafia | ✅ Complete (Phase 3) |
| Trivia Challenge | ✅ Complete (Phase 4) |
| The Trust Game | ✅ Complete (Phase 5) |
| Polish & Deployment | 🔜 Partial (Phase 6) |
| **Total Tests** | **222 tests** (22 session + 10 modes + 19 flows + 10 majority + 13 mafia + 18 trivia + 15 trust + 87 simulation + other) |
