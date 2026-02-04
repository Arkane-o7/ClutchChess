"""Campaign system.

Provides campaign mode functionality including:
- Level definitions (32 legacy levels, organized into belts)
- Board string parsing for custom level layouts
- Progress tracking service
"""

from kfchess.campaign.board_parser import parse_board_string
from kfchess.campaign.levels import (
    BELT_NAMES,
    LEVELS,
    MAX_BELT,
    get_belt_levels,
    get_level,
)
from kfchess.campaign.models import CampaignLevel
from kfchess.campaign.service import CampaignProgressData, CampaignService

__all__ = [
    # Models
    "CampaignLevel",
    # Level definitions
    "LEVELS",
    "BELT_NAMES",
    "MAX_BELT",
    "get_level",
    "get_belt_levels",
    # Board parser
    "parse_board_string",
    # Service
    "CampaignService",
    "CampaignProgressData",
]
