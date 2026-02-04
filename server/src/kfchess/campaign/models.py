"""Campaign data models."""

from dataclasses import dataclass

from kfchess.game.board import BoardType


@dataclass
class CampaignLevel:
    """Campaign level definition.

    Attributes:
        level_id: Unique level index (0-based)
        belt: Belt number (1-9)
        speed: Game speed ("standard" or "lightning")
        board_str: Board layout in legacy string format
        board_type: Board dimensions (STANDARD or FOUR_PLAYER)
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
