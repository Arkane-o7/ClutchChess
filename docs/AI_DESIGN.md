# Kung Fu Chess AI — Design Document

## Overview

The AI is an event-driven decision layer over the existing game engine. It reads immutable state snapshots, evaluates candidate moves using timing-aware heuristics, and outputs move commands through the existing `AIPlayer` interface.

The system is designed around four difficulty levels with explicit computational budgets, progressing from simple heuristic evaluation to bounded tactical search.

---

## Difficulty Levels

| Level | Name | Key Capabilities | Budget per Call |
|-------|------|-------------------|-----------------|
| 1 | Novice | Positional heuristics, safe captures, basic threat avoidance | < 0.5ms |
| 2 | Intermediate | Arrival time fields, commitment penalty, capture feasibility with priority rules | < 2.5ms |
| 3 | Advanced | Dodgeability filters, anticipatory positioning, bounded rollout search | < 5ms |

All levels share the same code path with features gated by level. Every call is interruptible and returns best-so-far if budget is exceeded.

### Concurrency Model

AI decisions run on a **thread pool**, off the main game tick loop. This keeps the tick loop fast regardless of AI computation time.

1. **Trigger**: When an AI decision is needed (piece becomes movable, enemy move issued, capture occurs), the controller snapshots the game state and submits the decision task to the thread pool.
2. **Compute**: The AI evaluates candidates on a worker thread. The game loop continues ticking without waiting.
3. **Apply**: When the AI decision completes, the resulting move is queued and applied on the next tick. This adds 1–2 ticks of latency (~33–66ms) which is imperceptible.
4. **Cancellation**: If the game state changes meaningfully before a pending decision completes (e.g., a capture invalidates the plan), the pending result is discarded and a new decision is triggered.

This means the per-call budgets above are wall-clock time on a worker thread, not time stolen from the game loop. A server running many games shares the thread pool — the pool size limits concurrent AI computations, not the tick rate.

### Decision Frequency

AI does not run every tick. Decisions are triggered only by events:

- **Piece becomes movable**: cooldown expires on an idle piece (~every 2–10s depending on speed)
- **Enemy move issued**: a new piece starts traveling
- **Capture occurs**: material changes
- **Fallback timer**: if no event fires within ~200ms and pieces are movable

In practice, most ticks have zero AI work. A typical game might trigger 2–5 AI calls per second, not 30.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              AIController                    │
│  Event triggers, budget management,          │
│  difficulty gating, action selection         │
├──────────┬──────────┬───────────┬───────────┤
│ MoveGen  │  Eval    │ Tactics   │ Search    │
│ Candidate│ Scoring  │ Capture   │ Bounded   │
│ moves    │ function │ feasib.,  │ rollout   │
│ + prune  │          │ dodge,    │ (L3-4)    │
│          │          │ anticip.  │           │
├──────────┴──────────┴───────────┴───────────┤
│            ArrivalField (L2+)               │
│  Per-side timing fields on the board        │
├─────────────────────────────────────────────┤
│            StateExtractor                   │
│  Engine snapshot → AI-friendly structures   │
└─────────────────────────────────────────────┘
```

### Component Responsibilities

**StateExtractor** — Converts `GameState` into AI-friendly structures. For each piece: side, type, grid position, status (idle/traveling/cooldown), cooldown remaining. For the AI's own traveling pieces: full path and destination. For enemy traveling pieces: current position and direction of travel only (destination is hidden). Computed once per AI call.

**ArrivalField** (Level 2+) — Computes `T[side][square]`: the minimum ticks for any piece on `side` to reach each square, accounting for cooldowns and travel time. Used for margin analysis (`T_enemy[sq] - T_us[sq]`) and identifying critical squares.

**MoveGen** — Generates ~6–12 candidate moves per idle, movable piece. Includes safe captures, defensive evasions, king threats, partial slider stops, and anticipatory positioning moves (Level 3+). Prunes moves landing on squares with strongly negative margin (Level 2+).

**Eval** — Scores candidate moves with a weighted sum. Terms: material delta, king danger, destination safety (margin), commitment penalty (proportional to travel time), positional heuristics (center control, piece mobility, open files). All terms use arrival fields when available.

**Tactics** — Pre-scoring filters for move correctness under continuous collision rules. Capture feasibility (timing + priority), dodgeability analysis (Level 3+), anticipatory positioning (Level 3+).

**Search** (Level 3–4) — Bounded rollout when top-scored moves are close or involve high-value pieces. Simulates forward 1–2 seconds using a lightweight event sim. Enemy responses chosen by greedy policy.

**AIController** — Orchestrates everything. Manages event-driven triggers, enforces wall-clock budget, gates features by difficulty level, selects final action(s).

---

## Arrival Time Fields

For each side, compute `T[square]` = minimum ticks for any piece to reach that square.

For each idle piece on the side:
- `T_piece[sq]` = `cooldown_remaining` + `travel_time(piece, sq)`
- Knights: BFS over L-shaped moves
- Sliders (B/R/Q): ray traversal, blocked by static occupancy (ignore moving pieces for speed)
- King/Pawn: adjacent square BFS

Aggregate: `T_side[sq]` = min over all pieces. Traveling pieces are excluded (they can't be retasked).

**Derived values:**
- `margin[sq]` = `T_enemy[sq] - T_us[sq]` (positive = we control it)
- Critical squares `C`: king zones, high-value piece neighborhoods, open lines between major pieces and kings, lanes of traveling sliders

Evaluation focuses on critical squares to keep cost O(|C|) rather than O(board_size).

**Caching:** Fields are cached and incrementally updated — only recompute for pieces whose state changed since last call.

---

## Candidate Generation

For each idle, movable AI piece, generate up to ~12 candidates:

1. **Safe captures** — Targets where we arrive first or win on priority. Validated by tactical capture feasibility check.
2. **Defensive evasions** — If the piece is threatened (enemy can reach its square soon), move to the highest-margin safe square nearby.
3. **King threats** — Moves that reach the enemy king zone with positive margin.
4. **Partial slider stops** (Level 2+) — For sliders, include 1–3 intermediate squares along rays that improve margin or create threats. This models the "fake move" mechanic from our side.
5. **Anticipatory positioning** (Level 3+) — Infer likely destinations of enemy traveling pieces from their direction of travel, and move to squares that threaten or contest the most probable landing zones before they arrive and come off cooldown.
6. **Positional improvements** — Moves toward better-margin squares when no tactical candidates exist.

**Pruning:** Discard moves to squares with margin < -threshold (Level 2+), unless they win material. Penalize long travel unless it creates a forced advantage.

**Multi-piece coordination:** When multiple pieces are movable, use sequential greedy selection: pick the best move, update state, pick next best. Avoid self-collisions and lane conflicts.

---

## Scoring Function

Each candidate move is scored with a deterministic weighted sum:

| Term | Description | Levels |
|------|-------------|--------|
| **Material** | Captures that actually complete (validated by tactics) | All |
| **King danger** | Improvement in time-to-reach enemy king zone, penalty if enemy gains access to our king | All |
| **Safety** | Margin at destination square; en-prise penalty if enemy can reach it first | L2+ |
| **Commitment** | Penalty proportional to travel time; larger if dodgeable (L3+) | L2+ |
| **Positional** | Center control, piece mobility (reachable squares with positive margin), rook on open files, king exposure | All |
| **Coordination** | Bonus for moves that improve margin on critical squares | L2+ |

Weights are tuned per difficulty level. Novice uses only material + king danger + positional with loose weights, producing reasonable but imperfect play.

### Positional Heuristics (All Levels)

These provide sensible play in quiet positions:

- **Center control**: Prefer squares closer to center, weighted by piece mobility from that square
- **Piece activity**: Number of legal target squares from destination (more = better)
- **Rook on open files**: Bonus for rooks on files/ranks with no friendly pawns
- **King exposure**: Penalty for own king on squares with low margin; bonus for maintaining pawn cover
- **Development**: Early-game bonus for moving pieces off back rank (minor pieces especially)
- **Pawn structure**: Mild penalty for isolated/doubled pawns, bonus for connected pawns
- **Pawn advancement**: Bonus for pawns closer to promotion rank (auto-promotes to queen)

---

## Tactical Filters

### Capture Feasibility

Given candidate "A captures B":

1. Compute earliest intercept time where `dist(A(t), B(t)) < 0.4` under assumed B behavior.
2. Check capture priority: compare `move.start_tick` values. The piece whose move was issued earlier wins on contact. Same tick = mutual destruction.
3. Special rules: pawns moving straight cannot capture; knights only capture at ≥85% progress; airborne knights cannot be captured.

### Dodgeability (Level 3+)

Before committing to a long chase, enumerate the target's plausible dodge actions:
- Step perpendicular (1–2 squares)
- Continue forward
- Stop early at intermediate square

For each dodge, simulate intercept kinematics. If any dodge avoids capture and enables a counter-threat, apply a penalty scaled by:
- `dodge_window = distance_to_threat * ticks_per_square - estimated_reaction_ticks`
- Reaction time estimate: varies by game speed (~6 ticks standard, ~3 ticks lightning, representing ~200ms / ~100ms human reaction)
- Penalty is stronger when `dodge_window` is large (easy to dodge)

### Anticipatory Positioning (Level 3+)

Moving pieces cannot be usefully intercepted mid-travel because the interceptor's move is issued later and loses on capture priority. Instead, the AI reasons about where enemy pieces are likely heading based on their direction of travel, and positions to exploit them post-arrival:

1. For each enemy traveling piece E, the AI only knows its current position and direction — not its destination. Enumerate candidate stop squares along E's ray (every valid square from current position to board edge or first blocking piece).
2. Score each candidate stop by how tactically useful it would be for the enemy (threats created, king pressure, piece safety). Weight candidates accordingly — the AI assumes the enemy is making a reasonable move.
3. For the top candidate stops, compute estimated arrival tick and cooldown expiry.
4. For each movable AI piece P, check if P can reach a square that threatens a likely landing zone before E comes off cooldown.
5. Bonus for positions that cover multiple likely stops (hedging), or that attack the most probable destination.

---

## Bounded Rollout Search (Level 3)

### When to Search

Run rollout when:
- Top-2 scored actions are within 15% of each other
- The move involves queen or creates a king threat
- A capture sequence is detected (multiple captures possible)

### Search Parameters

| Parameter | Value |
|-----------|-------|
| Horizon | 1.0–2.0s |
| Our branches | 8–16 |
| Enemy model | Greedy best response |
| Max rollouts | 20–100 |

### Simulation

Lightweight event sim (not full engine):
1. Apply chosen actions (issue moves)
2. Advance time to next event (arrival, contact, cooldown expiry)
3. Resolve captures deterministically using priority rules
4. Update cooldowns
5. Evaluate terminal position

Only resolves interactions involving moving pieces — does not simulate full board physics for uninvolved pieces.

---

## Integration with Existing System

### Interface

The new AI implements the existing `AIPlayer` abstract base class:

```python
class KungFuAI(AIPlayer):
    def __init__(self, level: int = 1, speed: Speed = Speed.STANDARD):
        # level: 1 (Novice), 2 (Intermediate), 3 (Advanced)
        ...

    def should_move(self, state: GameState, player: int, current_tick: int) -> bool:
        # Returns True when global think delay has expired and at least
        # one piece is movable (idle + off cooldown).

    def get_move(self, state: GameState, player: int) -> tuple[str, int, int] | None:
        # Full pipeline: extract → arrival fields → generate → filter → score → (search) → select
```

### Game Service Integration

The game service needs minor changes to support the thread pool model:

- `_create_ai()` routes to `KungFuAI` with the requested level.
- `tick_game()` checks for completed AI decisions in the result queue and applies them via `validate_move` + `apply_move`. At most one move per AI player per tick.
- On state-changing events (enemy move issued, capture), the controller is notified so it can trigger new decisions or cancel stale ones.

### State Access

AI uses `GameState.copy()` for any lookahead/rollout to avoid mutating live state. The `StateExtractor` reads from the snapshot without copying for the evaluation path (read-only access).

### Move Limit

At most one move per AI player per tick. In practice, AI moves far less frequently — decisions are event-driven and bounded by piece cooldowns.

---

## Difficulty Imperfection

Lower difficulty levels should feel like weaker human players, not just slower versions of the best AI. Imperfection is introduced through multiple independent knobs:

### Scoring Noise

Add Gaussian noise to candidate scores before selection. Higher noise = more random-feeling play.

| Level | Noise σ (as % of score range) |
|-------|-------------------------------|
| Novice | 30–40% |
| Intermediate | 15–20% |
| Advanced | 5–10% |

### Think Delay

After the AI issues a move, it enters a global think delay before it will consider its next move. This is the primary knob for making lower levels feel slower — they can only make decisions so often, regardless of how many pieces are available.

| Level | Standard | Lightning |
|-------|----------|-----------|
| Novice | 0.5–5s | 0.3–2.5s |
| Intermediate | 0.3–2s | 0.15–1s |
| Advanced | 0.1–1s | 0.05–0.5s |

A new random delay is rolled after each move. During the delay, the AI makes no moves even if multiple pieces are off cooldown. When the delay expires, the AI evaluates the current board and picks the best available move, then rolls a new delay.

### Tactical Blindness

Lower levels intentionally skip some evaluation terms:

- **Novice**: No arrival fields, no safety margin, no commitment penalty. Sees only material, basic king danger, and positional heuristics. Occasionally misses free captures (via noise).
- **Intermediate**: Has arrival fields but occasionally ignores defended-piece checks (~20% miss rate).
- **Advanced**: Full evaluation with search.

### Piece and Move Consideration Limits

Lower levels don't scan the full board — they consider fewer pieces and fewer moves per piece, simulating a human who focuses on one area at a time.

| Level | Pieces Considered | Candidates per Piece |
|-------|-------------------|---------------------|
| Novice | 1–2 random movable pieces | ~3–4 |
| Intermediate | Up to 4 movable pieces | ~6–8 |
| Advanced | All movable pieces | ~10–12 |

At Novice, the AI picks 1–2 random movable pieces and finds the best move among a small candidate set for those pieces. This naturally produces weaker play without artificial noise alone — the AI simply doesn't see the whole board.

---

## 4-Player Mode

### Design Constraints

4-player games on a 12x12 board with 4× the pieces demand much tighter computation. The AI must remain within budget despite the larger state space.

### Simplifications for 4-Player

- **Arrival fields**: Computed per-side but only for critical squares (king zones of all players + contested center). Skip full-board computation.
- **Candidate generation**: Reduced to ~4–6 per piece (fewer slider partial stops, no anticipatory positioning below Level 3).
- **Target selection**: AI must choose which opponent to pressure. Heuristic: target the opponent with the most exposed king or lowest material, unless another opponent is directly threatening the AI's king.
- **Alliance detection**: No formal alliances, but the AI should avoid attacking an opponent who is currently pressuring a mutual threat. Simple heuristic: deprioritize attacking players who are actively engaged with another enemy.
- **Positional heuristics**: Center control is more important on 12x12. King exposure is evaluated against all opponents' arrival fields (union of enemy T values).

### Budget Scaling

4-player games get tighter budgets per AI player since there may be multiple AI players per game:

| Level | 2-Player Budget | 4-Player Budget (per AI) |
|-------|----------------|--------------------------|
| Novice | < 0.5ms | < 0.25ms |
| Intermediate | < 2.5ms | < 1.25ms |
| Advanced | < 5ms | < 2.5ms |

---

## AI-vs-AI Testing Harness

An automated harness for running AI-vs-AI games, used for validation and weight tuning.

### Capabilities

- Run N games between two AI configurations (level, speed, board type)
- Track win/loss/draw rates, average game length, material at game end
- Deterministic seeding for reproducibility
- Output per-game logs for debugging (moves, evaluations, key decisions)

### Validation Tests

- **Level ordering**: Level N+1 beats Level N with >60% win rate over 100 games
- **Speed consistency**: AI plays reasonably at both standard and lightning speeds
- **4-player**: AI doesn't immediately lose or stalemate in 4-player games
- **No regressions**: After weight/logic changes, re-run the suite to verify level ordering holds

### Tuning Workflow

1. Adjust weights or imperfection knobs
2. Run AI-vs-AI suite (Level 1 vs 2, 2 vs 3, 3 vs 4)
3. Verify win rate ordering
4. Spot-check games where the wrong level won — look for systematic issues
5. Iterate

---

## Build Order

### Phase 1: Level 1 (Novice)
- `StateExtractor`: engine snapshot → AI structures (2-player and 4-player)
- `MoveGen`: candidate generation using `GameEngine.get_legal_moves()` + basic pruning
- `Eval`: material + king danger + positional heuristics (no arrival fields)
- `AIController`: basic trigger logic (cooldown expiry + fallback timer), budget enforcement, thread pool integration
- `KungFuAI` class implementing `AIPlayer`
- Imperfection knobs: scoring noise, reaction delay, move frequency
- AI-vs-AI test harness (Level 1 vs DummyAI)
- Tests: beats DummyAI consistently, doesn't hang pieces for free, stays within 0.5ms budget

### Phase 2: Level 2 (Intermediate)
- `ArrivalField`: per-side timing computation with caching (critical-squares-only mode for 4-player)
- `Tactics`: capture feasibility with priority rules
- `Eval` upgrades: margin-based safety, commitment penalty, coordination
- `MoveGen` upgrades: partial slider stops, margin-based pruning
- 4-player target selection heuristic
- AI-vs-AI validation: Level 2 beats Level 1 >60% over 100 games
- Tests: avoids losing pieces to basic tactics, controls center

### Phase 3: Level 3 (Advanced)
- `Tactics` upgrades: dodgeability analysis, anticipatory positioning
- `Search`: bounded rollout with greedy enemy model
- Event-driven triggers (enemy move, capture events)
- AI-vs-AI validation: Level 3 beats Level 2
- Tests: positions against landing squares, avoids dodgeable chases, looks ahead through capture sequences

---

## Testing Strategy

### Deterministic Scenario Tests

1. **Free capture**: Piece can safely capture an undefended piece → AI takes it at all levels
2. **Defended piece**: Capture would result in losing a higher-value piece → AI avoids it (L2+)
3. **Dodge scenario**: Chasing a rook on a long line where the rook can dodge → AI avoids or sets up a trap (L3+)
4. **Priority race**: Simultaneous contact where earlier-issued move wins → AI avoids "arrive first but lose" scenarios (L2+)
6. **Anticipatory positioning**: Enemy rook moving along a file → AI infers likely destination and moves to threaten the landing zone before cooldown expires (L3+)
7. **King safety**: AI doesn't leave king exposed when other moves are available (all levels)
8. **Quiet position**: No immediate tactics → AI makes positionally sensible moves (all levels)

### Performance Tests

- Worst-case 2-player positions (many pieces, multiple traveling) stay within budget
- Worst-case 4-player positions stay within halved budgets
- Level 1 completes in < 0.5ms, Level 3 in < 5ms
- Thread pool doesn't starve with 50+ concurrent AI games

### Regression Tests (via AI-vs-AI Harness)

- Level N+1 beats Level N with >60% win rate over 100 games (2-player)
- Level ordering holds at both standard and lightning speeds
- 4-player: AI survives to endgame and doesn't immediately lose
- No level hangs pieces that the level below wouldn't also hang
