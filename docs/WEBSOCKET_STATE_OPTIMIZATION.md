# WebSocket State Optimization Plan

## Problem

The server broadcasts full game state every tick (100ms) to all connected clients, even when nothing has changed. This is wasteful of bandwidth and CPU. The reference implementation (`the original implementation`) only sends updates when state actually changes.

## Current Behavior

### Server (`server/src/clutchchess/ws/handler.py:506-609`)
- `_run_game_loop()` runs at 10 ticks/second
- Every tick: builds full state message and broadcasts to all clients
- No change detection - always sends

### Replay (`server/src/clutchchess/replay/session.py:217-259`)
- `_playback_loop()` sends state every tick during playback
- Same issue as live games

### Client
- `client/src/stores/game.ts:456-462` - updates `currentTick` and `lastTickTime` on each message
- `client/src/game/interpolation.ts` - interpolates piece positions based on active moves
- `client/src/components/game/GameBoard.tsx:196-201` - already does tick interpolation but caps at 1.0

## Solution Overview

1. **Server**: Only broadcast when state changes (events, moves, cooldowns)
2. **Protocol**: Add `time_since_tick` for smooth client interpolation
3. **Client**: Remove tick interpolation cap to allow continued animation between server updates

## Implementation Plan

### Phase 1: Protocol Changes

**File: `server/src/clutchchess/ws/protocol.py`**
- Add `time_since_tick: float` to `StateUpdateMessage` (milliseconds since tick started, 0-100)

**File: `client/src/ws/types.ts`**
- Add `time_since_tick?: number` to `StateUpdateMessage`

### Phase 2: Server Change Detection

**File: `server/src/clutchchess/ws/handler.py`**

Add helper function to detect if state changed:
```python
def _has_state_changed(
    prev_active_moves: list[ActiveMove],
    prev_cooldowns: list[Cooldown],
    curr_active_moves: list[ActiveMove],
    curr_cooldowns: list[Cooldown],
    events: list[GameEvent],
) -> bool:
    """Check if game state has meaningfully changed."""
    # Always send if there are events
    if events:
        return True

    # Check if active moves changed (new move started or move completed)
    prev_move_ids = {m.piece_id for m in prev_active_moves}
    curr_move_ids = {m.piece_id for m in curr_active_moves}
    if prev_move_ids != curr_move_ids:
        return True

    # Check if cooldowns changed (piece entered/exited cooldown)
    prev_cd_ids = {c.piece_id for c in prev_cooldowns}
    curr_cd_ids = {c.piece_id for c in curr_cooldowns}
    if prev_cd_ids != curr_cd_ids:
        return True

    return False
```

Modify `_run_game_loop()`:
- Track previous tick's `active_moves` and `cooldowns`
- Only broadcast if `_has_state_changed()` returns True
- Always broadcast on first tick after game starts
- Add `time_since_tick` to message (elapsed time within current tick)

### Phase 3: Replay Session Changes

**File: `server/src/clutchchess/replay/session.py`**

Apply same optimization to `_playback_loop()`:
- Track previous state's active_moves and cooldowns
- Only send when state changes between ticks
- Add `time_since_tick` to state messages

### Phase 4: Client Interpolation Fix

**File: `client/src/stores/game.ts`**

Add `timeSinceTick` to state and update handler:
```typescript
// Add to initial state
timeSinceTick: 0, // ms (0-100), from server

// In updateFromStateMessage:
timeSinceTick: msg.time_since_tick ?? 0,
```

**File: `client/src/components/game/GameBoard.tsx`** (lines 196-201)

The client already interpolates but caps at 1 tick. Fix:
```typescript
// Current (problematic - caps at 1 tick ahead):
const tickFraction = Math.min(timeSinceLastTick / TIMING.TICK_PERIOD_MS, 1.0);

// Fixed - allow interpolation up to 10 ticks ahead, account for server's time_since_tick:
const timeSinceTick = useGameStore.getState().timeSinceTick ?? 0;
const adjustedTime = timeSinceLastTick + timeSinceTick;
const tickFraction = Math.min(adjustedTime / TIMING.TICK_PERIOD_MS, 10.0);
```

**File: `client/src/stores/replay.ts`**

Add `timeSinceTick` and `lastTickTime` to replay state for proper interpolation tracking.

**File: `client/src/components/replay/ReplayBoard.tsx`** (line 97)

Same fix - remove the 1.0 cap:
```typescript
// Current:
const tickFraction = Math.min(timeSinceLastTick / TIMING.TICK_PERIOD_MS, 1.0);

// Fixed:
const tickFraction = Math.min(timeSinceLastTick / TIMING.TICK_PERIOD_MS, 10.0);
```

## Files to Modify

| File | Changes |
|------|---------|
| `server/src/clutchchess/ws/protocol.py` | Add `time_since_tick` field |
| `server/src/clutchchess/ws/handler.py` | Add change detection, conditional broadcast |
| `server/src/clutchchess/replay/session.py` | Same optimization for replays |
| `client/src/ws/types.ts` | Add `time_since_tick` to type |
| `client/src/stores/game.ts` | Add `timeSinceTick` state field |
| `client/src/stores/replay.ts` | Add `timeSinceTick`, `lastTickTime` fields |
| `client/src/components/game/GameBoard.tsx` | Fix tick interpolation cap |
| `client/src/components/replay/ReplayBoard.tsx` | Fix tick interpolation cap |

## Verification

1. **Unit tests**: Add tests for `_has_state_changed()` helper
2. **Manual testing**:
   - Start a game with two browser windows
   - Open Network tab in DevTools, filter for WebSocket messages
   - Before: ~10 messages/second constantly
   - After: Messages only when moves/captures happen, idle periods have no messages
3. **Replay testing**:
   - Watch a replay, verify smooth playback
   - Pause/seek should still work correctly
4. **Run existing tests**:
   ```bash
   cd server && uv run pytest tests/ -v
   cd client && npm test
   ```

## Backwards Compatibility

- `time_since_tick` is optional in client types (defaults to 0)
- Client will work with old servers that don't send the field
- Change is purely additive to protocol

## Expected Results

- **Bandwidth reduction**: ~90% fewer WebSocket messages during idle periods
- **CPU reduction**: Less message serialization/parsing on both ends
- **Smooth animations**: Maintained via client-side interpolation
- **No visual change**: Players shouldn't notice any difference in game feel
