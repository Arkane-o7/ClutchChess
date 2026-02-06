"""Tests for WebSocket handler utilities."""

from clutchchess.ws.handler import _has_state_changed


class TestHasStateChanged:
    """Tests for the _has_state_changed helper function."""

    def test_returns_true_when_events_present(self):
        """Should return True when there are events, regardless of other state."""
        result = _has_state_changed(
            prev_active_move_ids=set(),
            prev_cooldown_ids=set(),
            curr_active_move_ids=set(),
            curr_cooldown_ids=set(),
            has_events=True,
        )
        assert result is True

    def test_returns_true_when_active_move_started(self):
        """Should return True when a new piece starts moving."""
        result = _has_state_changed(
            prev_active_move_ids=set(),
            prev_cooldown_ids=set(),
            curr_active_move_ids={"P:1:6:4"},
            curr_cooldown_ids=set(),
            has_events=False,
        )
        assert result is True

    def test_returns_true_when_active_move_ended(self):
        """Should return True when a piece finishes moving."""
        result = _has_state_changed(
            prev_active_move_ids={"P:1:6:4"},
            prev_cooldown_ids=set(),
            curr_active_move_ids=set(),
            curr_cooldown_ids=set(),
            has_events=False,
        )
        assert result is True

    def test_returns_true_when_cooldown_started(self):
        """Should return True when a piece enters cooldown."""
        result = _has_state_changed(
            prev_active_move_ids=set(),
            prev_cooldown_ids=set(),
            curr_active_move_ids=set(),
            curr_cooldown_ids={"P:1:6:4"},
            has_events=False,
        )
        assert result is True

    def test_returns_true_when_cooldown_ended(self):
        """Should return True when a piece exits cooldown."""
        result = _has_state_changed(
            prev_active_move_ids=set(),
            prev_cooldown_ids={"P:1:6:4"},
            curr_active_move_ids=set(),
            curr_cooldown_ids=set(),
            has_events=False,
        )
        assert result is True

    def test_returns_false_when_nothing_changed(self):
        """Should return False when state is identical."""
        result = _has_state_changed(
            prev_active_move_ids={"P:1:6:4"},
            prev_cooldown_ids={"Q:1:7:3"},
            curr_active_move_ids={"P:1:6:4"},
            curr_cooldown_ids={"Q:1:7:3"},
            has_events=False,
        )
        assert result is False

    def test_returns_false_when_empty_state_unchanged(self):
        """Should return False when both states are empty."""
        result = _has_state_changed(
            prev_active_move_ids=set(),
            prev_cooldown_ids=set(),
            curr_active_move_ids=set(),
            curr_cooldown_ids=set(),
            has_events=False,
        )
        assert result is False

    def test_returns_true_with_multiple_active_moves_changing(self):
        """Should return True when different pieces are moving."""
        result = _has_state_changed(
            prev_active_move_ids={"P:1:6:4", "P:1:6:2"},
            prev_cooldown_ids=set(),
            curr_active_move_ids={"P:1:6:4", "N:1:7:1"},
            curr_cooldown_ids=set(),
            has_events=False,
        )
        assert result is True

    def test_returns_true_with_multiple_cooldowns_changing(self):
        """Should return True when different pieces are on cooldown."""
        result = _has_state_changed(
            prev_active_move_ids=set(),
            prev_cooldown_ids={"P:1:6:4", "R:1:7:0"},
            curr_active_move_ids=set(),
            curr_cooldown_ids={"P:1:6:4", "Q:1:7:3"},
            has_events=False,
        )
        assert result is True

    def test_events_take_priority_over_unchanged_state(self):
        """Events should trigger change even if active moves/cooldowns same."""
        result = _has_state_changed(
            prev_active_move_ids={"P:1:6:4"},
            prev_cooldown_ids={"Q:1:7:3"},
            curr_active_move_ids={"P:1:6:4"},
            curr_cooldown_ids={"Q:1:7:3"},
            has_events=True,
        )
        assert result is True
