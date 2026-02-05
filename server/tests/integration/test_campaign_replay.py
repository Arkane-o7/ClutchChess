"""Integration tests for campaign replay functionality.

These tests verify:
- Campaign replays save with initial_board_str
- ReplayEngine uses custom board for campaign replays
- Database round-trip preserves campaign fields
- Backwards compatibility for non-campaign replays

Run with: uv run pytest tests/integration/test_campaign_replay.py -v
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.campaign.board_parser import parse_board_string
from kfchess.campaign.levels import get_level
from kfchess.db.models import CampaignProgress, User
from kfchess.db.repositories.replays import ReplayRepository
from kfchess.game.board import BoardType
from kfchess.game.replay import Replay, ReplayEngine
from kfchess.game.state import ReplayMove, Speed
from kfchess.services.game_service import GameService

from .conftest import generate_test_id

# Sample custom board string for testing (different from standard starting position)
CUSTOM_BOARD_STR = """
00000000K2000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
0000000000000000
K100000000000000
""".strip()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for campaign replay tests."""
    user = User(
        email="campaign_replay_test@example.com",
        hashed_password="test_hash",
        is_active=True,
        is_verified=True,
        username="CampaignReplayTest",
        ratings={},
    )
    db_session.add(user)
    await db_session.flush()

    yield user

    # Cleanup
    from sqlalchemy import delete

    await db_session.execute(
        delete(CampaignProgress).where(CampaignProgress.user_id == user.id)
    )
    await db_session.delete(user)
    await db_session.commit()


class TestCampaignReplayPersistence:
    """Tests for saving and loading campaign replays with initial_board_str."""

    @pytest.mark.asyncio
    async def test_save_campaign_replay_with_initial_board_str(
        self, db_session: AsyncSession
    ):
        """Test that campaign replays save with initial_board_str."""
        game_id = generate_test_id()
        repository = ReplayRepository(db_session)

        try:
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "u:123", 2: "bot:campaign"},
                moves=[
                    ReplayMove(tick=5, piece_id="K:1:7:0", to_row=6, to_col=0, player=1),
                ],
                total_ticks=100,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(UTC),
                campaign_level_id=0,
                initial_board_str=CUSTOM_BOARD_STR,
            )

            record = await repository.save(game_id, replay)
            await db_session.commit()

            # Verify the record has campaign fields
            assert record.id == game_id
            assert record.campaign_level_id == 0
            assert record.initial_board_str == CUSTOM_BOARD_STR

        finally:
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_load_campaign_replay_preserves_initial_board_str(
        self, db_session: AsyncSession
    ):
        """Test that loading a campaign replay preserves initial_board_str."""
        game_id = generate_test_id()
        repository = ReplayRepository(db_session)

        try:
            # Save a campaign replay
            replay = Replay(
                version=2,
                speed=Speed.LIGHTNING,
                board_type=BoardType.STANDARD,
                players={1: "u:456", 2: "bot:campaign"},
                moves=[],
                total_ticks=50,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(UTC),
                campaign_level_id=5,
                initial_board_str=CUSTOM_BOARD_STR,
            )

            await repository.save(game_id, replay)
            await db_session.commit()

            # Load it back
            loaded = await repository.get_by_id(game_id)

            assert loaded is not None
            assert loaded.campaign_level_id == 5
            assert loaded.initial_board_str == CUSTOM_BOARD_STR

        finally:
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_standard_replay_has_null_initial_board_str(
        self, db_session: AsyncSession
    ):
        """Test that non-campaign replays have null initial_board_str."""
        game_id = generate_test_id()
        repository = ReplayRepository(db_session)

        try:
            # Save a standard (non-campaign) replay
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "u:789", 2: "u:101"},
                moves=[],
                total_ticks=200,
                winner=2,
                win_reason="king_captured",
                created_at=datetime.now(UTC),
                # No campaign fields set
            )

            await repository.save(game_id, replay)
            await db_session.commit()

            # Load it back
            loaded = await repository.get_by_id(game_id)

            assert loaded is not None
            assert loaded.campaign_level_id is None
            assert loaded.initial_board_str is None

        finally:
            await repository.delete(game_id)
            await db_session.commit()


class TestReplayEngineCustomBoard:
    """Tests for ReplayEngine using custom board configurations."""

    def test_replay_engine_uses_initial_board_str(self):
        """Test that ReplayEngine creates custom board from initial_board_str."""
        replay = Replay(
            version=2,
            speed=Speed.STANDARD,
            board_type=BoardType.STANDARD,
            players={1: "u:123", 2: "bot:campaign"},
            moves=[],
            total_ticks=0,
            winner=None,
            win_reason=None,
            created_at=datetime.now(UTC),
            campaign_level_id=0,
            initial_board_str=CUSTOM_BOARD_STR,
        )

        engine = ReplayEngine(replay)
        state = engine.get_state_at_tick(0)

        # Verify the board matches the custom layout
        # CUSTOM_BOARD_STR has:
        # - K2 (black king) at row 0, col 4
        # - K1 (white king) at row 7, col 0
        board = state.board

        # Find kings
        white_king = None
        black_king = None
        for piece in board.pieces:
            if piece.type.value == "K":
                if piece.player == 1:
                    white_king = piece
                elif piece.player == 2:
                    black_king = piece

        assert white_king is not None, "White king should exist"
        assert black_king is not None, "Black king should exist"

        # Verify positions match custom board
        assert white_king.row == 7
        assert white_king.col == 0
        assert black_king.row == 0
        assert black_king.col == 4

        # Verify NOT standard starting position (kings would be at col 4)
        # In standard chess, white king is at row 7, col 4
        assert white_king.col != 4, "Should not be standard starting position"

    def test_replay_engine_uses_standard_board_when_no_initial_board_str(self):
        """Test that ReplayEngine uses standard board when initial_board_str is None."""
        replay = Replay(
            version=2,
            speed=Speed.STANDARD,
            board_type=BoardType.STANDARD,
            players={1: "u:123", 2: "u:456"},
            moves=[],
            total_ticks=0,
            winner=None,
            win_reason=None,
            created_at=datetime.now(UTC),
            # No campaign fields - standard game
        )

        engine = ReplayEngine(replay)
        state = engine.get_state_at_tick(0)

        # Verify standard starting position
        # White king should be at row 7, col 4
        # Black king should be at row 0, col 4
        board = state.board

        white_king = None
        black_king = None
        for piece in board.pieces:
            if piece.type.value == "K":
                if piece.player == 1:
                    white_king = piece
                elif piece.player == 2:
                    black_king = piece

        assert white_king is not None
        assert black_king is not None

        # Standard starting positions
        assert white_king.row == 7
        assert white_king.col == 4
        assert black_king.row == 0
        assert black_king.col == 4

    def test_replay_engine_advances_ticks_with_custom_board(self):
        """Test that ReplayEngine can advance ticks with custom board."""
        replay = Replay(
            version=2,
            speed=Speed.STANDARD,
            board_type=BoardType.STANDARD,
            players={1: "u:123", 2: "bot:campaign"},
            moves=[],  # No moves - just test tick advancement
            total_ticks=50,
            winner=None,
            win_reason=None,
            created_at=datetime.now(UTC),
            campaign_level_id=0,
            initial_board_str=CUSTOM_BOARD_STR,
        )

        engine = ReplayEngine(replay)

        # Get initial state
        state_t0 = engine.get_state_at_tick(0)

        # Verify custom board at tick 0
        white_king = None
        for piece in state_t0.board.pieces:
            if piece.type.value == "K" and piece.player == 1:
                white_king = piece
                break

        assert white_king is not None
        assert white_king.row == 7
        assert white_king.col == 0

        # Advance to tick 25
        state_t25 = engine.get_state_at_tick(25)

        # Verify custom board is still maintained after tick advancement
        white_king_t25 = None
        for piece in state_t25.board.pieces:
            if piece.type.value == "K" and piece.player == 1:
                white_king_t25 = piece
                break

        assert white_king_t25 is not None
        # King should still be at starting position (no moves in this replay)
        assert white_king_t25.row == 7
        assert white_king_t25.col == 0

        # Verify tick advanced correctly
        assert state_t25.current_tick == 25


class TestCampaignGameReplay:
    """Tests for campaign game creation and replay retrieval."""

    async def test_campaign_game_stores_initial_board_str(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that campaign game stores initial_board_str in managed game."""
        game_service = GameService()
        level = get_level(0)
        assert level is not None

        game_id, _, _ = game_service.create_campaign_game(
            level=level,
            user_id=test_user.id,
        )

        managed = game_service.get_managed_game(game_id)
        assert managed is not None

        # Verify initial_board_str is stored
        assert managed.initial_board_str is not None
        assert managed.initial_board_str == level.board_str

    async def test_campaign_replay_includes_initial_board_str(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test that get_replay includes initial_board_str for campaign games."""
        game_service = GameService()
        level = get_level(0)
        assert level is not None

        game_id, _, _ = game_service.create_campaign_game(
            level=level,
            user_id=test_user.id,
        )

        # Force the game to finish so we can get replay
        managed = game_service.get_managed_game(game_id)
        assert managed is not None

        from kfchess.game.state import GameStatus, WinReason

        managed.state.status = GameStatus.FINISHED
        managed.state.winner = 1
        managed.state.win_reason = WinReason.KING_CAPTURED

        # Get replay
        replay = game_service.get_replay(game_id)

        assert replay is not None
        assert replay.campaign_level_id == 0
        assert replay.initial_board_str is not None
        assert replay.initial_board_str == level.board_str


class TestCampaignReplayRoundTrip:
    """Tests for full round-trip: game → replay → save → load → engine."""

    @pytest.mark.asyncio
    async def test_full_campaign_replay_round_trip(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test complete flow: create campaign game → get replay → save → load → replay."""
        game_service = GameService()
        repository = ReplayRepository(db_session)
        level = get_level(0)
        assert level is not None

        # Create campaign game
        game_id, _, _ = game_service.create_campaign_game(
            level=level,
            user_id=test_user.id,
        )

        # Force finish
        managed = game_service.get_managed_game(game_id)
        assert managed is not None

        from kfchess.game.state import GameStatus, WinReason

        managed.state.status = GameStatus.FINISHED
        managed.state.winner = 1
        managed.state.win_reason = WinReason.KING_CAPTURED

        # Get replay from game service
        replay = game_service.get_replay(game_id)
        assert replay is not None
        assert replay.initial_board_str is not None

        try:
            # Save to database
            await repository.save(game_id, replay)
            await db_session.commit()

            # Load from database
            loaded_replay = await repository.get_by_id(game_id)
            assert loaded_replay is not None
            assert loaded_replay.initial_board_str == level.board_str
            assert loaded_replay.campaign_level_id == 0

            # Use ReplayEngine with loaded replay
            engine = ReplayEngine(loaded_replay)
            state = engine.get_state_at_tick(0)

            # Verify the board matches the campaign level's custom layout
            # Parse the expected board to compare
            expected_board = parse_board_string(level.board_str, level.board_type)

            # Count pieces - should match
            assert len(state.board.pieces) == len(expected_board.pieces)

        finally:
            await repository.delete(game_id)
            await db_session.commit()


class TestCampaignReplayEdgeCases:
    """Tests for edge cases and data integrity."""

    @pytest.mark.asyncio
    async def test_large_board_string_persists_correctly(
        self, db_session: AsyncSession
    ):
        """Test that large/complex board strings persist without truncation."""
        game_id = generate_test_id()
        repository = ReplayRepository(db_session)

        # Use a complex board string (level 31 has many pieces)
        level = get_level(31)
        assert level is not None

        try:
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "u:123", 2: "bot:campaign"},
                moves=[],
                total_ticks=100,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(UTC),
                campaign_level_id=31,
                initial_board_str=level.board_str,
            )

            await repository.save(game_id, replay)
            await db_session.commit()

            # Load and verify
            loaded = await repository.get_by_id(game_id)
            assert loaded is not None
            assert loaded.initial_board_str == level.board_str
            assert len(loaded.initial_board_str) == len(level.board_str)

        finally:
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_campaign_replay_with_many_moves(self, db_session: AsyncSession):
        """Test campaign replay with many moves preserves all data."""
        game_id = generate_test_id()
        repository = ReplayRepository(db_session)

        try:
            # Generate many moves
            moves = [
                ReplayMove(
                    tick=i * 15,
                    piece_id=f"P:1:6:{i % 8}",
                    to_row=5,
                    to_col=i % 8,
                    player=1,
                )
                for i in range(200)
            ]

            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "u:123", 2: "bot:campaign"},
                moves=moves,
                total_ticks=3000,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(UTC),
                campaign_level_id=5,
                initial_board_str=CUSTOM_BOARD_STR,
            )

            await repository.save(game_id, replay)
            await db_session.commit()

            # Load and verify
            loaded = await repository.get_by_id(game_id)
            assert loaded is not None
            assert len(loaded.moves) == 200
            assert loaded.initial_board_str == CUSTOM_BOARD_STR
            assert loaded.campaign_level_id == 5

        finally:
            await repository.delete(game_id)
            await db_session.commit()
