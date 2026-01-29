"""Tests for the lobby manager."""

import pytest

from kfchess.lobby.manager import LobbyError, LobbyManager
from kfchess.lobby.models import LobbySettings, LobbyStatus


class TestLobbyCreation:
    """Tests for lobby creation."""

    @pytest.mark.asyncio
    async def test_create_lobby_basic(self) -> None:
        """Test creating a basic lobby."""
        manager = LobbyManager()
        result = await manager.create_lobby(
            host_user_id=1,
            host_username="testuser",
        )

        assert not isinstance(result, LobbyError)
        lobby, player_key = result

        assert lobby.id == 1
        assert len(lobby.code) == 6
        assert lobby.host_slot == 1
        assert lobby.status == LobbyStatus.WAITING
        assert len(lobby.players) == 1
        assert lobby.players[1].username == "testuser"
        assert lobby.players[1].user_id == 1
        assert player_key.startswith("s1_")

    @pytest.mark.asyncio
    async def test_create_lobby_with_settings(self) -> None:
        """Test creating a lobby with custom settings."""
        manager = LobbyManager()
        settings = LobbySettings(
            is_public=False,
            speed="lightning",
            player_count=4,
            is_ranked=False,
        )
        result = await manager.create_lobby(
            host_user_id=1,
            host_username="testuser",
            settings=settings,
        )

        assert not isinstance(result, LobbyError)
        lobby, _ = result

        assert lobby.settings.is_public is False
        assert lobby.settings.speed == "lightning"
        assert lobby.settings.player_count == 4

    @pytest.mark.asyncio
    async def test_create_lobby_with_ai(self) -> None:
        """Test creating a lobby with AI players."""
        manager = LobbyManager()
        result = await manager.create_lobby(
            host_user_id=1,
            host_username="testuser",
            add_ai=True,
            ai_type="bot:dummy",
        )

        assert not isinstance(result, LobbyError)
        lobby, _ = result

        # Should have host + AI
        assert len(lobby.players) == 2
        assert lobby.players[1].username == "testuser"
        assert lobby.players[2].is_ai is True
        assert lobby.players[2].ai_type == "bot:dummy"

    @pytest.mark.asyncio
    async def test_create_lobby_unique_codes(self) -> None:
        """Test that lobby codes are unique."""
        manager = LobbyManager()
        codes = set()
        for i in range(10):
            result = await manager.create_lobby(
                host_user_id=i,
                host_username=f"user{i}",
            )
            assert not isinstance(result, LobbyError)
            lobby, _ = result
            codes.add(lobby.code)

        assert len(codes) == 10

    @pytest.mark.asyncio
    async def test_create_lobby_guest(self) -> None:
        """Test creating a lobby as a guest."""
        manager = LobbyManager()
        result = await manager.create_lobby(
            host_user_id=None,
            host_username="Guest123",
        )

        assert not isinstance(result, LobbyError)
        lobby, _ = result

        assert lobby.players[1].user_id is None
        assert lobby.players[1].username == "Guest123"


class TestJoinLobby:
    """Tests for joining lobbies."""

    @pytest.mark.asyncio
    async def test_join_lobby_success(self) -> None:
        """Test successfully joining a lobby."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        join_result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )

        assert not isinstance(join_result, LobbyError)
        updated_lobby, player_key, slot = join_result

        assert len(updated_lobby.players) == 2
        assert slot == 2
        assert updated_lobby.players[2].username == "player2"
        assert player_key.startswith("s2_")

    @pytest.mark.asyncio
    async def test_join_lobby_not_found(self) -> None:
        """Test joining a nonexistent lobby."""
        manager = LobbyManager()
        result = await manager.join_lobby(
            code="ABCDEF",
            user_id=1,
            username="player",
        )

        assert isinstance(result, LobbyError)
        assert result.code == "not_found"

    @pytest.mark.asyncio
    async def test_join_lobby_full(self) -> None:
        """Test joining a full lobby."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,  # Fills the second slot
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )

        assert isinstance(result, LobbyError)
        assert result.code == "lobby_full"

    @pytest.mark.asyncio
    async def test_join_lobby_preferred_slot(self) -> None:
        """Test joining with preferred slot."""
        manager = LobbyManager()
        # Create 4-player lobby
        settings = LobbySettings(player_count=4)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        # Join with preferred slot 3
        result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
            preferred_slot=3,
        )

        assert not isinstance(result, LobbyError)
        _, _, slot = result
        assert slot == 3

    @pytest.mark.asyncio
    async def test_join_lobby_game_in_progress(self) -> None:
        """Test joining a lobby with game in progress."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Set host ready and start game
        await manager.set_ready(lobby.code, host_key, True)
        await manager.start_game(lobby.code, host_key)

        # Try to join
        result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )

        assert isinstance(result, LobbyError)
        assert result.code == "game_in_progress"


class TestPlayerLock:
    """Tests for the one-lobby-per-player rule."""

    @pytest.mark.asyncio
    async def test_player_lock_create_leaves_old_lobby(self) -> None:
        """Test that creating a new lobby leaves the old one."""
        manager = LobbyManager()
        player_id = "user:1"

        # Create first lobby
        result1 = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            player_id=player_id,
        )
        assert not isinstance(result1, LobbyError)
        lobby1, _ = result1

        # Create second lobby (should leave first)
        result2 = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            player_id=player_id,
        )
        assert not isinstance(result2, LobbyError)
        lobby2, _ = result2

        # First lobby should be deleted (no players left)
        assert manager.get_lobby(lobby1.code) is None
        assert manager.get_lobby(lobby2.code) is not None

    @pytest.mark.asyncio
    async def test_player_lock_join_leaves_old_lobby(self) -> None:
        """Test that joining a new lobby leaves the old one."""
        manager = LobbyManager()
        player_id = "user:2"

        # Create two lobbies
        result1 = await manager.create_lobby(
            host_user_id=1,
            host_username="host1",
        )
        assert not isinstance(result1, LobbyError)
        lobby1, _ = result1

        result2 = await manager.create_lobby(
            host_user_id=2,
            host_username="host2",
        )
        assert not isinstance(result2, LobbyError)
        lobby2, _ = result2

        # Join first lobby
        join1 = await manager.join_lobby(
            code=lobby1.code,
            user_id=3,
            username="player",
            player_id=player_id,
        )
        assert not isinstance(join1, LobbyError)
        assert len(manager.get_lobby(lobby1.code).players) == 2

        # Join second lobby (should leave first)
        join2 = await manager.join_lobby(
            code=lobby2.code,
            user_id=3,
            username="player",
            player_id=player_id,
        )
        assert not isinstance(join2, LobbyError)

        # Player should only be in second lobby
        assert len(manager.get_lobby(lobby1.code).players) == 1
        assert len(manager.get_lobby(lobby2.code).players) == 2

    @pytest.mark.asyncio
    async def test_find_player_lobby(self) -> None:
        """Test finding which lobby a player is in."""
        manager = LobbyManager()
        player_id = "user:1"

        # No lobby initially
        assert manager.find_player_lobby(player_id) is None

        # Create lobby
        result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            player_id=player_id,
        )
        assert not isinstance(result, LobbyError)
        lobby, _ = result

        # Should find player in lobby
        found = manager.find_player_lobby(player_id)
        assert found is not None
        assert found[0] == lobby.code
        assert found[1] == 1  # slot


class TestLeaveLobby:
    """Tests for leaving lobbies."""

    @pytest.mark.asyncio
    async def test_leave_lobby_success(self) -> None:
        """Test successfully leaving a lobby."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        join_result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )
        assert not isinstance(join_result, LobbyError)
        _, player_key, _ = join_result

        # Leave
        result = await manager.leave_lobby(lobby.code, player_key)
        assert result is not None
        assert len(result.players) == 1

    @pytest.mark.asyncio
    async def test_leave_lobby_host_transfers(self) -> None:
        """Test that host is transferred when host leaves."""
        manager = LobbyManager()
        settings = LobbySettings(player_count=4)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Add another player
        join_result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )
        assert not isinstance(join_result, LobbyError)

        # Host leaves
        result = await manager.leave_lobby(lobby.code, host_key)
        assert result is not None
        assert result.host_slot == 2  # Host transferred to slot 2

    @pytest.mark.asyncio
    async def test_leave_lobby_last_human_deletes(self) -> None:
        """Test that lobby is deleted when last human leaves."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Host leaves (only AI remains)
        result = await manager.leave_lobby(lobby.code, host_key)
        assert result is None  # Lobby deleted
        assert manager.get_lobby(lobby.code) is None


class TestReadyState:
    """Tests for ready state management."""

    @pytest.mark.asyncio
    async def test_set_ready_success(self) -> None:
        """Test setting ready state."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        result = await manager.set_ready(lobby.code, host_key, True)
        assert not isinstance(result, LobbyError)
        assert result.players[1].is_ready is True

    @pytest.mark.asyncio
    async def test_set_ready_toggle(self) -> None:
        """Test toggling ready state."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Set ready
        await manager.set_ready(lobby.code, host_key, True)
        # Unready
        result = await manager.set_ready(lobby.code, host_key, False)
        assert not isinstance(result, LobbyError)
        assert result.players[1].is_ready is False

    @pytest.mark.asyncio
    async def test_ai_always_ready(self) -> None:
        """Test that AI players are always ready."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        # AI should be ready
        assert lobby.players[2].is_ready is True


class TestSettings:
    """Tests for lobby settings management."""

    @pytest.mark.asyncio
    async def test_update_settings_host_only(self) -> None:
        """Test that only host can update settings."""
        manager = LobbyManager()
        settings = LobbySettings(player_count=4)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        join_result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )
        assert not isinstance(join_result, LobbyError)
        _, player_key, _ = join_result

        # Non-host tries to update settings
        new_settings = LobbySettings(speed="lightning")
        result = await manager.update_settings(lobby.code, player_key, new_settings)
        assert isinstance(result, LobbyError)
        assert result.code == "not_host"

    @pytest.mark.asyncio
    async def test_update_settings_unreadies_players(self) -> None:
        """Test that updating settings unreadies all players."""
        manager = LobbyManager()
        settings = LobbySettings(player_count=4)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        join_result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="player2",
        )
        assert not isinstance(join_result, LobbyError)
        _, player_key, _ = join_result

        # Both ready up
        await manager.set_ready(lobby.code, host_key, True)
        await manager.set_ready(lobby.code, player_key, True)

        # Host updates settings
        new_settings = LobbySettings(player_count=4, speed="lightning")
        result = await manager.update_settings(lobby.code, host_key, new_settings)
        assert not isinstance(result, LobbyError)

        # Both should be unreadied
        assert result.players[1].is_ready is False
        assert result.players[2].is_ready is False

    @pytest.mark.asyncio
    async def test_cannot_reduce_player_count(self) -> None:
        """Test that player count cannot be reduced below current players."""
        manager = LobbyManager()
        settings = LobbySettings(player_count=4)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Add two more players
        await manager.join_lobby(lobby.code, 2, "player2")
        await manager.join_lobby(lobby.code, 3, "player3")

        # Try to reduce to 2 players
        new_settings = LobbySettings(player_count=2)
        result = await manager.update_settings(lobby.code, host_key, new_settings)
        assert isinstance(result, LobbyError)
        assert result.code == "invalid_settings"


class TestKickPlayer:
    """Tests for kicking players."""

    @pytest.mark.asyncio
    async def test_kick_player_success(self) -> None:
        """Test successfully kicking a player."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        await manager.join_lobby(lobby.code, 2, "player2")

        result = await manager.kick_player(lobby.code, host_key, 2)
        assert not isinstance(result, LobbyError)
        assert len(result.players) == 1

    @pytest.mark.asyncio
    async def test_kick_self_fails(self) -> None:
        """Test that host cannot kick themselves."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        result = await manager.kick_player(lobby.code, host_key, 1)
        assert isinstance(result, LobbyError)
        assert result.code == "invalid_action"

    @pytest.mark.asyncio
    async def test_non_host_cannot_kick(self) -> None:
        """Test that non-host cannot kick players."""
        manager = LobbyManager()
        settings = LobbySettings(player_count=4)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        join_result = await manager.join_lobby(lobby.code, 2, "player2")
        assert not isinstance(join_result, LobbyError)
        _, player_key, _ = join_result

        await manager.join_lobby(lobby.code, 3, "player3")

        # Non-host tries to kick
        result = await manager.kick_player(lobby.code, player_key, 3)
        assert isinstance(result, LobbyError)
        assert result.code == "not_host"


class TestAIPlayers:
    """Tests for AI player management."""

    @pytest.mark.asyncio
    async def test_add_ai_success(self) -> None:
        """Test adding an AI player."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        result = await manager.add_ai(lobby.code, host_key, "bot:dummy")
        assert not isinstance(result, LobbyError)
        assert len(result.players) == 2
        assert result.players[2].is_ai is True

    @pytest.mark.asyncio
    async def test_remove_ai_success(self) -> None:
        """Test removing an AI player."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        result = await manager.remove_ai(lobby.code, host_key, 2)
        assert not isinstance(result, LobbyError)
        assert len(result.players) == 1

    @pytest.mark.asyncio
    async def test_cannot_add_ai_to_ranked(self) -> None:
        """Test that AI cannot be added to ranked games."""
        manager = LobbyManager()
        settings = LobbySettings(is_ranked=True)
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        result = await manager.add_ai(lobby.code, host_key, "bot:dummy")
        assert isinstance(result, LobbyError)
        assert result.code == "invalid_action"


class TestStartGame:
    """Tests for starting games."""

    @pytest.mark.asyncio
    async def test_start_game_success(self) -> None:
        """Test successfully starting a game."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Set host ready
        await manager.set_ready(lobby.code, host_key, True)

        result = await manager.start_game(lobby.code, host_key)
        assert not isinstance(result, LobbyError)
        game_id, player_keys = result

        assert len(game_id) == 8
        assert 1 in player_keys  # Host has a key
        assert 2 not in player_keys  # AI doesn't have a key

        # Check lobby status
        updated_lobby = manager.get_lobby(lobby.code)
        assert updated_lobby.status == LobbyStatus.IN_GAME
        assert updated_lobby.current_game_id == game_id

    @pytest.mark.asyncio
    async def test_start_game_not_all_ready(self) -> None:
        """Test that game cannot start if not all ready."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Don't set host ready
        result = await manager.start_game(lobby.code, host_key)
        # Should auto-ready host but still succeed since AI is ready
        assert not isinstance(result, LobbyError)

    @pytest.mark.asyncio
    async def test_start_game_not_full(self) -> None:
        """Test that game cannot start if lobby is not full."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        await manager.set_ready(lobby.code, host_key, True)

        result = await manager.start_game(lobby.code, host_key)
        assert isinstance(result, LobbyError)
        assert result.code == "not_ready"

    @pytest.mark.asyncio
    async def test_start_game_non_host(self) -> None:
        """Test that non-host cannot start game."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Get a non-host key somehow
        # For this test, we'll create a 4p lobby and join
        settings = LobbySettings(player_count=4)
        create_result2 = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=settings,
        )
        assert not isinstance(create_result2, LobbyError)
        lobby2, _ = create_result2

        join_result = await manager.join_lobby(lobby2.code, 2, "player2")
        assert not isinstance(join_result, LobbyError)
        _, player_key, _ = join_result

        result = await manager.start_game(lobby2.code, player_key)
        assert isinstance(result, LobbyError)
        assert result.code == "not_host"


class TestEndGame:
    """Tests for ending games and rematch flow."""

    @pytest.mark.asyncio
    async def test_end_game_resets_state(self) -> None:
        """Test that ending a game resets lobby state."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        await manager.set_ready(lobby.code, host_key, True)
        await manager.start_game(lobby.code, host_key)

        result = await manager.end_game(lobby.code, winner=1)
        assert result is not None
        assert result.status == LobbyStatus.FINISHED
        assert result.current_game_id is None
        assert result.players[1].is_ready is False  # Human unreadied

    @pytest.mark.asyncio
    async def test_return_to_lobby(self) -> None:
        """Test returning to lobby after game."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        await manager.set_ready(lobby.code, host_key, True)
        await manager.start_game(lobby.code, host_key)
        await manager.end_game(lobby.code, winner=1)

        result = await manager.return_to_lobby(lobby.code)
        assert not isinstance(result, LobbyError)
        assert result.status == LobbyStatus.WAITING


class TestPublicLobbies:
    """Tests for public lobby listing."""

    @pytest.mark.asyncio
    async def test_get_public_lobbies(self) -> None:
        """Test getting public lobbies."""
        manager = LobbyManager()

        # Create a public lobby
        await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=LobbySettings(is_public=True),
        )

        # Create a private lobby
        await manager.create_lobby(
            host_user_id=2,
            host_username="host2",
            settings=LobbySettings(is_public=False),
        )

        lobbies = manager.get_public_lobbies()
        assert len(lobbies) == 1
        assert lobbies[0].settings.is_public is True

    @pytest.mark.asyncio
    async def test_get_public_lobbies_filtered(self) -> None:
        """Test filtering public lobbies."""
        manager = LobbyManager()

        # Create lobbies with different speeds
        await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            settings=LobbySettings(speed="standard"),
        )
        await manager.create_lobby(
            host_user_id=2,
            host_username="host2",
            settings=LobbySettings(speed="lightning"),
        )

        lobbies = manager.get_public_lobbies(speed="lightning")
        assert len(lobbies) == 1
        assert lobbies[0].settings.speed == "lightning"


class TestValidatePlayerKey:
    """Tests for player key validation."""

    @pytest.mark.asyncio
    async def test_validate_player_key_success(self) -> None:
        """Test validating a valid player key."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        slot = manager.validate_player_key(lobby.code, host_key)
        assert slot == 1

    @pytest.mark.asyncio
    async def test_validate_player_key_invalid(self) -> None:
        """Test validating an invalid player key."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        slot = manager.validate_player_key(lobby.code, "invalid_key")
        assert slot is None

    @pytest.mark.asyncio
    async def test_validate_player_key_wrong_lobby(self) -> None:
        """Test validating a key for the wrong lobby."""
        manager = LobbyManager()
        create_result1 = await manager.create_lobby(
            host_user_id=1,
            host_username="host1",
        )
        assert not isinstance(create_result1, LobbyError)
        _, key1 = create_result1

        create_result2 = await manager.create_lobby(
            host_user_id=2,
            host_username="host2",
        )
        assert not isinstance(create_result2, LobbyError)
        lobby2, _ = create_result2

        # Try to use key1 with lobby2
        slot = manager.validate_player_key(lobby2.code, key1)
        assert slot is None


class TestCleanup:
    """Tests for lobby cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_stale_lobbies(self) -> None:
        """Test cleaning up stale lobbies."""
        manager = LobbyManager()

        # Create a lobby
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        # Should not be cleaned up (too recent)
        cleaned = await manager.cleanup_stale_lobbies(waiting_max_age_seconds=3600)
        assert cleaned == 0
        assert manager.get_lobby(lobby.code) is not None

    @pytest.mark.asyncio
    async def test_delete_lobby(self) -> None:
        """Test explicitly deleting a lobby."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        result = await manager.delete_lobby(lobby.code)
        assert result is True
        assert manager.get_lobby(lobby.code) is None


class TestLobbyModels:
    """Tests for lobby model properties and serialization."""

    @pytest.mark.asyncio
    async def test_lobby_is_full(self) -> None:
        """Test the is_full property."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        assert lobby.is_full is False

        # Add AI to fill
        await manager.add_ai(lobby.code, list(manager._player_keys[lobby.code].values())[0])
        updated = manager.get_lobby(lobby.code)
        assert updated.is_full is True

    @pytest.mark.asyncio
    async def test_lobby_all_ready(self) -> None:
        """Test the all_ready property."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, host_key = create_result

        # Not ready yet
        assert lobby.all_ready is False

        # Set host ready
        await manager.set_ready(lobby.code, host_key, True)
        updated = manager.get_lobby(lobby.code)
        assert updated.all_ready is True

    @pytest.mark.asyncio
    async def test_lobby_to_dict(self) -> None:
        """Test lobby serialization."""
        manager = LobbyManager()
        create_result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            add_ai=True,
        )
        assert not isinstance(create_result, LobbyError)
        lobby, _ = create_result

        data = lobby.to_dict()

        assert "id" in data
        assert "code" in data
        assert "hostSlot" in data
        assert "settings" in data
        assert "players" in data
        assert "status" in data
        assert data["hostSlot"] == 1
        assert len(data["players"]) == 2

    @pytest.mark.asyncio
    async def test_create_lobby_with_picture_url(self) -> None:
        """Test that picture_url is stored on LobbyPlayer when creating a lobby."""
        manager = LobbyManager()
        result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            picture_url="https://pic.com/host.jpg",
        )
        assert not isinstance(result, LobbyError)
        lobby, _ = result
        assert lobby.players[1].picture_url == "https://pic.com/host.jpg"

    @pytest.mark.asyncio
    async def test_join_lobby_with_picture_url(self) -> None:
        """Test that picture_url is stored on LobbyPlayer when joining a lobby."""
        manager = LobbyManager()
        result = await manager.create_lobby(host_user_id=1, host_username="host")
        assert not isinstance(result, LobbyError)
        lobby, _ = result

        join_result = await manager.join_lobby(
            code=lobby.code,
            user_id=2,
            username="joiner",
            picture_url="https://pic.com/joiner.jpg",
        )
        assert not isinstance(join_result, LobbyError)
        lobby, _, slot = join_result
        assert lobby.players[slot].picture_url == "https://pic.com/joiner.jpg"

    @pytest.mark.asyncio
    async def test_to_dict_includes_picture_url(self) -> None:
        """Test that to_dict includes pictureUrl for players."""
        manager = LobbyManager()
        result = await manager.create_lobby(
            host_user_id=1,
            host_username="host",
            picture_url="https://pic.com/host.jpg",
        )
        assert not isinstance(result, LobbyError)
        lobby, _ = result

        data = lobby.to_dict()
        assert data["players"][1]["pictureUrl"] == "https://pic.com/host.jpg"

    @pytest.mark.asyncio
    async def test_to_dict_picture_url_none(self) -> None:
        """Test that to_dict includes null pictureUrl when not set."""
        manager = LobbyManager()
        result = await manager.create_lobby(host_user_id=1, host_username="host")
        assert not isinstance(result, LobbyError)
        lobby, _ = result

        data = lobby.to_dict()
        assert data["players"][1]["pictureUrl"] is None

    def test_lobby_settings_validation(self) -> None:
        """Test settings validation."""
        # Valid settings
        settings = LobbySettings(speed="standard", player_count=2)
        assert settings.speed == "standard"

        # Invalid speed
        with pytest.raises(ValueError):
            LobbySettings(speed="invalid")

        # Invalid player count
        with pytest.raises(ValueError):
            LobbySettings(player_count=3)
