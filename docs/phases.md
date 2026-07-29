# Development Phases

## Phase 1 — Game Engine & Session Management ✅
- [x] Session lifecycle (create, join, leave, start, end)
- [x] Game modes (Campaign, Standalone, Local)
- [x] Player management (add, remove, score, eliminate)
- [x] Standings and elimination logic
- [x] Timer system for round timeouts
- [x] Leaderboard (campaign persistence, session cache)
- [x] Database models and repositories
- [x] Help cog, admin cog (ping, sync, force-end)
- [x] All 12 session tests passing

## Phase 2 — Majority Rules Game ✅
- [x] Table splitting (10 players → 2 tables of 5)
- [x] Question bank (20 opinion-based questions)
- [x] Majority calculation with tie handling
- [x] Per-round scoring and per-table score tracking
- [x] Campaign: top 4 advance, bottom 6 eliminated
- [x] `/play majority` and `/play majority local` commands
- [x] 9 tests (majority logic, question bank)

## Phase 3 — One Night Mafia ✅
- [x] 13-card role deck (7 unique roles)
- [x] Role definitions, order, and night actions
- [x] Night phase execution (see_team, investigate, rob, etc.)
- [x] Voting phase with timeout and tie resolution
- [x] Win-condition evaluation (mafia/civilian/tanner)
- [x] Role reveal and center card reveal
- [x] `/play mafia` and `/play mafia local` commands
- [x] 12 tests (deck, win conditions, night actions)

## Phase 4 — Trivia Challenge 🔜
- [ ] Question bank (multiple categories)
- [ ] Trivia game loop (question → answer → score)
- [ ] Speed bonus scoring
- [ ] Category selection
- [ ] Campaign integration

## Phase 5 — The Trust Game 🔜
- [ ] Hidden card mechanic
- [ ] Betting/trust rounds
- [ ] Reveal and scoring
- [ ] Campaign integration

## Phase 6 — Polish & Production 🔜
- [ ] Error handling and user feedback
- [ ] Rate limiting and anti-spam
- [ ] Analytics and logging
- [ ] Performance optimization
- [ ] Extended test coverage
