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
| Campaign AI behavior | New AI level "campaign" (internal level -1) that matches intermediate (level 2) configuration; can be tuned later |
| 4-player win condition | Last survivor — player wins when all opponent kings are captured (AI can eliminate each other) |
| Progress reset | Not needed — users can replay any completed level |
| Replay integration | Yes — campaign games are saved as replays and function as normal games |
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
│   ├── models.py           # CampaignLevel dataclass, progress model
│   ├── board_parser.py     # Parse board strings → Board objects
│   └── service.py          # Campaign business logic
├── api/
│   └── campaigns.py        # REST endpoints
├── ws/
│   └── game.py             # (existing, add campaign game support)
└── db/
    ├── models.py           # Add CampaignProgress model
    └── repositories/
        └── campaign.py     # Campaign progress repository

client/src/
├── pages/
│   └── Campaign.tsx        # Campaign page component
├── stores/
│   └── campaign.ts         # Zustand store for campaign state
├── components/
│   └── campaign/
│       ├── LevelSelect.tsx # Level selection UI
│       ├── BeltProgress.tsx# Belt progress display
│       └── LevelCard.tsx   # Individual level card
└── data/
    └── campaignLevels.ts   # Level metadata (titles, descriptions)
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
│  GET /api/campaigns/progress                                │
│  POST /api/campaigns/levels/{level}/start                   │
│  (progress updated automatically on game win)               │
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

**Add to `server/src/kfchess/ai/kungfu_ai.py` or `services/game_service.py`:**

```python
# Campaign AI is a distinct difficulty level that currently matches intermediate (level 2)
# but can be tuned independently in the future.

_DIFFICULTY_MAP: dict[str, int] = {
    "novice": 1,
    "intermediate": 2,
    "advanced": 3,
    "campaign": -1,  # Special campaign level
}

def _create_ai(difficulty: str, speed: Speed) -> AIPlayer:
    """Create an AI player with the given difficulty."""
    level = _DIFFICULTY_MAP.get(difficulty, 2)

    if level == -1:
        # Campaign AI: uses intermediate (level 2) configuration
        # This is separate so we can tune it independently later
        return KungFuAI(level=2, speed=speed)
    else:
        return KungFuAI(level=level, speed=speed)
```

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

**`server/src/kfchess/api/campaigns.py`:**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from kfchess.auth.deps import current_active_user
from kfchess.campaign.levels import BELT_NAMES, MAX_BELT, get_level
from kfchess.campaign.service import CampaignService
from kfchess.db.models import User

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class ProgressResponse(BaseModel):
    levels_completed: dict[str, bool]
    belts_completed: dict[str, bool]
    current_belt: int
    max_belt: int


class LevelInfo(BaseModel):
    level_id: int
    belt: int
    title: str
    description: str
    speed: str
    is_4player: bool
    is_unlocked: bool
    is_completed: bool


class StartLevelResponse(BaseModel):
    game_id: str
    player_key: str


@router.get("/progress", response_model=ProgressResponse)
async def get_progress(
    user: User = Depends(current_active_user),
    campaign_service: CampaignService = Depends(),
):
    """Get user's campaign progress."""
    progress = await campaign_service.get_progress(user.id)
    return ProgressResponse(
        levels_completed=progress.levels_completed,
        belts_completed=progress.belts_completed,
        current_belt=progress.current_belt,
        max_belt=MAX_BELT,
    )


@router.get("/belts/{belt}/levels", response_model=list[LevelInfo])
async def get_belt_levels(
    belt: int,
    user: User = Depends(current_active_user),
    campaign_service: CampaignService = Depends(),
):
    """Get all levels for a belt."""
    if belt < 1 or belt > MAX_BELT:
        raise HTTPException(status_code=404, detail="Belt not found")

    progress = await campaign_service.get_progress(user.id)
    levels = []

    for level_idx in range((belt - 1) * 8, belt * 8):
        level = get_level(level_idx)
        if level is None:
            continue

        levels.append(
            LevelInfo(
                level_id=level.level_id,
                belt=level.belt,
                title=level.title,
                description=level.description,
                speed=level.speed,
                is_4player=level.player_count > 2,
                is_unlocked=progress.is_level_unlocked(level.level_id),
                is_completed=progress.is_level_completed(level.level_id),
            )
        )

    return levels


@router.post("/levels/{level_id}/start", response_model=StartLevelResponse)
async def start_level(
    level_id: int,
    user: User = Depends(current_active_user),
    campaign_service: CampaignService = Depends(),
    game_service=Depends(),  # GameService dependency
):
    """Start a campaign level."""
    state = await campaign_service.start_level(user.id, level_id)

    if state is None:
        raise HTTPException(status_code=403, detail="Level is locked")

    # Register game with game service (treated as normal game with replay)
    game_id, player_key = await game_service.register_campaign_game(
        state=state,
        user_id=user.id,
        level_id=level_id,
    )

    return StartLevelResponse(game_id=game_id, player_key=player_key)
```

### 7. Game Service Integration

**Additions to `server/src/kfchess/services/game_service.py`:**

```python
# Track campaign games for progress updates
campaign_games: dict[str, int] = {}  # game_id → level_id


async def register_campaign_game(
    self,
    state: GameState,
    user_id: int,
    level_id: int,
) -> tuple[str, str]:
    """Register a campaign game and return game_id + player_key.

    Campaign games are treated as normal games:
    - Replays are saved on completion
    - Game events are broadcast via WebSocket
    - Progress is updated when player 1 wins (or is last survivor in 4P)
    """
    game_id = state.game_id
    player_key = str(uuid.uuid4())

    # Store campaign level association
    self.campaign_games[game_id] = level_id

    # Create AI opponents
    level = get_level(level_id)
    if level:
        for player_num, player_id in state.players.items():
            if player_id.startswith("c:"):
                # Campaign AI (uses "campaign" difficulty)
                ai = self._create_ai("campaign", state.speed)
                self._ai_players[game_id, player_num] = ai

    # Register game normally (enables replay saving)
    await self._register_game(game_id, state, {1: player_key})

    return game_id, player_key


async def on_game_over(self, game_id: str, winner: int):
    """Handle game completion (called for all games including campaign)."""
    # Save replay (works for both multiplayer and campaign games)
    await self._save_replay(game_id)

    # Handle campaign progress if this is a campaign game
    if game_id in self.campaign_games:
        level_id = self.campaign_games[game_id]

        # Player 1 wins if:
        # - 2P mode: winner == 1
        # - 4P mode: winner == 1 (last survivor)
        if winner == 1:
            state = self._games.get(game_id)
            if state:
                user_id = int(state.players[1].split(":")[1])
                new_belt = await self.campaign_service.complete_level(user_id, level_id)

                # Optionally notify client of belt completion
                if new_belt:
                    await self._broadcast_belt_completed(game_id, level_id // 8 + 1)

        del self.campaign_games[game_id]
```

### 8. Frontend Components

**`client/src/stores/campaign.ts`:**

```typescript
import { create } from "zustand";
import { api } from "../api/client";

interface CampaignProgress {
  levelsCompleted: Record<string, boolean>;
  beltsCompleted: Record<string, boolean>;
  currentBelt: number;
  maxBelt: number;
}

interface LevelInfo {
  levelId: number;
  belt: number;
  title: string;
  description: string;
  speed: string;
  is4Player: boolean;
  isUnlocked: boolean;
  isCompleted: boolean;
}

interface CampaignState {
  progress: CampaignProgress | null;
  currentBeltLevels: LevelInfo[];
  selectedBelt: number;
  loading: boolean;
  error: string | null;

  fetchProgress: () => Promise<void>;
  fetchBeltLevels: (belt: number) => Promise<void>;
  selectBelt: (belt: number) => void;
  startLevel: (levelId: number) => Promise<{ gameId: string; playerKey: string }>;
}

export const useCampaignStore = create<CampaignState>((set, get) => ({
  progress: null,
  currentBeltLevels: [],
  selectedBelt: 1,
  loading: false,
  error: null,

  fetchProgress: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get("/api/campaigns/progress");
      set({
        progress: response.data,
        selectedBelt: response.data.currentBelt,
        loading: false,
      });
    } catch (error) {
      set({ error: "Failed to load progress", loading: false });
    }
  },

  fetchBeltLevels: async (belt: number) => {
    set({ loading: true });
    try {
      const response = await api.get(`/api/campaigns/belts/${belt}/levels`);
      set({ currentBeltLevels: response.data, loading: false });
    } catch (error) {
      set({ error: "Failed to load levels", loading: false });
    }
  },

  selectBelt: (belt: number) => {
    set({ selectedBelt: belt });
    get().fetchBeltLevels(belt);
  },

  startLevel: async (levelId: number) => {
    const response = await api.post(`/api/campaigns/levels/${levelId}/start`);
    return response.data;
  },
}));
```

**`client/src/pages/Campaign.tsx`:**

```tsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useCampaignStore } from "../stores/campaign";
import { useAuthStore } from "../stores/auth";
import { BeltSelector } from "../components/campaign/BeltSelector";
import { LevelGrid } from "../components/campaign/LevelGrid";

export function Campaign() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const {
    progress,
    currentBeltLevels,
    selectedBelt,
    loading,
    fetchProgress,
    fetchBeltLevels,
    selectBelt,
    startLevel,
  } = useCampaignStore();

  useEffect(() => {
    if (!user) {
      navigate("/login?next=/campaign");
      return;
    }
    fetchProgress();
  }, [user]);

  useEffect(() => {
    if (progress) {
      fetchBeltLevels(selectedBelt);
    }
  }, [progress, selectedBelt]);

  const handleStartLevel = async (levelId: number) => {
    const { gameId, playerKey } = await startLevel(levelId);
    navigate(`/game/${gameId}?key=${playerKey}`);
  };

  if (!user) return null;
  if (loading && !progress) return <div>Loading...</div>;

  return (
    <div className="campaign-page">
      <h1>Campaign Mode</h1>

      <BeltSelector
        currentBelt={progress?.currentBelt ?? 1}
        maxBelt={progress?.maxBelt ?? 1}
        selectedBelt={selectedBelt}
        beltsCompleted={progress?.beltsCompleted ?? {}}
        onSelectBelt={selectBelt}
      />

      <LevelGrid levels={currentBeltLevels} onStartLevel={handleStartLevel} />
    </div>
  );
}
```

**`client/src/data/campaignLevels.ts`:**

```typescript
export const BELT_NAMES = [
  "", // 0 unused
  "White",
  "Yellow",
  "Green",
  "Purple",
  "Orange",
  "Blue",
  "Brown",
  "Red",
  "Black",
];

export const MAX_BELT = 4;

// Level metadata is fetched from the server API
// This file contains only constants needed client-side
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

### Unit Tests

1. **Board parser**: Test all piece types, empty squares, both board sizes
2. **Progress logic**: Test unlock conditions, belt completion
3. **Level definitions**: Validate all 32 levels parse correctly

### Integration Tests

1. **Start level flow**: User → API → GameService → WebSocket
2. **Win detection**: Campaign game over triggers progress update
3. **Replay saving**: Campaign games are saved as replays
4. **Progress persistence**: Progress survives restart

### E2E Tests

1. **Complete belt**: Play through 8 levels, verify belt unlocks
2. **Replay a level**: Complete level, replay from history

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
- [ ] Add campaign API endpoints
- [ ] Integrate with `GameService` for campaign games
- [ ] Add campaign AI handling (level -1 → intermediate config)
- [ ] Ensure replays are saved for campaign games
- [ ] Test campaign game flow end-to-end

### Phase 3: Frontend
- [x] Implement campaign Zustand store (`client/src/stores/campaign.ts`)
- [x] Create Campaign page component (`client/src/pages/Campaign.tsx`)
- [x] Create BeltSelector and LevelGrid components (`client/src/components/campaign/`)
- [x] Add navigation from Home to Campaign (route in `App.tsx`, button in `Home.tsx`)
- [x] Style campaign UI (`Campaign.css`, `BeltSelector.css`, `LevelGrid.css`)
- [x] Add API types and functions (`api/types.ts`, `api/client.ts`)
- [x] Frontend tests (25 tests: 20 store + 5 component)

### Phase 4: 4-Player Content (Future)
- [ ] Design 4-player levels (brainstorm session)
- [ ] Add 4-player board string support to parser
- [ ] Implement per-opponent AI configuration (optional)
- [ ] Test 4-player campaign games

### Phase 5: Polish
- [ ] Add belt completion celebration UI
- [ ] Test replay viewing for campaign games
- [ ] Performance testing with many levels
