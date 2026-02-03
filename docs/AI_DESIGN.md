# Kung Fu Chess AI — Design Document

## Overview

The AI is an event-driven decision layer over the existing game engine. It reads immutable state snapshots, evaluates candidate moves using timing-aware heuristics, and outputs move commands through the existing `AIPlayer` interface.

The system is designed around three difficulty levels with explicit computational budgets, progressing from simple heuristic evaluation to tactical awareness with dodge and recapture analysis.

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| **Level 1 (Novice)** | ✅ Complete | Material, positional heuristics, noise, think delay |
| **Level 2 (Intermediate)** | ✅ Complete | Arrival fields, safety scoring, commitment penalty, evasion, threat scoring |
| **Level 3 (Advanced)** | ✅ Complete | Dodgeability (with ray filtering), recapture positioning |
| **StateExtractor** | ✅ Complete | 2P and 4P support, piece status tracking, enemy info hiding |
| **ArrivalField** | ✅ Complete | Per-side timing, per-piece enemy times, critical-only mode for 4P |
| **MoveGen** | ✅ Complete (L1-3) | Candidate generation, capture/evasion flags, margin-based pruning |
| **Eval** | ✅ Complete (L1-3) | Weighted scoring with level-gated terms |
| **Tactics** | ✅ Complete | capture_value ✅, move_safety ✅, dodge_probability ✅, threaten_score ✅, recapture_bonus ✅ |
| **Search** | ⏭️ Descoped | Bounded rollout not needed for L3 differentiation |
| **Fast move gen** | ✅ Complete | Per-piece candidate squares (reduces validate_move calls ~10×) |
| **Thread pool** | ❌ Not started | AI runs synchronously on game tick loop |
| **Event-driven triggers** | ❌ Not started | Only cooldown-expiry + idle piece check |
| **Arrival field caching** | ❌ Not started | Full recomputation every call |
| **Partial slider stops** | ❌ Not started | Planned L2 feature, not yet in MoveGen |
| **4P target selection** | ❌ Not started | No per-opponent evaluation |
| **AI-vs-AI harness** | ✅ Complete | 10-game matchups, material adjudication, win rate logging |

### Current Harness Results (10 games each)

| Matchup | Win Rate | Notes |
|---------|----------|-------|
| L1 vs Dummy (standard) | 100% | All decisive |
| L1 vs Dummy (lightning) | 100% | All decisive |
| L2 vs L1 (standard) | 80–100% | Mostly decisive |
| L2 vs L1 (lightning) | 90–100% | Mostly decisive |
| L3 vs L2 (standard) | 70–90% | Mostly decisive |
| L3 vs L2 (lightning) | 60–100% | Some draws at tick limit |

---

## Difficulty Levels

| Level | Name | Key Capabilities | Budget per Call |
|-------|------|-------------------|-----------------|
| 1 | Novice | Positional heuristics, basic captures, high noise | < 0.5ms |
| 2 | Intermediate | Arrival time fields, safety scoring, commitment penalty, evasion, threat scoring | < 2.5ms |
| 3 | Advanced | Dodgeability with ray filtering, recapture positioning, reduced noise | < 5ms |

All levels share the same code path with features gated by level.

### Concurrency Model

> **Status: Not yet implemented.** AI currently runs synchronously within the game tick loop. The design below describes the planned thread pool model.

AI decisions run on a **thread pool**, off the main game tick loop. This keeps the tick loop fast regardless of AI computation time.

1. **Trigger**: When an AI decision is needed (piece becomes movable, enemy move issued, capture occurs), the controller snapshots the game state and submits the decision task to the thread pool.
2. **Compute**: The AI evaluates candidates on a worker thread. The game loop continues ticking without waiting.
3. **Apply**: When the AI decision completes, the resulting move is queued and applied on the next tick. This adds 1–2 ticks of latency (~33–66ms) which is imperceptible.
4. **Cancellation**: If the game state changes meaningfully before a pending decision completes (e.g., a capture invalidates the plan), the pending result is discarded and a new decision is triggered.

### Decision Frequency

AI does not evaluate every tick. The controller uses a **think delay** — a random pause between moves that varies by level and speed. When the delay expires, it checks for idle pieces and runs the full pipeline.

**Current implementation** (in `AIController.should_move()`):
1. Check think delay: `ticks_since_last_move < think_delay_ticks` → return False (cheap, no allocations)
2. Quick idle piece check: scan board for any non-captured, non-moving, non-cooldown piece
3. Full state extraction and movable piece check

> **Planned but not implemented**: Event-driven triggers (enemy move issued, capture occurs, fallback timer). Currently only cooldown-expiry and idle-piece checks.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              AIController                    │
│  Think delay, budget management,            │
│  difficulty gating, action selection         │
├──────────┬──────────┬───────────────────────┤
│ MoveGen  │  Eval    │ Tactics               │
│ Candidate│ Scoring  │ capture_value,         │
│ moves    │ function │ move_safety,           │
│ + prune  │          │ dodge_probability,     │
│          │          │ threaten_score,        │
│          │          │ recapture_bonus        │
├──────────┴──────────┴───────────────────────┤
│            ArrivalField (L2+)               │
│  Per-side timing fields on the board        │
├─────────────────────────────────────────────┤
│            StateExtractor                   │
│  Engine snapshot → AI-friendly structures   │
└─────────────────────────────────────────────┘
```

### Component Responsibilities

**StateExtractor** `state_extractor.py` — Converts `GameState` into `AIState`. For each piece: side, type, grid position, status (idle/traveling/cooldown), cooldown remaining. For the AI's own traveling pieces: full path and destination. For enemy traveling pieces: current position and direction of travel only (destination is hidden). Also stores `enemy_escape_moves: dict[str, list[tuple[int, int]]]` for L3 dodge analysis. Computed once per AI call, cached between `should_move()` and `get_move()`.

**ArrivalField** `arrival_field.py` — Computes `T[side][square]`: the minimum ticks for any piece on `side` to reach each square, accounting for cooldowns and travel time. Supports all 6 piece types with correct pathfinding (slider blocking, knight BFS, pawn direction per player). Critical-squares-only mode for 4-player boards (king zones + center 4×4). Also computes per-piece enemy arrival times (`enemy_time_by_piece`) for recapture and threat analysis.

**MoveGen** `move_gen.py` — Generates candidate moves with `capture_type: PieceType | None` and `is_evasion: bool` flags. Uses `GameEngine.get_legal_moves_fast()` for efficient move enumeration. Threatened pieces are evaluated first when arrival data is available. Unsafe non-capture moves are pruned by margin threshold. Evasion is determined by checking if the piece is threatened (negative safety margin) and the destination is safe; for captures, safety is recomputed excluding the captured piece.

**Eval** `eval.py` — Scores candidates with a weighted sum. Level-gated terms described in Scoring Function section below.

**Tactics** `tactics.py` — Five tactical functions:
- `capture_value`: Simple piece value lookup for captures
- `move_safety`: Probability-based recapture cost for all moves (L2+)
- `dodge_probability`: Dodge likelihood with attack ray filtering (L3+)
- `threaten_score`: Value of best safely threatened enemy piece (L3), king capped at queen value
- `recapture_bonus`: Positioning reward for recapturing incoming attackers (L3+)

**AIController** `controller.py` — Manages think delays, gates features by level, caches state between should_move/get_move, computes enemy escape moves for L3, orchestrates the full pipeline.

---

## Arrival Time Fields

For each side, compute `T[square]` = minimum ticks for any piece to reach that square.

For each idle piece on the side:
- `T_piece[sq]` = `cooldown_remaining` + `travel_time(piece, sq)`
- Knights: BFS over L-shaped moves (1-2 hops, with cooldown between)
- Sliders (B/R/Q): ray traversal, blocked by static occupancy (ignore moving pieces for speed)
- King/Pawn: adjacent square enumeration
- Pawns: player-specific forward direction (2P and 4P), diagonal captures

Aggregate: `T_side[sq]` = min over all pieces. Traveling pieces are excluded (they can't be retasked).

**Derived values:**
- `margin[sq]` = `T_enemy[sq] - T_us[sq]` (positive = we control it)
- Critical squares `C`: king zones (3×3 around each king), center region
- `post_arrival_safety(sq, travel, exclude_piece_id, moving_from)`: safety margin accounting for travel time, cooldown, and reaction time. Can exclude a specific piece (for capture analysis). The `moving_from` parameter recomputes enemy arrival with the origin square vacated, preventing self-blocking where the piece's own position falsely blocks enemy slider rays.
- `is_piece_at_risk(sq, cooldown_remaining)`: whether a piece can be captured before it can move
- `enemy_time_by_piece`: per-piece enemy arrival times for threat and recapture analysis

**Current limitations:**
- No caching between calls — full recomputation every time (planned: incremental updates)
- Critical-squares-only mode uses static king zones + center (planned: also open lines, traveling piece lanes)

---

## Candidate Generation

For each idle, movable AI piece, generate candidates:

### Current Implementation

**Piece limits by level:**

| Level | Pieces Considered | Candidates per Piece |
|-------|-------------------|---------------------|
| 1 | Up to 4 | Up to 4 |
| 2 | Up to 8 | Up to 8 |
| 3 | Up to 16 | Up to 12 |

**Move properties:**

Each `CandidateMove` has:
- `piece_id`, `to_row`, `to_col`: the move itself
- `capture_type: PieceType | None`: type of piece being captured, or None for non-captures
- `is_evasion: bool`: True if this move saves a threatened piece by moving to a safe square
- `ai_piece: AIPiece | None`: reference to the moving piece's AI state

A move can be both a capture and an evasion simultaneously. Evasion for captures is determined by recomputing post-arrival safety at the destination excluding the captured piece.

**Prioritization:** Captures first, then evasions, then positional moves.

**Pruning (L2+):** Discard non-capture moves to squares where `post_arrival_safety < -(cooldown_ticks / 2)`.

**Fast move generation:** `GameEngine.get_legal_moves_fast()` generates only geometrically reachable squares per piece type before calling `validate_move()`, reducing calls from ~1024 to ~100 per position:
- Pawns: 2-4 squares (forward + diagonal captures)
- Knights: up to 8 L-shapes
- Sliders: ray-cast stopping at first stationary piece
- King: 8 adjacents + castling targets

### Not Yet Implemented

- **Partial slider stops** (planned L2+) — For sliders, include 1–3 intermediate squares along rays that improve margin or create threats.
- **Multi-piece coordination** — Sequential greedy selection with self-collision avoidance.

---

## Scoring Function

Each candidate move is scored with a deterministic weighted sum plus noise.

### Implemented Terms

| Term | Weight | Levels | Description |
|------|--------|--------|-------------|
| **Material** | 10.0 | All | Piece value of captured target (via `capture_value`) |
| **Center control** | 1.0 | All | Distance from board center (closer = better) |
| **Development** | 0.8 | All | Bonus for moving knights/bishops off back rank |
| **Pawn advancement** | 0.15 | All | Bonus for pawns closer to promotion rank (0.5 × 0.3) |
| **Safety** | 10.0 | L2+ | P(recapture) × -piece_value at destination (all moves including captures) |
| **Evasion** | 10.0 | L2+ | Saving a threatened piece ≈ capturing one of equal value |
| **Commitment** | -0.15 | L2+ | Penalty proportional to Chebyshev travel distance (non-captures only) |
| **Threat** | 1.0 | L3 | Value of best enemy piece we safely threaten post-move (king capped at queen value) |
| **Dodge EV** | via Material | L3 | For captures: EV = (1-p)×capture + p×(-our_value×0.9), replaces raw material |
| **Recapture** | 4.0 | L3 | Value of enemy attacker we can recapture after it lands |

### Capture Value

`capture_value(candidate) -> float`

Simple lookup: returns `PIECE_VALUES[capture_type]` for captures, 0.0 for non-captures. Post-arrival safety (recapture risk) is handled separately by `move_safety`.

### Move Safety (L2+)

`move_safety(candidate, ai_state, arrival_data) -> float`

Returns expected material loss from recapture at the destination:
1. Compute `post_arrival_safety` margin (excluding captured piece if this is a capture)
2. If margin ≥ TICK_RATE_HZ: safe, return 0.0
3. Otherwise: `P(recapture) = clamp(1.0 - margin / TICK_RATE_HZ, 0, 1)`
4. Return `-P(recapture) × our_piece_value`

Applies to ALL moves including captures. For captures, the captured piece is excluded from enemy arrival time calculations via `exclude_piece_id`.

### Dodge Probability (L3)

`dodge_probability(candidate, ai_state, arrival_data) -> float`

For capture moves, estimates probability (0.0–1.0) that the target dodges:
1. Compute our travel time to target
2. Check target's `cooldown_remaining + reaction_ticks` vs our arrival — if target can't move in time, return 0.0
3. Get target's escape moves from `enemy_escape_moves`
4. Filter out escapes along the attack ray (via `_is_along_attack_ray`) — moves in the same direction as the attack still get captured
5. `time_factor = min(1.0, dodge_window / (2 × tps))` (speed-proportional)
6. `escape_factor = min(1.0, valid_dodge_count / 2.0)`
7. Return `time_factor × escape_factor`

Used in EV framework: `EV = (1-p) × capture_value + p × (-our_value × 0.9)`

### Threat Score (L3)

`threaten_score(candidate, ai_state, arrival_data) -> float`

After arriving at dest and completing cooldown, finds the highest-value enemy piece we can attack that can't counter-capture us:
1. For each non-traveling enemy piece: compute time for us to attack it from dest
2. Check if enemy can reach our dest before our attack lands (recomputed with our origin vacated from occupancy to avoid self-blocking)
3. If enemy can counter-capture: not a safe threat, skip
4. King threat value is capped at queen level (9.0) to prevent it from dominating scoring
5. Return max piece value among safely threatened enemies

### Recapture Bonus (L3)

`recapture_bonus(candidate, ai_state, arrival_data) -> float`

Detects enemy pieces traveling toward our pieces and rewards positioning for recapture:
1. For each traveling enemy piece, project along travel ray to find targeted own piece
2. Compute enemy landing time and vulnerability window (landing + cooldown)
3. Compute our total time: travel to dest + cooldown + reaction + travel to target
4. If we can arrive before enemy vulnerability expires: bonus = enemy attacker's piece value
5. Return max across all incoming attacks

### Move Selection (Weighted Rank)

Instead of perturbing scores with Gaussian noise, moves are scored deterministically, sorted by score, then selected using rank-based weighted random choice. The AI picks one move from the top N candidates using level-specific weights:

| Rank | L1 | L2 | L3 |
|------|-----|-----|-----|
| 1st | 30 | 50 | 75 |
| 2nd | 25 | 20 | 15 |
| 3rd | 20 | 15 | 5 |
| 4th | 15 | 5 | 3 |
| 5th | 5 | 5 | 2 |
| 6th | 5 | 5 | — |

L1 spreads weight across 6 candidates (frequently picks suboptimal moves). L3 concentrates on the top 1-2 (nearly always picks the best move).

---

## Integration with Existing System

### Interface

The AI implements the existing `AIPlayer` abstract base class:

```python
class KungFuAI(AIPlayer):
    def __init__(self, level: int = 1, speed: Speed = Speed.STANDARD):
        # level: 1 (Novice), 2 (Intermediate), 3 (Advanced)
        ...

    def should_move(self, state: GameState, player: int, current_tick: int) -> bool:
        # Returns True when global think delay has expired and at least
        # one piece is movable (idle + off cooldown).

    def get_move(self, state: GameState, player: int) -> tuple[str, int, int] | None:
        # Full pipeline: extract → arrival fields → generate → score → select
```

### Game Service Integration

- `_create_ai()` routes to `KungFuAI` with the requested level.
- `tick_game()` calls `should_move()` and `get_move()` synchronously during the tick loop.
- Move is validated via `validate_move` + `apply_move` before being applied.

> **Planned**: Thread pool model where AI runs off the tick loop, with result queue and stale-decision cancellation.

### State Access

AI uses `GameState.copy()` for any lookahead/rollout to avoid mutating live state. The `StateExtractor` reads from the snapshot without copying for the evaluation path (read-only access).

### Move Limit

At most one move per AI player per tick. In practice, AI moves far less frequently — decisions are bounded by think delays and piece cooldowns.

---

## Difficulty Imperfection

Lower difficulty levels should feel like weaker human players, not just slower versions of the best AI.

### Weighted Rank Selection — ✅ Implemented

Moves are scored deterministically, then selected via rank-based weighted random choice. Lower levels spread weight across more candidates, causing frequent suboptimal picks. See "Move Selection" above for weight tables.

### Think Delay — ✅ Implemented

After the AI issues a move, it enters a global think delay before it will consider its next move. A new random delay is rolled after each move using `random.uniform()`.

| Level | Standard | Lightning |
|-------|----------|-----------|
| Novice | 1–6s | 1–4s |
| Intermediate | 0.6–5s | 0.6–3s |
| Advanced | 0.3–3s | 0.3–2s |

### Tactical Blindness

- **Novice**: No arrival fields, no safety margin, no commitment penalty, no threat scoring. Sees only material, center control, development, and pawn advancement. High noise causes frequent suboptimal choices.
- **Intermediate**: Arrival fields, safety scoring, evasion, commitment penalty.
- **Advanced**: Threat scoring, dodgeability analysis with ray filtering, recapture positioning, tightest move selection.

### Piece and Move Consideration Limits — ✅ Implemented

| Level | Pieces Considered | Candidates per Piece |
|-------|-------------------|---------------------|
| Novice | Up to 4 | Up to 4 |
| Intermediate | Up to 8 | Up to 8 |
| Advanced | Up to 16 | Up to 12 |

Pieces are selected randomly (with threatened pieces prioritized when arrival data is available). This naturally produces weaker play at lower levels — the AI simply doesn't see the whole board.

---

## 4-Player Mode

### Implemented

- **Board awareness**: 12×12 board with corner cutouts detected via `board_width > 8`
- **Pawn directions**: Per-player forward vectors for all 4 positions (N/S/E/W)
- **Back rank detection**: Player-specific for development bonus
- **Pawn advancement**: Uses correct axis per player orientation
- **Critical-only arrival fields**: Restricts computation to king zones (3×3 around each king) + center 4×4 region
- **Fast move generation**: `is_valid_square()` correctly excludes corner cutouts for all piece types

### Not Yet Implemented

- **Target selection heuristic**: AI should choose which opponent to pressure.
- **Alliance detection**: Deprioritize attacking players who are actively engaged with another enemy.
- **Multi-opponent threat analysis**: Threat and safety should evaluate against all opponents' arrival fields.

### Budget Scaling

4-player games get tighter budgets per AI player since there may be multiple AI players per game:

| Level | 2-Player Budget | 4-Player Budget (per AI) |
|-------|----------------|--------------------------|
| Novice | < 0.5ms | < 0.25ms |
| Intermediate | < 2.5ms | < 1.25ms |
| Advanced | < 5ms | < 2.5ms |

---

## AI-vs-AI Testing Harness

### Current Implementation

Located in `tests/unit/ai/test_ai_harness.py`. Excluded from normal test suite via `@pytest.mark.slow` (run with `uv run pytest -m slow --log-cli-level=INFO`).

**Features:**
- 10 games per matchup, 20,000 tick limit
- Games that hit the tick limit are adjudicated by material advantage (using PIECE_VALUES)
- Results logged with win/loss/draw counts, percentages, and decisive vs adjudicated breakdown
- Think delays active (not zeroed out) — tests actual AI strength including timing
- Alternates player 1/player 2 sides in L2 vs L1 matchups

**Matchups tested:**
- L1 vs DummyAI (standard + lightning)
- L2 vs L1 (standard + lightning)
- L3 vs L2 (standard + lightning)

### Planned Additions

- **4-player harness** — AI survives to endgame, doesn't immediately lose
- **Deterministic seeding** for reproducibility
- **Per-game logging** for debugging (moves, evaluations, key decisions)
- **100-game runs** for statistically significant level ordering validation (>60% win rate)

---

## Build Order

### Phase 1: Level 1 (Novice) — ✅ Complete
- `StateExtractor`: engine snapshot → AI structures (2-player and 4-player) ✅
- `MoveGen`: candidate generation using fast legal moves ✅
- `Eval`: material + positional heuristics (no arrival fields) ✅
- `AIController`: think delay, budget enforcement ✅
- `KungFuAI` class implementing `AIPlayer` ✅
- Imperfection knobs: scoring noise, think delay, piece/move limits ✅
- AI-vs-AI test harness (Level 1 vs DummyAI) ✅
- Fast move generation (`get_legal_moves_fast`) ✅

### Phase 2: Level 2 (Intermediate) — ✅ Complete
- `ArrivalField`: per-side timing computation (critical-squares-only mode for 4-player) ✅
- `Tactics`: capture_value, move_safety (probability-based), threaten_score ✅
- `Eval` upgrades: safety scoring, commitment penalty, evasion bonus, threat bonus ✅
- `MoveGen` upgrades: margin-based pruning, threatened piece prioritization, capture/evasion flags ✅
- AI-vs-AI validation: Level 2 beats Level 1 ~80% over 10 games ✅

**Remaining L2 work:**
- Partial slider stops in MoveGen
- Arrival field caching / incremental updates
- 4-player target selection heuristic

### Phase 3: Level 3 (Advanced) — ✅ Complete
- `Tactics` upgrades: dodge_probability with attack ray filtering, recapture_bonus ✅
- `Eval` upgrades: L3 EV framework for captures (dodge × fail cost), recapture positioning ✅
- Reduced noise (5% σ) and faster think delays ✅
- Rollout search descoped (not needed for L3 differentiation)
- AI-vs-AI validation: Level 3 vs Level 2 matchups ✅

---

## Testing Strategy

### Deterministic Scenario Tests

1. **Free capture**: Piece can safely capture an undefended piece → AI takes it at all levels
2. **Defended piece**: Capture would result in losing a higher-value piece → AI avoids it (L2+)
3. **Dodge scenario**: Chasing a piece where the target has escape squares off the attack ray → AI accounts for dodge probability (L3)
4. **Recapture setup**: Enemy traveling toward our piece → AI positions to recapture after enemy lands (L3)
5. **Safe threat**: AI moves to threaten a high-value enemy piece that can't counter-capture (L2+)
6. **Evasion**: Threatened piece moves to safety; capture-evasions correctly identify safe landing squares excluding captured piece (L2+)
7. **Quiet position**: No immediate tactics → AI makes positionally sensible moves (all levels)

### Current Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_arrival_field.py` | 27+ | Computation, blocking, pawn directions, critical-only, post-arrival safety |
| `test_tactics.py` | 21+ | capture_value (3), move_safety (2), dodge_probability (7), recapture_bonus (5), threaten_score (3) |
| `test_eval.py` | 4+ | Scoring with captures, evasions, noise |
| `test_ai_harness.py` | 6 | L1 vs Dummy (2 speeds), L2 vs L1 (2 speeds), L3 vs L2 (2 speeds) |
| `test_state_extractor.py` | 9+ | Piece extraction, status tracking, enemy info hiding |
| `test_move_gen.py` | — | Covered indirectly via harness |

### Performance Tests (Planned)

- Worst-case 2-player positions (many pieces, multiple traveling) stay within budget
- Worst-case 4-player positions stay within halved budgets
- Level 1 completes in < 0.5ms, Level 3 in < 5ms
- Thread pool doesn't starve with 50+ concurrent AI games

### Regression Tests (via AI-vs-AI Harness)

- Level N+1 beats Level N with >60% win rate over 100 games (2-player)
- Level ordering holds at both standard and lightning speeds
- 4-player: AI survives to endgame and doesn't immediately lose
