"""Integration tests for ReplayRepository.

These tests hit the real PostgreSQL database to catch issues like:
- Timezone handling (naive vs aware datetimes)
- JSON serialization edge cases
- Constraint violations
- Type coercion issues

Run with: uv run pytest tests/integration/test_replay_repository.py -v
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kfchess.db.repositories.replays import ReplayRepository
from kfchess.game.board import BoardType
from kfchess.game.replay import Replay
from kfchess.game.state import ReplayMove, Speed

from .conftest import generate_test_id


class TestReplayRepositorySaveIntegration:
    """Integration tests for saving replays to PostgreSQL."""

    @pytest.mark.asyncio
    async def test_save_with_timezone_aware_datetime(self, db_session: AsyncSession):
        """Test that timezone-aware datetimes are handled correctly.

        This test catches the bug where PostgreSQL's TIMESTAMP WITHOUT TIME ZONE
        column couldn't accept timezone-aware Python datetimes.
        """
        game_id = generate_test_id()

        try:
            # Create replay with timezone-aware datetime (like GameState.finished_at)
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "player1", 2: "player2"},
                moves=[
                    ReplayMove(tick=5, piece_id="P:1:6:4", to_row=4, to_col=4, player=1),
                ],
                total_ticks=100,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(timezone.utc),  # Timezone-aware!
            )

            repository = ReplayRepository(db_session)
            record = await repository.save(game_id, replay)
            await db_session.commit()

            assert record.id == game_id
            assert record.winner == 1

            # Verify we can read it back
            loaded = await repository.get_by_id(game_id)
            assert loaded is not None
            assert loaded.winner == 1
            assert loaded.total_ticks == 100
        finally:
            # Cleanup
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_save_with_naive_datetime(self, db_session: AsyncSession):
        """Test that naive datetimes also work correctly."""
        game_id = generate_test_id()

        try:
            replay = Replay(
                version=2,
                speed=Speed.LIGHTNING,
                board_type=BoardType.STANDARD,
                players={1: "player1", 2: "player2"},
                moves=[],
                total_ticks=50,
                winner=2,
                win_reason="king_captured",
                created_at=datetime.now(),  # Naive datetime
            )

            repository = ReplayRepository(db_session)
            record = await repository.save(game_id, replay)
            await db_session.commit()

            assert record.id == game_id
        finally:
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_save_with_none_datetime(self, db_session: AsyncSession):
        """Test that None datetime defaults to now()."""
        game_id = generate_test_id()

        try:
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "player1", 2: "player2"},
                moves=[],
                total_ticks=0,
                winner=None,
                win_reason=None,
                created_at=None,  # Will default to now()
            )

            repository = ReplayRepository(db_session)
            record = await repository.save(game_id, replay)
            await db_session.commit()

            assert record.id == game_id
            assert record.created_at is not None
        finally:
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_save_idempotent(self, db_session: AsyncSession):
        """Test that saving the same replay twice doesn't fail."""
        game_id = generate_test_id()

        try:
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={1: "player1", 2: "player2"},
                moves=[],
                total_ticks=100,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(timezone.utc),
            )

            repository = ReplayRepository(db_session)

            # Save first time
            record1 = await repository.save(game_id, replay)
            await db_session.commit()

            # Save again (should be idempotent)
            record2 = await repository.save(game_id, replay)

            assert record1.id == record2.id
        finally:
            await repository.delete(game_id)
            await db_session.commit()


class TestReplayRepositoryJsonHandling:
    """Integration tests for JSON serialization edge cases."""

    @pytest.mark.asyncio
    async def test_save_with_many_moves(self, db_session: AsyncSession):
        """Test saving a replay with many moves."""
        game_id = generate_test_id()

        try:
            # Generate many moves
            moves = [
                ReplayMove(tick=i * 10, piece_id=f"P:1:6:{i % 8}", to_row=5, to_col=i % 8, player=1)
                for i in range(500)
            ]

            replay = Replay(
                version=2,
                speed=Speed.LIGHTNING,
                board_type=BoardType.STANDARD,
                players={1: "player1", 2: "player2"},
                moves=moves,
                total_ticks=5000,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(timezone.utc),
            )

            repository = ReplayRepository(db_session)
            record = await repository.save(game_id, replay)
            await db_session.commit()

            # Verify all moves are preserved
            loaded = await repository.get_by_id(game_id)
            assert loaded is not None
            assert len(loaded.moves) == 500
        finally:
            await repository.delete(game_id)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_save_with_special_characters_in_player_id(self, db_session: AsyncSession):
        """Test that player IDs with special characters are handled."""
        game_id = generate_test_id()

        try:
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.STANDARD,
                players={
                    1: "user:abc_123-def",
                    2: "bot:dummy",
                },
                moves=[],
                total_ticks=100,
                winner=1,
                win_reason="king_captured",
                created_at=datetime.now(timezone.utc),
            )

            repository = ReplayRepository(db_session)
            record = await repository.save(game_id, replay)
            await db_session.commit()

            loaded = await repository.get_by_id(game_id)
            assert loaded is not None
            assert loaded.players[1] == "user:abc_123-def"
            assert loaded.players[2] == "bot:dummy"
        finally:
            await repository.delete(game_id)
            await db_session.commit()


class TestReplayRepositoryFourPlayer:
    """Integration tests for 4-player replays."""

    @pytest.mark.asyncio
    async def test_save_four_player_replay(self, db_session: AsyncSession):
        """Test saving a 4-player game replay."""
        game_id = generate_test_id()

        try:
            replay = Replay(
                version=2,
                speed=Speed.STANDARD,
                board_type=BoardType.FOUR_PLAYER,
                players={
                    1: "player1",
                    2: "player2",
                    3: "player3",
                    4: "player4",
                },
                moves=[
                    ReplayMove(tick=5, piece_id="P:1:11:5", to_row=9, to_col=5, player=1),
                    ReplayMove(tick=10, piece_id="P:2:5:2", to_row=5, to_col=4, player=2),
                    ReplayMove(tick=15, piece_id="P:3:2:8", to_row=4, to_col=8, player=3),
                    ReplayMove(tick=20, piece_id="P:4:8:11", to_row=8, to_col=9, player=4),
                ],
                total_ticks=200,
                winner=3,
                win_reason="last_standing",
                created_at=datetime.now(timezone.utc),
            )

            repository = ReplayRepository(db_session)
            record = await repository.save(game_id, replay)
            await db_session.commit()

            loaded = await repository.get_by_id(game_id)
            assert loaded is not None
            assert loaded.board_type == BoardType.FOUR_PLAYER
            assert len(loaded.players) == 4
            assert loaded.winner == 3
        finally:
            await repository.delete(game_id)
            await db_session.commit()


class TestReplayRepositoryDelete:
    """Integration tests for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_removes_from_database(self, db_session: AsyncSession):
        """Test that delete actually removes the record."""
        game_id = generate_test_id()

        replay = Replay(
            version=2,
            speed=Speed.STANDARD,
            board_type=BoardType.STANDARD,
            players={1: "player1", 2: "player2"},
            moves=[],
            total_ticks=100,
            winner=1,
            win_reason="king_captured",
            created_at=datetime.now(timezone.utc),
        )

        repository = ReplayRepository(db_session)
        await repository.save(game_id, replay)
        await db_session.commit()

        # Verify it exists
        assert await repository.exists(game_id)

        # Delete it
        deleted = await repository.delete(game_id)
        await db_session.commit()

        assert deleted is True
        assert not await repository.exists(game_id)
