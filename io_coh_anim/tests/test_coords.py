"""Tests for coordinate system conversions."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from io_coh_anim.core.coords import (
    blender_to_game,
    game_to_blender,
    max_to_game,
    game_to_max,
)


class TestCoordConversion:
    def test_blender_to_game_identity(self):
        # Origin stays at origin
        assert blender_to_game((0, 0, 0)) == (0, 0, 0)

    def test_blender_to_game_axes(self):
        # Blender X-right → Game -X
        assert blender_to_game((1, 0, 0)) == (-1, 0, 0)
        # Blender Y-forward → Game -Z
        assert blender_to_game((0, 1, 0)) == (0, 0, -1)
        # Blender Z-up → Game Y-up
        assert blender_to_game((0, 0, 1)) == (0, 1, 0)

    def test_round_trip(self):
        original = (3.5, -1.2, 7.8)
        converted = blender_to_game(original)
        back = game_to_blender(converted)
        for a, b in zip(original, back):
            assert abs(a - b) < 1e-10

    def test_max_is_same_as_blender(self):
        v = (1.5, -2.5, 3.5)
        assert max_to_game(v) == blender_to_game(v)
        assert game_to_max(v) == game_to_blender(v)
