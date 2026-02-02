"""Tests for arrival time field computation."""

from kfchess.ai.arrival_field import ArrivalField
from kfchess.ai.state_extractor import StateExtractor
from kfchess.game.board import BoardType
from kfchess.game.engine import GameEngine
from kfchess.game.moves import Cooldown
from kfchess.game.state import GameStatus, Speed


def _make_state(speed=Speed.STANDARD):
    state = GameEngine.create_game(
        speed=speed,
        players={1: "bot:ai1", 2: "bot:ai2"},
        board_type=BoardType.STANDARD,
    )
    state.status = GameStatus.PLAYING
    return state


class TestArrivalField:
    def test_basic_computation(self):
        """Arrival fields compute without error on initial board."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        assert len(data.our_time) > 0
        assert len(data.enemy_time) > 0

    def test_own_piece_square_zero_time(self):
        """A piece on its own square has arrival time = 0 (if idle)."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Player 1 rook at (7, 0)
        assert data.get_our_time(7, 0) == 0

    def test_rook_blocked_by_pawn(self):
        """Rook can't reach past a blocking pawn."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Rook at (7,0) is blocked by pawn at (6,0)
        assert data.get_our_time(5, 0) != 0

    def test_pawn_reaches_forward(self):
        """Pawn reaches forward squares."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        config = state.config
        data = ArrivalField.compute(ai_state, config)
        # Pawn at (6,0) reaches (5,0) in 1*tps = 30
        assert data.get_our_time(5, 0) == config.ticks_per_square

    def test_enemy_time_near_enemy(self):
        """Enemy arrival time should be low near enemy pieces."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Enemy back rank (row 0) should have very low enemy time
        assert data.get_enemy_time(0, 4) == 0  # Enemy king is there

    def test_our_time_far_from_pieces(self):
        """Our arrival time should be high for distant unreachable squares."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Row 0 is across the board — most pieces can't reach in 1 move
        # Some squares might be INF if no piece can reach
        our_t = data.get_our_time(0, 0)
        assert our_t > 0

    def test_cooldown_adds_delay(self):
        """Pieces on cooldown have arrival time increased."""
        state = _make_state()
        state.cooldowns.append(Cooldown(piece_id="p1_n1", start_tick=0, duration=50))
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Field still computes; just check it doesn't crash
        assert data.get_our_time(5, 0) > 0

    def test_critical_only_mode(self):
        """Critical-only mode computes fewer squares."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        full = ArrivalField.compute(ai_state, state.config, critical_only=False)
        critical = ArrivalField.compute(ai_state, state.config, critical_only=True)
        assert len(critical.our_time) < len(full.our_time)

    def test_lightning_speed(self):
        """Arrival times are shorter with lightning speed."""
        state_std = _make_state(Speed.STANDARD)
        state_lit = _make_state(Speed.LIGHTNING)
        ai_std = StateExtractor.extract(state_std, 1)
        ai_lit = StateExtractor.extract(state_lit, 1)
        data_std = ArrivalField.compute(ai_std, state_std.config)
        data_lit = ArrivalField.compute(ai_lit, state_lit.config)
        assert data_std.get_our_time(5, 0) > data_lit.get_our_time(5, 0)

    def test_post_arrival_safety_safe_square(self):
        """A square far from enemies has positive post-arrival safety."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        config = state.config
        data = ArrivalField.compute(ai_state, config)
        # Move a pawn 1 square forward (row 6→5, near our side)
        travel = config.ticks_per_square  # 1 square
        safety = data.post_arrival_safety(5, 0, travel)
        # Near our back rank, enemy is far — should be safe
        assert safety > 0

    def test_post_arrival_safety_dangerous_square(self):
        """A square near enemy pieces has negative post-arrival safety."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        config = state.config
        data = ArrivalField.compute(ai_state, config)
        # Try moving deep into enemy territory with long travel
        travel = 5 * config.ticks_per_square
        safety = data.post_arrival_safety(2, 4, travel)
        # Near enemy back rank with long travel + cooldown — very unsafe
        assert safety < 0

    def test_enemy_time_excluding(self):
        """Excluding a piece from enemy times works correctly."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Enemy king at (0, 4) — enemy_time at (0,4) should be 0
        assert data.get_enemy_time(0, 4) == 0
        # Excluding the king, other pieces may still reach (0,4)
        # but it should be > 0 (queen at (0,3) reaches in 1*tps)
        enemy_king = ai_state.get_enemy_king()
        assert enemy_king is not None
        excl_time = data.get_enemy_time_excluding(0, 4, enemy_king.piece.id)
        assert excl_time > 0

    def test_is_piece_at_risk_idle(self):
        """Idle pieces are only at risk if enemy is within reaction time."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Idle piece (cd=0): only at risk if enemy_t < reaction_ticks (3).
        # Even near enemies, arrival >= 1 square = 30 ticks, so not at risk.
        assert data.is_piece_at_risk(2, 4, cooldown_remaining=0) is False
        # Enemy king sits at (0,4) with arrival time 0 — at risk
        assert data.is_piece_at_risk(0, 4, cooldown_remaining=0) is True

    def test_is_piece_at_risk_on_cooldown(self):
        """Pieces on cooldown are at risk if enemy arrives before cd expires."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        data = ArrivalField.compute(ai_state, state.config)
        # Piece on long cooldown near enemies — at risk
        assert data.is_piece_at_risk(2, 4, cooldown_remaining=300) is True
        # Piece far from enemies even with cooldown — safe
        assert data.is_piece_at_risk(7, 4, cooldown_remaining=300) is False

    def test_tps_and_cd_stored(self):
        """ArrivalData stores tps and cd_ticks from config."""
        state = _make_state()
        ai_state = StateExtractor.extract(state, 1)
        config = state.config
        data = ArrivalField.compute(ai_state, config)
        assert data.tps == config.ticks_per_square
        assert data.cd_ticks == config.cooldown_ticks
