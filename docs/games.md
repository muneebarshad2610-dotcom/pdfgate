# House of Games — Detailed Game Mechanics

---

## Game 1: Majority Rules

### Description
A social strategy game where players must predict the majority answer rather than the correct answer.

### Setup
- **Players:** Exactly 10.
- **Split:** Two tables of 5 (random assignment).
- **Rounds:** 10.

### Round Flow
1. Bot announces a question with 4-6 answer options.
2. Each player privately selects one answer (buttons).
3. After all answer or timeout (30s), bot reveals vote distribution per table.
4. Majority answer = the answer chosen by the most players.
5. Players who selected the majority answer earn 1 point.
6. In case of a tie for majority, all tied answers count as majority.

### Scoring
| Event | Points |
|-------|--------|
| Match the majority | +1 |
| Miss the majority | 0 |
| Void (no answer) | 0 |

### End of Game
- After 10 rounds, top 4 players on the table leaderboard receive **1 leaderboard point each** (Campaign mode).
- In case of tie for 4th place, all tied players receive the point.

### Mode-Specific Behavior
- **Campaign:** Points contribute to season leaderboard. Bottom 2 players are eliminated from the house after the game.
- **Standalone:** Session leaderboard shown. No eliminations.
- **Local:** Scores shown for fun. Nothing recorded.

---

## Game 2: One Night Mafia

### Description
A fast-paced deduction game where players have one night to identify the mafia.

### Setup
- **Players:** 10.
- **Deck:** 13 role cards — only 10 are dealt (3 remain in the center).
- **Dealing:** Random. Each player sees only their own role card.

### Role Distribution

| Role | Count | Team | Ability |
|------|-------|------|---------|
| Mafia | 2 | Mafia | See each other |
| Henchman | 1 | Mafia | Sees mafia (mafia cannot see henchman) |
| Civilian | 2 | Civilian | No ability |
| Investigator | 1 | Civilian | Look at 1 player's card OR 2 center cards |
| Robber | 1 | Civilian | Swap card with another player (can't see received card) |
| Troublemaker | 1 | Civilian | Swap two other players' cards (can't see either) |
| Insomniac | 1 | Civilian | Look at own card at end of night |
| Seer | 1 | Civilian | Check if a player is mafia OR look at 2 center cards |
| Masons | 2 | Civilian | See each other (confirm both are civilian) |
| Tanner | 1 | Tanner | Win if voted out |

### Night Phase Order (5 minutes total)

| Order | Role(s) | Action |
|-------|---------|--------|
| 1 | Mafia (2) | Wake up, see each other, go back to sleep |
| 2 | Investigator (1) | Wake up, use ability, go back to sleep |
| 3 | Robber (1) | Wake up, swap with another player, go back to sleep |
| 4 | Insomniac (1) | Wake up, look at own card, go back to sleep |
| 5 | Troublemaker (1) | Wake up, swap two other players, go back to sleep |
| 6 | Masons (2) | Wake up, see each other, go back to sleep |
| 7 | Henchman (1) | Wake up, see mafia members, go back to sleep |

**Note:** If the Seer role is in play, they act after the Investigator (order 2.5).

### Day Phase (Voting)
- All players wake up.
- Voting begins: each player votes for one player via buttons.
- Player with the most votes is eliminated.
- **Tie-breaker:** No one is eliminated (re-vote or random depending on session config).

### Win Conditions

| Winner | Condition | Points |
|--------|-----------|--------|
| Mafia Team | Mafia member is NOT voted out | +3 each |
| Mafia Team | Henchman IS voted out | +3 each (mafia + henchman) |
| Civilian Team | Mafia member IS voted out | +3 each |
| Tanner | Tanner IS voted out | +7 (solo) |

- If Henchman is voted out, Mafia team wins (including Henchman).
- If Tanner is voted out, Tanner wins **instead** of the Mafia team.

### Mode-Specific Behavior
- **Campaign:** Points contribute to season leaderboard.
- **Standalone:** Session leaderboard shown.
- **Local:** Scores shown but not recorded.

---

## Game 3: Trivia Challenge ✅

### Description
A quiz game where players answer general knowledge questions. Bottom players are eliminated each round.

### Setup
- **Players:** 10.
- **Rounds:** Until only 1 player remains (dynamic — questions shuffled from bank).

### Round Flow
1. Bot presents a multiple-choice question (4 options) with category shown.
2. Each player has **20 seconds** to answer via ephemeral DM buttons.
3. After time expires, correct answer is revealed publicly.
4. **Scoring:** +1 for correct, 0 for incorrect, 0 for void.
5. **Elimination:** Bottom 2 players (by score, then total correct across all rounds) are eliminated.
6. Void turns count as incorrect (0 points).

### Tie-Breaking for Elimination
1. Total score (cumulative).
2. Total correct answers across all previous rounds.
3. Player ID (deterministic fallback).

### End of Game
- Last player standing is the winner.
- In Campaign mode, leaderboard points awarded based on final placement (5/4/3/2/1 for top 5).

### Question Categories
- Science (41 questions)
- Geography (40 questions)
- History (36 questions)
- Literature (34 questions)
- Pop Culture (35 questions)
- Sports (36 questions)
- Nature (14 questions)

### Question Bank
- 236 questions across all categories.
- No repeated questions within a single session.
- Questions are randomized in order at game start.

### Mode-Specific Behavior
- **Campaign:** Leaderboard points awarded based on final placement. Eliminated players are removed from the house.
- **Standalone:** Session leaderboard. No eliminations from the house — only from the current game.
- **Local:** Fun scores only.

---

## Game 4: The Trust Game 🔜 *Not yet implemented*

### Description
A high-stakes deduction game where players must identify their own hidden card by questioning others.

### Setup (Planned)
- **Players:** 10 (or configurable 8-12).
- **Deck:** 12 face cards (J, Q, K of hearts, diamonds, clubs, spades).
- **Dealing:** Each player receives 1 card hidden from themselves. Remaining cards go to the center.
- **Rounds:** 8.

### Card Assignment (Planned)
- Each player's card is displayed to **other players** but hidden from the card's owner.
- The card is attached to the player's Discord display name during the round.

### Round Flow (Planned)

#### Phase 1: Questioning (90 seconds)
- Each player gets **3 questions** to ask other players about their card.
- **Truth Token (1 per round):** One of the three questions can be designated as a "Truth Token." The host (bot) answers this question truthfully on behalf of the target player.
- **Lying encouraged:** For the other 2 questions, the answering player may lie or tell the truth as they wish.
- Questions are submitted via a modal interface.
- Answers are sent via ephemeral message to the asker.

#### Phase 2: Guess Lock (30 seconds)
- After questioning ends, players lock in their guess about their own card.
- Guesses are submitted via buttons (select from 12 cards).

### Scoring (Planned)

| Event | Points |
|-------|--------|
| Correct guess | +3 |
| Incorrect guess | 0 |
| Void (no guess) | 0 |

### End of Game (Planned)
- After 8 rounds, top 2 players on the leaderboard advance.
- Bottom players face elimination (in Campaign mode).

### Truth Token Mechanics (Planned)
- The bot knows all card assignments.
- When a Truth Token question is asked, the bot responds with an absolutely truthful answer about the target player's card.
- Example: "Is Alice's card a heart?" → Bot answers "Yes" or "No" truthfully.
- Players must decide which of their 3 questions to use their Truth Token on.

### Strategy Notes (Planned)
- Players may collude, bluff, or form alliances.
- The Trust Game is designed to create drama and social dynamics around who can be trusted.

### Mode-Specific Behavior (Planned)
- **Campaign:** Points advance the season leaderboard. Bottom players eliminated from the house.
- **Standalone:** Session leaderboard only.
- **Local:** No recording.

---

## Cross-Game Mechanics

### Campaign Mode Rules
- A season consists of all 4 games played in sequence.
- Players accumulate leaderboard points across games.
- After each game, bottom-performing players are eliminated from the house.
- The player with the most points at the end of the season wins.

### Player Elimination (Campaign)
| Game | Elimination Rule |
|------|-----------------|
| Majority Rules | Bottom 2 players eliminated from house |
| One Night Mafia | No house elimination (session-based only) |
| Trivia Challenge | Bottom 2 eliminated from house (or last-place) |
| The Trust Game | Bottom players eliminated from house |

### Standalone Mode Rules
- Any single game can be played without starting a campaign.
- Session-based leaderboard resets after the game ends.
- No permanent elimination.

### Local Mode Rules
- Any single game can be started with `/play [game] local`.
- No leaderboard, no points recorded.
- All game mechanics function identically.
- Ideal for practice, private groups, or casual play.
