"""Tests for compression/decompression routines."""

import math
import pytest
import sys
import os

# Add parent to path for imports without Blender
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from io_coh_anim.formats.compression import (
    compress_quat_5byte,
    decompress_quat_5byte,
    compress_quat_8byte,
    decompress_quat_8byte,
    compress_pos_6byte,
    decompress_pos_6byte,
    compress_pos_uncompressed,
    decompress_pos_uncompressed,
    can_compress_pos_6byte,
)


class TestQuat5Byte:
    """Test 5-byte quaternion compression round-trips."""

    def _assert_quat_close(self, a, b, tol=0.02):
        """Assert two quaternions are close (accounting for sign flip)."""
        # Quaternions q and -q represent the same rotation
        dot = sum(ai * bi for ai, bi in zip(a, b))
        if dot < 0:
            b = tuple(-bi for bi in b)
        for ai, bi in zip(a, b):
            assert abs(ai - bi) < tol, f"Quaternion mismatch: {a} vs {b}"

    def test_identity(self):
        q = (1.0, 0.0, 0.0, 0.0)
        compressed = compress_quat_5byte(q)
        assert len(compressed) == 5
        result = decompress_quat_5byte(compressed)
        self._assert_quat_close(q, result)

    def test_90_degree_x(self):
        angle = math.pi / 2
        s = math.sin(angle / 2)
        c = math.cos(angle / 2)
        q = (c, s, 0.0, 0.0)
        compressed = compress_quat_5byte(q)
        result = decompress_quat_5byte(compressed)
        self._assert_quat_close(q, result)

    def test_45_degree_y(self):
        angle = math.pi / 4
        s = math.sin(angle / 2)
        c = math.cos(angle / 2)
        q = (c, 0.0, s, 0.0)
        compressed = compress_quat_5byte(q)
        result = decompress_quat_5byte(compressed)
        self._assert_quat_close(q, result)

    def test_arbitrary_rotation(self):
        q = (0.5, 0.5, 0.5, 0.5)  # 120 degrees around (1,1,1)
        compressed = compress_quat_5byte(q)
        result = decompress_quat_5byte(compressed)
        self._assert_quat_close(q, result)

    def test_negative_w(self):
        q = (-0.707, 0.707, 0.0, 0.0)
        compressed = compress_quat_5byte(q)
        result = decompress_quat_5byte(compressed)
        self._assert_quat_close(q, result)

    def test_many_random(self):
        """Test a variety of rotations."""
        import random
        random.seed(42)
        for _ in range(100):
            # Random unit quaternion
            w = random.uniform(-1, 1)
            x = random.uniform(-1, 1)
            y = random.uniform(-1, 1)
            z = random.uniform(-1, 1)
            length = math.sqrt(w*w + x*x + y*y + z*z)
            if length < 0.01:
                continue
            q = (w/length, x/length, y/length, z/length)
            compressed = compress_quat_5byte(q)
            result = decompress_quat_5byte(compressed)
            self._assert_quat_close(q, result, tol=0.03)


class TestQuat8Byte:
    """Test 8-byte quaternion compression."""

    def test_round_trip(self):
        q = (0.707, 0.0, 0.707, 0.0)
        compressed = compress_quat_8byte(q)
        assert len(compressed) == 8
        result = decompress_quat_8byte(compressed)
        for a, b in zip(q, result):
            assert abs(a - b) < 0.001


class TestPos6Byte:
    """Test 6-byte position compression."""

    def test_zero(self):
        v = (0.0, 0.0, 0.0)
        compressed = compress_pos_6byte(v)
        assert len(compressed) == 6
        result = decompress_pos_6byte(compressed)
        for a, b in zip(v, result):
            assert abs(a - b) < 0.0001

    def test_small_values(self):
        v = (0.5, -0.3, 0.8)
        compressed = compress_pos_6byte(v)
        result = decompress_pos_6byte(compressed)
        for a, b in zip(v, result):
            assert abs(a - b) < 0.001

    def test_near_limit(self):
        v = (0.999, -0.999, 0.5)
        compressed = compress_pos_6byte(v)
        result = decompress_pos_6byte(compressed)
        for a, b in zip(v, result):
            assert abs(a - b) < 0.001


class TestPosUncompressed:
    """Test uncompressed position (12 bytes)."""

    def test_round_trip(self):
        v = (100.5, -42.3, 0.001)
        compressed = compress_pos_uncompressed(v)
        assert len(compressed) == 12
        result = decompress_pos_uncompressed(compressed)
        for a, b in zip(v, result):
            assert abs(a - b) < 1e-6


class TestCanCompress:
    def test_small_values(self):
        positions = [(0.1, 0.2, 0.3), (-0.5, 0.8, -0.9)]
        assert can_compress_pos_6byte(positions) is True

    def test_large_values(self):
        positions = [(0.1, 0.2, 1.5)]
        assert can_compress_pos_6byte(positions) is False

    def test_empty(self):
        assert can_compress_pos_6byte([]) is True
