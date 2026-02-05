# Kung Fu Chess Campaign Mode — Design Document

## Overview

The campaign mode provides a single-player progression system with puzzle-like chess challenges. Players progress through themed "belts" (inspired by martial arts ranks), completing 8 levels per belt to advance. The system preserves compatibility with the legacy kfchess campaign implementation while extending support to 4-player boards.

---

## Goals & Constraints

### Must Have
1. **Backward compatibility** with existing campaign progress data (already in current database)
2. **Same level format** for existing 32 levels (copied faithfully from legacy)
3. **DB schema compatibility** with existing `campaign_progress` table
4. **4-player campaign levels** — future levels using the 12x12 board

### Design Decisions

| Question | Decision |
|----------|----------|
| Campaign AI behavior | Uses difficulty level 3 (advanced) via "bot:campaign" player ID; can be tuned per level later |
| 4-player win condition | Last survivor — player wins when all opponent kings are captured (AI can eliminate each other) |
| Progress reset | Not needed — users can replay any completed level |
| Replay integration | Yes — campaign games saved with `campaign_level_id` and `initial_board_str` for custom board reconstruction |
| Offline progress | No — campaign page requires login |

---

## Legacy System Analysis

### Database Schema (Preserved)

The existing `campaign_progress` table (already in the current database):

```sql
CREATE TABLE campaign_progress (
    id        BIGSERIAL PRIMARY KEY,
    user_id   BIGINT UNIQUE,
    progress  JSONB
);
```

**Progress JSONB structure:**
```json
{
  "levelsCompleted": {"0": true, "1": true, "7": true},
  "beltsCompleted": {"1": true}
}
```
- Keys are string representations of integers (level index, belt number)
- Belt 1 = levels 0-7, Belt 2 = levels 8-15, etc.

### Level Specification Format (Preserved)

Levels use a string-based board representation:

**Board string format:**
- 8 rows for 2-player (8x8), 12 rows for 4-player (12x12)
- Each square = 2 characters: piece type + player number
- `00` = empty square
- Piece types: `P` (pawn), `N` (knight), `B` (bishop), `R` (rook), `Q` (queen), `K` (king)
- Players: `1` (white/east), `2` (black/south), `3` (west), `4` (north)

### Belt Structure

| Belt | Levels | Speed | Theme | Status |
|------|--------|-------|-------|--------|
| 1 - White | 0-7 | Standard | Tutorial basics | Implemented |
| 2 - Yellow | 8-15 | Standard | Pawn structures, basic tactics | Implemented |
| 3 - Green | 16-23 | Lightning | Speed introduction | Implemented |
| 4 - Purple | 24-31 | Standard | Advanced piece coordination | Implemented |
| 5 - Orange | 32-39 | TBD | 4-player introduction | Planned |
| 6 - Blue | 40-47 | TBD | 4-player tactics | Planned |
| 7 - Brown | 48-55 | TBD | Expert challenges | Planned |
| 8 - Red | 56-63 | TBD | Master challenges | Planned |
| 9 - Black | 64-71 | TBD | Grandmaster | Planned |

---

## Architecture

### New Components

```
server/src/kfchess/
├── campaign/
│   ├── __init__.py
│   ├── levels.py           # Level definitions (all 32 legacy levels)
│   ├── models.py           # CampaignLevel dataclass
│   ├── board_parser.py     # Parse board strings → Board objects
│   └── service.py          # Campaign business logic (CampaignService, CampaignProgressData)
├── api/
│   └── campaign.py         # REST endpoints (/campaign/*)
├── ws/
│   └── handler.py          # WebSocket handler (campaign completion)
├── services/
│   └── game_service.py     # GameService (create_campaign_game)
└── db/
    ├── models.py           # CampaignProgress model, GameReplay.campaign_level_id
    └── repositories/
        └── campaign.py     # Campaign progress repository (JSONB upsert)

client/src/
├── pages/
│   ├── Campaign.tsx        # Campaign page component
│   └── Campaign.css        # Page styles
├── stores/
│   └── campaign.ts         # Zustand store (progress, levels, belt selection)
├── components/
│   └── campaign/
│       ├── index.ts        # Barrel exports
│       ├── BeltSelector.tsx    # Belt selection with color indicators
│       ├── BeltSelector.css
│       ├── LevelGrid.tsx       # Grid of level cards
│       └── LevelGrid.css
└── api/
    ├── client.ts           # API calls (getCampaignProgress, startCampaignLevel)
    └── types.ts            # CampaignProgress, CampaignLevel, StartCampaignGameResponse
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                                │
│  Campaign Page → Level Select → Start Level → Game Page     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    REST API                                  │
│  GET /campaign/progress                                     │
│  GET /campaign/levels                                       │
│  POST /campaign/levels/{level_id}/start                     │
│  (progress updated automatically on game win via WebSocket) │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Campaign Service                            │
│  - Load level definitions                                    │
│  - Check unlock status                                       │
│  - Create campaign games via GameService                     │
│  - Update progress on win                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Game Engine                                │
│  - GameEngine.create_game_from_board()                      │
│  - Custom board from level definition                        │
│  - Campaign AI opponent(s)                                   │
│  - Replay saved on completion (like normal games)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Database Model

**Add to `server/src/kfchess/db/models.py`:**

```python
class CampaignProgress(Base):
    """User's campaign progress.

    Schema matches legacy kfchess for backward compatibility.
    Progress is stored as JSONB with:
      - levelsCompleted: dict[str, bool] - level index → completed
      - beltsCompleted: dict[str, bool] - belt number → completed

    Note: This table already exists with user data from the legacy system.
    """
    __tablename__ = "campaign_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    progress: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
```

**Migration** (only needed if table doesn't exist — check first):
```sql
-- Only run if table doesn't exist
CREATE TABLE IF NOT EXISTS campaign_progress (
    id        BIGSERIAL PRIMARY KEY,
    user_id   BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    progress  JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_campaign_progress_user_id ON campaign_progress(user_id);
```

### 2. Level Definition System

**`server/src/kfchess/campaign/models.py`:**

```python
from dataclasses import dataclass

from kfchess.game.board import BoardType  # Reuse existing enum


@dataclass
class CampaignLevel:
    """Campaign level definition.

    Attributes:
        level_id: Unique level index (0-based)
        belt: Belt number (1-9)
        speed: Game speed ("standard" or "lightning")
        board_str: Board layout in legacy string format
        board_type: Board dimensions (uses existing BoardType enum)
        player_count: Number of players (2 or 4)
        title: Display name
        description: Hint/objective text
    """
    level_id: int
    belt: int
    speed: str
    board_str: str
    board_type: BoardType = BoardType.STANDARD
    player_count: int = 2
    title: str = ""
    description: str = ""

    @property
    def belt_level(self) -> int:
        """Level within belt (0-7)."""
        return self.level_id % 8
```

**`server/src/kfchess/campaign/board_parser.py`:**

```python
from kfchess.game.board import Board, BoardType
from kfchess.game.pieces import Piece, PieceType

PIECE_TYPE_MAP = {
    "P": PieceType.PAWN,
    "N": PieceType.KNIGHT,
    "B": PieceType.BISHOP,
    "R": PieceType.ROOK,
    "Q": PieceType.QUEEN,
    "K": PieceType.KING,
}


def parse_board_string(board_str: str, board_type: BoardType) -> Board:
    """Parse legacy board string format into a Board object.

    Args:
        board_str: Multi-line string with 2 chars per square
        board_type: Target board dimensions

    Returns:
        Board object with pieces placed
    """
    lines = [line.strip() for line in board_str.strip().splitlines() if line.strip()]

    if board_type == BoardType.STANDARD:
        expected_rows = 8
        expected_cols = 8
    else:
        expected_rows = 12
        expected_cols = 12

    if len(lines) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, got {len(lines)}")

    board = Board.create_empty(board_type)

    for row, line in enumerate(lines):
        if len(line) != expected_cols * 2:
            raise ValueError(f"Row {row} has wrong length: {len(line)}, expected {expected_cols * 2}")

        for col in range(expected_cols):
            cell = line[col * 2 : col * 2 + 2]
            if cell == "00":
                continue

            piece_type_char = cell[0]
            player = int(cell[1])

            if piece_type_char not in PIECE_TYPE_MAP:
                raise ValueError(f"Unknown piece type: {piece_type_char}")

            board.add_piece(
                Piece.create(
                    PIECE_TYPE_MAP[piece_type_char],
                    player=player,
                    row=row,
                    col=col,
                )
            )

    return board
```

### 3. Level Definitions (All 32 Legacy Levels)

**`server/src/kfchess/campaign/levels.py`:**

```python
"""Campaign level definitions.

Levels 0-31: Legacy 2-player levels (preserved from original kfchess)
Levels 32+: Future 4-player levels (to be designed)
"""

from .models import CampaignLevel

# Belt names
BELT_NAMES = [
    None,      # 0 (unused)
    "White",   # 1: levels 0-7
    "Yellow",  # 2: levels 8-15
    "Green",   # 3: levels 16-23
    "Purple",  # 4: levels 24-31
    "Orange",  # 5: levels 32-39 (future)
    "Blue",    # 6: levels 40-47 (future)
    "Brown",   # 7: levels 48-55 (future)
    "Red",     # 8: levels 56-63 (future)
    "Black",   # 9: levels 64-71 (future)
]

MAX_BELT = 4  # Currently implemented belts


LEVELS: list[CampaignLevel] = [
    # ========== Belt 1: White (Tutorial) ==========
    CampaignLevel(
        level_id=0,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            P1P1P1P1P1P1P1P1
            R1N1B1Q1K1B1N1R1
        """,
        title="Welcome to Kung Fu Chess",
        description="It's like chess, but there are no turns. Win by capturing the enemy king!",
    ),
    CampaignLevel(
        level_id=1,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            R10000Q1K10000R1
        """,
        title="The Elite Guard",
        description="Use your queen and rooks to trap the enemy king. Remember, pieces can move at the same time!",
    ),
    CampaignLevel(
        level_id=2,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            P1P1P10000P1P1P1
            00000000K1000000
        """,
        title="March of the Pawns",
        description="Advance pawns to the end of the board to promote them.",
    ),
    CampaignLevel(
        level_id=3,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000R1K1R10000
        """,
        title="Flanking Strike",
        description="Attack the enemy king from both sides with your rooks.",
    ),
    CampaignLevel(
        level_id=4,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000Q1K1000000
        """,
        title="Royal Couple",
        description="A king must always protect his queen!",
    ),
    CampaignLevel(
        level_id=5,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000P1P1000000
            00000000K1000000
        """,
        title="Step by Step",
        description="Maintain a tight formation to avoid the enemy breaking through.",
    ),
    CampaignLevel(
        level_id=6,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000B100K1B10000
        """,
        title="Criss Cross",
        description="Bishops are great for closing off angles, but keep in mind that they only cover one color each.",
    ),
    CampaignLevel(
        level_id=7,
        belt=1,
        speed="standard",
        board_str="""
            00000000K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            00N10000K100N100
        """,
        title="The Two Horsemen",
        description="Knights capture only at the end of their path. Ride to victory!",
    ),

    # ========== Belt 2: Yellow ==========
    CampaignLevel(
        level_id=8,
        belt=2,
        speed="standard",
        board_str="""
            0000000000000000
            000000P2K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000B100K1B10000
        """,
        title="Bishop Blockade",
        description="Don't let the pawn advance to the end of the board!",
    ),
    CampaignLevel(
        level_id=9,
        belt=2,
        speed="standard",
        board_str="""
            00000000K2000000
            000000P2P2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000Q1K1000000
        """,
        title="Double Trouble",
        description="Choose your angle of attack wisely.",
    ),
    CampaignLevel(
        level_id=10,
        belt=2,
        speed="standard",
        board_str="""
            00000000K2000000
            0000P2P2P2P20000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000P100000000
            00N10000K10000R1
        """,
        title="Ragtag Crew",
        description="Use the various tools at your disposal to deconstruct the enemy line.",
    ),
    CampaignLevel(
        level_id=11,
        belt=2,
        speed="standard",
        board_str="""
            0000P200K2P20000
            00P2P2P2P2P2P200
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000P1P1000000
            R1000000K10000R1
        """,
        title="Clean Sweep",
        description="Rooks specialize in sweeping up the backline.",
    ),
    CampaignLevel(
        level_id=12,
        belt=2,
        speed="standard",
        board_str="""
            00P2P200K2P2P200
            00P2P2P2P2P2P200
            000000P2P2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000P1P1P1P10000
            000000Q1K1000000
        """,
        title="Queen of Blades",
        description="She rules the board and captures pawns like it's no big deal.",
    ),
    CampaignLevel(
        level_id=13,
        belt=2,
        speed="standard",
        board_str="""
            P2P2P200K2P2P2P2
            P2P2P2P2P2P2P2P2
            0000P2P2P2P20000
            0000000000000000
            0000000000000000
            0000000000000000
            00P1P1P1P1P1P100
            00N1B100K1B1N100
        """,
        title="Helm's Deep",
        description="Haldir's Elves and the Riders of Rohan fight alongside Theoden.",
    ),
    CampaignLevel(
        level_id=14,
        belt=2,
        speed="standard",
        board_str="""
            P2P2P200K2P2P2P2
            P2P2P2P2P2P2P2P2
            00P2P2P2P2P2P200
            0000P2P2P2P20000
            0000000000000000
            0000000000000000
            P1P1P1P1P1P1P1P1
            00N100Q1K1B100R1
        """,
        title="Attack of the Clones",
        description="May the force be with you.",
    ),
    CampaignLevel(
        level_id=15,
        belt=2,
        speed="standard",
        board_str="""
            P2P2P200K2P2P2P2
            P2P2P2P2P2P2P2P2
            P2P2P2P2P2P2P2P2
            P2P2P2P2P2P2P2P2
            0000000000000000
            0000000000000000
            P1P1P1P1P1P1P1P1
            R1N1B1Q1K1B1N1R1
        """,
        title="For the Alliance!",
        description="You must put an end to the Horde once and for all.",
    ),

    # ========== Belt 3: Green (Lightning Speed) ==========
    CampaignLevel(
        level_id=16,
        belt=3,
        speed="lightning",
        board_str="""
            000000Q2K2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            000000Q1K1000000
        """,
        title="Fast as Lightning",
        description="Lightning speed is five times faster. You can still dodge if you're quick, though!",
    ),
    CampaignLevel(
        level_id=17,
        belt=3,
        speed="lightning",
        board_str="""
            0000B200K2B20000
            000000P2P2000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            00N100Q1K100N100
        """,
        title="Lightning McQueen",
        description="McQueen and the crew race to the finish.",
    ),
    CampaignLevel(
        level_id=18,
        belt=3,
        speed="lightning",
        board_str="""
            K200N20000000000
            00N1000000000000
            K100P10000000000
            0000000000000000
            0000000000000000
            0000P20000P20000
            0000000000000000
            0000000000000000
        """,
        title="Quick Attack",
        description="The enemy king is cornered. Finish him off before the reinforcements arrive!",
    ),
    CampaignLevel(
        level_id=19,
        belt=3,
        speed="lightning",
        board_str="""
            00000000K2000000
            0000000000000000
            0000P2000000P200
            00P200P200P200P2
            P2000000P2000000
            0000000000000000
            0000000000000000
            R1000000K10000R1
        """,
        title="The Great Escape",
        description="Get out and grab victory before the wall closes in.",
    ),
    CampaignLevel(
        level_id=20,
        belt=3,
        speed="lightning",
        board_str="""
            00000000K2B2N2R2
            00000000P2P2P2P2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            P1P1P1P1P1000000
            R1N1B1Q1K1000000
        """,
        title="Half and Half",
        description="An empty half leaves the king vulnerable to attack.",
    ),
    CampaignLevel(
        level_id=21,
        belt=3,
        speed="lightning",
        board_str="""
            000000P2P2K20000
            000000P2P2000000
            000000P2P2000000
            000000P2P2000000
            0000000000000000
            0000000000000000
            0000P10000000000
            R1000000K1B10000
        """,
        title="Pillar of Autumn",
        description="Slice through the pillar before it falls. Leave no pawn standing!",
    ),
    CampaignLevel(
        level_id=22,
        belt=3,
        speed="lightning",
        board_str="""
            00000000K2000000
            0000B20000000000
            R200000000000000
            0000000000000000
            000000N200000000
            00000000000000N1
            00000000P1000000
            00R10000K1B10000
        """,
        title="Pressure Point",
        description="Survive the pressure and take control of the situation.",
    ),
    CampaignLevel(
        level_id=23,
        belt=3,
        speed="lightning",
        board_str="""
            00N200Q2K20000R2
            P200P20000P2P200
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            00P1P1P1000000P1
            R1000000K1B1N100
        """,
        title="Need for Speed",
        description="Discover your inner speed demon to overcome the odds.",
    ),

    # ========== Belt 4: Purple ==========
    CampaignLevel(
        level_id=24,
        belt=4,
        speed="standard",
        board_str="""
            P2P2P2P2K2P2P2P2
            P2P2P2P2P2P2P2P2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000P1P1P1P10000
            P1P1P1P1K1P1P1P1
        """,
        title="Pawn Shop",
        description="You won't be able to buy your way to victory here.",
    ),
    CampaignLevel(
        level_id=25,
        belt=4,
        speed="standard",
        board_str="""
            N2N2N2N2K2N2N2N2
            N2N2N2N2N2N2N2N2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000N1N1N1N10000
            N1N1N1N1K1N1N1N1
        """,
        title="A Knightly Battle",
        description="Stop horsing around!",
    ),
    CampaignLevel(
        level_id=26,
        belt=4,
        speed="standard",
        board_str="""
            B2B2B2B2K2B2B2B2
            B2B2B2B2B2B2B2B2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000B1B1B1B10000
            B1B1B1B1K1B1B1B1
        """,
        title="Canterbury vs York",
        description="The bishops have succumbed to a civil war.",
    ),
    CampaignLevel(
        level_id=27,
        belt=4,
        speed="standard",
        board_str="""
            R2R2R2R2K2R2R2R2
            R2R2R2R2R2R2R2R2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000R1R1R1R10000
            R1R1R1R1K1R1R1R1
        """,
        title="Captain Rook",
        description="Charge forward and break through the enemy fortress.",
    ),
    CampaignLevel(
        level_id=28,
        belt=4,
        speed="standard",
        board_str="""
            Q2Q2Q2Q2K2Q2Q2Q2
            Q2Q2Q2Q2Q2Q2Q2Q2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            0000Q1Q1Q1Q10000
            Q1Q1Q1Q1K1Q1Q1Q1
        """,
        title="Queensland",
        description="The land of the Queen and the home of the King.",
    ),
    CampaignLevel(
        level_id=29,
        belt=4,
        speed="standard",
        board_str="""
            R2R2R2R2K2R2R2R2
            B2B2P2P2P2P2B2B2
            0000000000000000
            0000000000000000
            0000000000000000
            0000000000000000
            N1N1P1P1P1P1N1N1
            B1B1B1B1K1B1B1B1
        """,
        title="Fountain of Dreams",
        description="Will you find what you seek?",
    ),
    CampaignLevel(
        level_id=30,
        belt=4,
        speed="standard",
        board_str="""
            P2R2Q2Q2K2Q2R2P2
            00P2B2R2R2B2P200
            0000P2B2B2P20000
            000000P2P2000000
            0000000000000000
            0000000000000000
            R1R1P1P1P1P1R1R1
            N1N1Q1Q1K1Q1N1N1
        """,
        title="Battlefield",
        description="The enemy formation is strong, but breakable.",
    ),
    CampaignLevel(
        level_id=31,
        belt=4,
        speed="standard",
        board_str="""
            Q2Q2Q2Q2K2Q2Q2Q2
            N2N2N2N2B2B2B2B2
            P2P2P2P2P2P2P2P2
            0000000000000000
            0000000000000000
            0000000000000000
            N1N1N1N1N1N1N1N1
            R1R1B1B1K1B1R1R1
        """,
        title="Final Destination",
        description="No items, Fox only, Final Destination.",
    ),

    # ========== Belt 5+: 4-Player (Future) ==========
    # Levels 32+ will be designed later
]


def get_level(level_id: int) -> CampaignLevel | None:
    """Get a level by ID."""
    if 0 <= level_id < len(LEVELS):
        return LEVELS[level_id]
    return None


def get_belt_levels(belt: int) -> list[CampaignLevel]:
    """Get all levels for a belt (8 levels per belt)."""
    start = (belt - 1) * 8
    end = start + 8
    return [lvl for lvl in LEVELS if start <= lvl.level_id < end]
```

### 4. Campaign AI

Campaign games use the existing AI system with difficulty level 3 (advanced). The AI opponent is identified by `"bot:campaign"` in the players dict, which `GameService` recognizes when creating the AI player.

```python
# In GameService.create_campaign_game():
# AI opponent uses difficulty level 3 (advanced)
players = {
    1: f"user:{user_id}",      # Human player
    2: "bot:campaign",          # Campaign AI (difficulty 3)
}
```

Future enhancement: Per-level AI difficulty could be added to `CampaignLevel` to vary challenge across belts.

### 5. Campaign Service

**`server/src/kfchess/campaign/service.py`:**

```python
from dataclasses import dataclass

from kfchess.campaign.board_parser import parse_board_string
from kfchess.campaign.levels import MAX_BELT, get_level
from kfchess.db.repositories.campaign import CampaignProgressRepository
from kfchess.game.engine import GameEngine
from kfchess.game.state import GameState, Speed


@dataclass
class CampaignProgressData:
    """User's campaign progress (domain object)."""

    levels_completed: dict[str, bool]
    belts_completed: dict[str, bool]

    @property
    def current_belt(self) -> int:
        """Highest unlocked belt (1-based)."""
        return min(MAX_BELT, len(self.belts_completed) + 1)

    def is_level_unlocked(self, level_id: int) -> bool:
        """Check if a level is playable."""
        if level_id == 0:
            return True
        # Previous level must be completed
        if str(level_id - 1) in self.levels_completed:
            return True
        # Or this is the first level of an unlocked belt
        belt = level_id // 8 + 1
        belt_first_level = (belt - 1) * 8
        if level_id == belt_first_level and belt <= self.current_belt:
            return True
        return False

    def is_level_completed(self, level_id: int) -> bool:
        return str(level_id) in self.levels_completed


class CampaignService:
    """Campaign business logic."""

    def __init__(self, progress_repo: CampaignProgressRepository):
        self.progress_repo = progress_repo

    async def get_progress(self, user_id: int) -> CampaignProgressData:
        """Get user's campaign progress."""
        data = await self.progress_repo.get_progress(user_id)
        return CampaignProgressData(
            levels_completed=data.get("levelsCompleted", {}),
            belts_completed=data.get("beltsCompleted", {}),
        )

    async def start_level(self, user_id: int, level_id: int) -> GameState | None:
        """Start a campaign level.

        Returns:
            GameState if level can be started, None if locked
        """
        progress = await self.get_progress(user_id)

        if not progress.is_level_unlocked(level_id):
            return None

        level = get_level(level_id)
        if level is None:
            return None

        # Parse board from level definition
        board = parse_board_string(level.board_str, level.board_type)

        # Create players map
        # Player 1 is always the human
        players = {1: f"user:{user_id}"}

        # Add AI opponents
        if level.player_count == 2:
            players[2] = f"c:{level_id}"  # Campaign AI marker
        else:
            # 4-player: AI opponents at positions 2, 3, 4
            for p in range(2, level.player_count + 1):
                players[p] = f"c:{level_id}"

        # Create game with custom board
        speed = Speed.STANDARD if level.speed == "standard" else Speed.LIGHTNING
        state = GameEngine.create_game_from_board(
            speed=speed,
            players=players,
            board=board,
        )

        return state

    async def complete_level(self, user_id: int, level_id: int) -> bool:
        """Mark a level as completed and check belt completion.

        Returns:
            True if a new belt was completed
        """
        progress = await self.get_progress(user_id)

        # Mark level completed
        progress.levels_completed[str(level_id)] = True

        # Check if belt is now complete
        belt = level_id // 8 + 1
        belt_start = (belt - 1) * 8
        belt_end = belt_start + 8

        new_belt_completed = False
        all_complete = all(
            str(lvl) in progress.levels_completed for lvl in range(belt_start, belt_end)
        )

        if all_complete and str(belt) not in progress.belts_completed:
            progress.belts_completed[str(belt)] = True
            new_belt_completed = True

        # Save progress
        await self.progress_repo.update_progress(
            user_id,
            {
                "levelsCompleted": progress.levels_completed,
                "beltsCompleted": progress.belts_completed,
            },
        )

        return new_belt_completed
```

### 6. API Endpoints

**`server/src/kfchess/api/campaign.py`:**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from kfchess.auth.deps import current_active_user, optional_current_user
from kfchess.campaign.levels import BELT_NAMES, MAX_BELT, get_level, LEVELS
from kfchess.campaign.service import CampaignService
from kfchess.db.models import User
from kfchess.services.game_service import GameService

router = APIRouter(prefix="/campaign", tags=["campaign"])


class CampaignProgressResponse(BaseModel):
    levelsCompleted: dict[str, bool]
    beltsCompleted: dict[str, bool]
    currentBelt: int
    maxBelt: int


class CampaignLevelResponse(BaseModel):
    levelId: int
    belt: int
    beltName: str
    title: str
    description: str
    speed: str
    playerCount: int
    isUnlocked: bool
    isCompleted: bool


class StartCampaignGameResponse(BaseModel):
    gameId: str
    playerKey: str
    playerNumber: int


@router.get("/progress")
async def get_progress(user: User = Depends(current_active_user)):
    """Get authenticated user's campaign progress."""
    ...

@router.get("/progress/{user_id}")
async def get_user_progress(user_id: int):
    """Get any user's campaign progress (public, for profiles)."""
    ...

@router.get("/levels")
async def get_levels(user: User | None = Depends(optional_current_user)):
    """Get all campaign levels with unlock/completion status."""
    ...

@router.get("/levels/{level_id}")
async def get_level_detail(level_id: int, user: User | None = Depends(optional_current_user)):
    """Get single level details."""
    ...

@router.post("/levels/{level_id}/start")
async def start_level(
    level_id: int,
    user: User = Depends(current_active_user),
    game_service: GameService = Depends(),
):
    """Start a campaign level. Creates game and returns credentials."""
    # Validates level is unlocked, creates game with custom board
    game_id, player_key, player_number = await game_service.create_campaign_game(
        user_id=user.id,
        level_id=level_id,
    )
    return StartCampaignGameResponse(
        gameId=game_id,
        playerKey=player_key,
        playerNumber=player_number,
    )
```

### 7. Game Service Integration

**`server/src/kfchess/services/game_service.py`:**

Campaign games are tracked via `ManagedGame` which stores:
- `campaign_level_id` - Level being played
- `campaign_user_id` - User who started the campaign game
- `initial_board_str` - Board string for replay reconstruction

```python
async def create_campaign_game(
    self,
    user_id: int,
    level_id: int,
) -> tuple[str, str, int]:
    """Create a campaign game with custom board and AI opponent.

    Returns:
        (game_id, player_key, player_number)
    """
    level = get_level(level_id)
    if not level:
        raise ValueError(f"Level {level_id} not found")

    # Check if level is unlocked
    progress = await self.campaign_service.get_progress(user_id)
    if not progress.is_level_unlocked(level_id):
        raise PermissionError("Level is locked")

    # Parse custom board from level definition
    board = parse_board_string(level.board_str, level.board_type)

    # Create game with human vs AI
    players = {1: f"user:{user_id}", 2: "bot:campaign"}
    speed = Speed.STANDARD if level.speed == "standard" else Speed.LIGHTNING

    state = GameEngine.create_game_from_board(speed, players, board)

    # Track campaign metadata in ManagedGame
    managed_game = ManagedGame(
        state=state,
        campaign_level_id=level_id,
        campaign_user_id=user_id,
        initial_board_str=level.board_str,
    )

    # Auto-start (all players ready)
    # ... game registration and AI setup ...

    return game_id, player_key, 1
```

**Campaign Completion** (`server/src/kfchess/ws/handler.py`):

When a campaign game ends with player 1 winning:

```python
async def _handle_campaign_completion(self, game: ManagedGame, winner: int):
    """Update campaign progress when player wins."""
    if winner == 1 and game.campaign_level_id is not None:
        new_belt = await self.campaign_service.complete_level(
            game.campaign_user_id,
            game.campaign_level_id,
        )
        if new_belt:
            logger.info(f"User {game.campaign_user_id} completed belt {game.campaign_level_id // 8 + 1}")
```

**Replay Integration:**

Campaign replays include:
- `campaign_level_id` in `GameReplay` model (for filtering campaign replays)
- `initial_board_str` for reconstructing custom board during playback

```python
# ReplayEngine uses initial_board_str to reconstruct board
if replay.initial_board_str:
    board = parse_board_string(replay.initial_board_str, replay.board_type)
    state = GameEngine.create_game_from_board(speed, players, board)
```

### 8. Frontend Components

**`client/src/stores/campaign.ts`:**

```typescript
import { create } from "zustand";
import { getCampaignProgress, getCampaignLevels, startCampaignLevel } from "../api/client";
import type { CampaignProgress, CampaignLevel } from "../api/types";

// Belt configuration (client-side constants)
export const BELT_NAMES: Record<number, string> = {
  1: "White", 2: "Yellow", 3: "Green", 4: "Purple",
  5: "Orange", 6: "Blue", 7: "Brown", 8: "Red", 9: "Black",
};

export const BELT_COLORS: Record<number, string> = {
  1: "#ffffff", 2: "#ffd700", 3: "#22c55e", 4: "#a855f7",
  5: "#f97316", 6: "#3b82f6", 7: "#92400e", 8: "#ef4444", 9: "#1f2937",
};

interface CampaignState {
  progress: CampaignProgress | null;
  levels: CampaignLevel[];
  selectedBelt: number;
  isLoading: boolean;
  isStartingLevel: boolean;
  error: string | null;

  init: () => Promise<void>;
  selectBelt: (belt: number) => void;
  startLevel: (levelId: number) => Promise<{ gameId: string; playerKey: string }>;
  clearError: () => void;
  reset: () => void;
}

export const useCampaignStore = create<CampaignState>((set, get) => ({
  progress: null,
  levels: [],
  selectedBelt: 1,
  isLoading: false,
  isStartingLevel: false,
  error: null,

  init: async () => {
    set({ isLoading: true, error: null });
    try {
      // Fetch progress and levels in parallel
      const [progress, levels] = await Promise.all([
        getCampaignProgress(),
        getCampaignLevels(),
      ]);
      set({
        progress,
        levels,
        selectedBelt: progress.currentBelt,
        isLoading: false,
      });
    } catch {
      set({ error: "Failed to load campaign", isLoading: false });
    }
  },

  selectBelt: (belt: number) => set({ selectedBelt: belt }),

  startLevel: async (levelId: number) => {
    set({ isStartingLevel: true });
    try {
      const response = await startCampaignLevel(levelId);
      set({ isStartingLevel: false });
      return response;
    } catch {
      set({ error: "Failed to start level", isStartingLevel: false });
      throw new Error("Failed to start level");
    }
  },

  clearError: () => set({ error: null }),
  reset: () => set({ progress: null, levels: [], selectedBelt: 1, error: null }),
}));

// Selectors
export const getLevelsForBelt = (levels: CampaignLevel[], belt: number) =>
  levels.filter((l) => l.belt === belt);

export const getBeltCompletionCount = (levels: CampaignLevel[], belt: number) =>
  getLevelsForBelt(levels, belt).filter((l) => l.isCompleted).length;
```

**`client/src/pages/Campaign.tsx`:**

```tsx
import { useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { useCampaignStore, getLevelsForBelt } from "../stores/campaign";
import { BeltSelector, LevelGrid } from "../components/campaign";
import "./Campaign.css";

function Campaign() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useAuthStore();
  const { progress, levels, selectedBelt, isLoading, isStartingLevel, error,
          init, selectBelt, startLevel, clearError } = useCampaignStore();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/login?next=/campaign");
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (isAuthenticated) init();
  }, [isAuthenticated, init]);

  const handleStartLevel = useCallback(async (levelId: number) => {
    try {
      const { gameId, playerKey } = await startLevel(levelId);
      navigate(`/game/${gameId}?playerKey=${playerKey}`);
    } catch { /* Error set in store */ }
  }, [startLevel, navigate]);

  if (authLoading) return <div className="campaign-loading">Loading...</div>;
  if (!isAuthenticated) return null;

  const beltLevels = getLevelsForBelt(levels, selectedBelt);

  return (
    <div className="campaign">
      <div className="campaign-header">
        <h1>Campaign Mode</h1>
        <p>Complete missions to earn your belts!</p>
      </div>

      {error && (
        <div className="campaign-error" role="alert">
          {error}
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}

      {isLoading && !progress ? (
        <div className="campaign-loading">Loading campaign...</div>
      ) : (
        <>
          <BeltSelector
            currentBelt={progress?.currentBelt ?? 1}
            maxBelt={progress?.maxBelt ?? 4}
            selectedBelt={selectedBelt}
            beltsCompleted={progress?.beltsCompleted ?? {}}
            onSelectBelt={selectBelt}
          />
          <LevelGrid
            levels={beltLevels}
            onStartLevel={handleStartLevel}
            isStarting={isStartingLevel}
          />
        </>
      )}
    </div>
  );
}

export default Campaign;
```

**`client/src/api/types.ts`:**

```typescript
export interface CampaignProgress {
  levelsCompleted: Record<string, boolean>;
  beltsCompleted: Record<string, boolean>;
  currentBelt: number;
  maxBelt: number;
}

export interface CampaignLevel {
  levelId: number;
  belt: number;
  beltName: string;
  title: string;
  description: string;
  speed: "standard" | "lightning";
  playerCount: number;
  isUnlocked: boolean;
  isCompleted: boolean;
}

export interface StartCampaignGameResponse {
  gameId: string;
  playerKey: string;
  playerNumber: number;
}
```

---

## 4-Player Campaign Design (Future)

### Win Condition

**Last Survivor**: Player 1 wins when they are the only player with a king remaining. AI opponents can eliminate each other, which creates dynamic gameplay.

### Level Design Guidelines (for future levels)

When designing 4-player campaign levels (Belt 5+):

1. **Asymmetric starts**: Player may have different pieces than opponents
2. **AI behavior**: Some AIs may focus on each other rather than the player
3. **Positioning**: Player 1 is always at the East position (col 11)
4. **Board format**: 12 rows, 24 chars per row

Example 4-player board string format:
```
000000R4N4B4Q4K4B4N4R4000000
000000P4P4P4P4P4P4P4P4000000
R3P300000000000000000000P1R1
N3P300000000000000000000P1N1
B3P300000000000000000000P1B1
K3P300000000000000000000P1Q1
Q3P300000000000000000000P1K1
B3P300000000000000000000P1B1
N3P300000000000000000000P1N1
R3P300000000000000000000P1R1
000000P2P2P2P2P2P2P2P2000000
000000R2N2B2K2Q2B2N2R2000000
```

---

## Testing Strategy

### Backend Unit Tests (`server/tests/unit/campaign/`)

1. **`test_board_parser.py`**: All piece types, empty squares, both board sizes, validation errors
2. **`test_service.py`**: CampaignProgressData unlock logic, belt completion detection
3. **`test_levels.py`**: Validate all 32 levels parse correctly, belt mapping

### Backend Integration Tests (`server/tests/integration/`)

1. **`test_campaign_flow.py`**: End-to-end game creation, start level, win detection
2. **`test_campaign_repository.py`**: JSONB upsert, progress persistence
3. **`test_campaign_replay.py`**: Replay saving with custom boards, `initial_board_str` reconstruction

### Frontend Tests

1. **`tests/stores/campaign.test.ts`**: Store actions, selectors, API integration
2. **`tests/components/Campaign.test.tsx`**: Page rendering, auth redirect, level grid

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [x] Add `CampaignProgress` DB model (migration: `011_add_campaign_progress`)
- [x] Implement `CampaignProgressRepository` (with upsert support)
- [x] Implement `board_parser.py` with tests (47 unit tests)
- [x] Add all 32 legacy levels to `levels.py`
- [x] Implement `CampaignService` (with `CampaignProgressData`)
- [x] Integration tests for repository (11 tests)

### Phase 2: API & Game Integration
- [x] Add campaign API endpoints (`/campaign/progress`, `/campaign/levels`, `/campaign/levels/{id}/start`)
- [x] Integrate with `GameService` for campaign games (`create_campaign_game()`)
- [x] Add campaign AI handling (uses difficulty level 3 / advanced)
- [x] Ensure replays are saved for campaign games (with `campaign_level_id` and `initial_board_str`)
- [x] Test campaign game flow end-to-end

### Phase 3: Frontend
- [x] Implement campaign Zustand store with selectors (`client/src/stores/campaign.ts`)
- [x] Create Campaign page with auth check (`client/src/pages/Campaign.tsx`)
- [x] Create BeltSelector with color indicators (`client/src/components/campaign/BeltSelector.tsx`)
- [x] Create LevelGrid with level cards (`client/src/components/campaign/LevelGrid.tsx`)
- [x] Add navigation from Home to Campaign (route in `App.tsx`, button in `Home.tsx`)
- [x] Style campaign UI with responsive design
- [x] Add API types (`CampaignProgress`, `CampaignLevel`, `StartCampaignGameResponse`)
- [x] Frontend tests (store and component tests)

### Phase 4: 4-Player Content (Future)
- [ ] Design 4-player levels (brainstorm session)
- [ ] Add 4-player board string support to parser
- [ ] Implement per-opponent AI configuration (optional)
- [ ] Test 4-player campaign games

### Phase 5: Polish
- [ ] Add belt completion celebration UI (animation/toast on belt complete)
- [x] Replay viewing for campaign games (uses `initial_board_str` for custom board reconstruction)
- [ ] Performance testing with many levels
