"""Tests for GEO delta compression/decompression."""

import os
import sys
import math
import struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from io_coh_anim.formats.geo_compression import (
    compress_deltas, decompress_deltas,
    compress_vertices, decompress_vertices,
    compress_normals, decompress_normals,
    compress_uvs, decompress_uvs,
    compress_tri_indices, decompress_tri_indices,
    zip_block, unzip_block,
    PACK_F32, PACK_U32,
    SCALE_VERTICES, SCALE_NORMALS, SCALE_UV1,
)


class TestDeltaCompressionF32:
    """Test float delta compression round-trips."""

    def test_zeros(self):
        """All zeros should compress to tiny size and decompress correctly."""
        values = [0.0] * 9  # 3 Vec3s
        compressed = compress_deltas(values, 3, 3, PACK_F32, SCALE_VERTICES)
        decompressed = decompress_deltas(compressed, 3, 3, PACK_F32)
        assert len(decompressed) == 9
        for v in decompressed:
            assert abs(v) < 1e-4

    def test_simple_values(self):
        """Simple float values should round-trip within quantization tolerance."""
        values = [1.0, 2.0, 3.0, 1.5, 2.5, 3.5]
        compressed = compress_deltas(values, 3, 2, PACK_F32, SCALE_VERTICES)
        decompressed = decompress_deltas(compressed, 3, 2, PACK_F32)
        assert len(decompressed) == 6
        for orig, dec in zip(values, decompressed):
            assert abs(orig - dec) < 0.001, f"Expected ~{orig}, got {dec}"

    def test_vertex_scale(self):
        """Vertex positions with typical CoH values."""
        positions = [
            0.0, 0.0, 42.5,
            0.1, 0.3, 42.8,
            -1.5, 2.0, 40.0,
        ]
        compressed = compress_deltas(positions, 3, 3, PACK_F32, SCALE_VERTICES)
        decompressed = decompress_deltas(compressed, 3, 3, PACK_F32)
        for orig, dec in zip(positions, decompressed):
            assert abs(orig - dec) < 0.001, f"Expected ~{orig}, got {dec}"

    def test_normal_scale(self):
        """Normal vectors with values in [-1, 1]."""
        normals = [
            0.0, 0.0, 1.0,
            0.707, 0.707, 0.0,
            -1.0, 0.0, 0.0,
        ]
        compressed = compress_deltas(normals, 3, 3, PACK_F32, SCALE_NORMALS)
        decompressed = decompress_deltas(compressed, 3, 3, PACK_F32)
        for orig, dec in zip(normals, decompressed):
            assert abs(orig - dec) < 0.01, f"Expected ~{orig}, got {dec}"

    def test_uv_scale(self):
        """UV coordinates."""
        uvs = [0.0, 0.0, 1.0, 0.0, 0.5, 0.5, 1.0, 1.0]
        compressed = compress_deltas(uvs, 2, 4, PACK_F32, SCALE_UV1)
        decompressed = decompress_deltas(compressed, 2, 4, PACK_F32)
        for orig, dec in zip(uvs, decompressed):
            assert abs(orig - dec) < 0.001, f"Expected ~{orig}, got {dec}"

    def test_large_delta(self):
        """Values with large jumps should use code 3 (full float)."""
        values = [0.0, 0.0, 0.0, 100.0, -200.0, 500.0]
        compressed = compress_deltas(values, 3, 2, PACK_F32, SCALE_VERTICES)
        decompressed = decompress_deltas(compressed, 3, 2, PACK_F32)
        for orig, dec in zip(values, decompressed):
            assert abs(orig - dec) < 0.01, f"Expected ~{orig}, got {dec}"


class TestDeltaCompressionU32:
    """Test integer delta compression for triangle indices."""

    def test_sequential(self):
        """Sequential indices (0,1,2,3,4,5,...) should compress well."""
        values = list(range(12))  # 4 triangles
        compressed = compress_deltas(values, 3, 4, PACK_U32, 0)
        decompressed = decompress_deltas(compressed, 3, 4, PACK_U32)
        assert decompressed == values

    def test_triangle_indices(self):
        """Typical triangle index patterns."""
        values = [0, 1, 2, 1, 3, 2, 4, 5, 6, 4, 6, 7]
        compressed = compress_deltas(values, 3, 4, PACK_U32, 0)
        decompressed = decompress_deltas(compressed, 3, 4, PACK_U32)
        assert decompressed == values

    def test_large_indices(self):
        """Large index values."""
        values = [1000, 1001, 1002, 2000, 2001, 2002]
        compressed = compress_deltas(values, 3, 2, PACK_U32, 0)
        decompressed = decompress_deltas(compressed, 3, 2, PACK_U32)
        assert decompressed == values


class TestHighLevelHelpers:
    """Test convenience functions for vertices, normals, UVs, triangles."""

    def test_vertices_round_trip(self):
        positions = [(0.0, 0.0, 42.5), (0.1, 0.3, 42.8), (-1.5, 2.0, 40.0)]
        compressed = compress_vertices(positions, 3)
        decompressed = decompress_vertices(compressed, 3)
        assert len(decompressed) == 3
        for orig, dec in zip(positions, decompressed):
            for a, b in zip(orig, dec):
                assert abs(a - b) < 0.001

    def test_normals_round_trip(self):
        normals = [(0.0, 0.0, 1.0), (0.707, 0.707, 0.0)]
        compressed = compress_normals(normals, 2)
        decompressed = decompress_normals(compressed, 2)
        assert len(decompressed) == 2
        for orig, dec in zip(normals, decompressed):
            for a, b in zip(orig, dec):
                assert abs(a - b) < 0.01

    def test_uvs_round_trip(self):
        uvs = [(0.0, 0.0), (1.0, 0.0), (0.5, 0.5), (1.0, 1.0)]
        compressed = compress_uvs(uvs, 4)
        decompressed = decompress_uvs(compressed, 4)
        assert len(decompressed) == 4
        for orig, dec in zip(uvs, decompressed):
            for a, b in zip(orig, dec):
                assert abs(a - b) < 0.001

    def test_triangles_round_trip(self):
        tris = [(0, 1, 2), (1, 3, 2), (4, 5, 6)]
        compressed = compress_tri_indices(tris, 3)
        decompressed = decompress_tri_indices(compressed, 3)
        assert decompressed == list(tris)

    def test_empty(self):
        assert compress_vertices([], 0) == b''
        assert decompress_vertices(b'', 0) == []
        assert compress_tri_indices([], 0) == b''
        assert decompress_tri_indices(b'', 0) == []


class TestZipBlock:
    """Test zlib compression wrapper."""

    def test_small_data(self):
        """Small data shouldn't be compressed (not worth it)."""
        data = b'\x00' * 10
        compressed, packsize, unpacksize = zip_block(data)
        assert unpacksize == 10

    def test_compressible_data(self):
        """Repetitive data should compress well."""
        data = b'\x00' * 10000
        compressed, packsize, unpacksize = zip_block(data)
        assert unpacksize == 10000
        assert packsize > 0  # Should be compressed
        assert len(compressed) < 10000

    def test_round_trip(self):
        """Compress → decompress should return original data."""
        data = bytes(range(256)) * 100
        compressed, packsize, unpacksize = zip_block(data)
        decompressed = unzip_block(compressed, packsize, unpacksize)
        assert decompressed == data

    def test_uncompressed_round_trip(self):
        """Data that doesn't compress well should pass through."""
        import random
        random.seed(42)
        data = bytes(random.getrandbits(8) for _ in range(100))
        compressed, packsize, unpacksize = zip_block(data)
        decompressed = unzip_block(compressed, packsize, unpacksize)
        assert decompressed == data

    def test_empty(self):
        compressed, packsize, unpacksize = zip_block(b'')
        assert compressed == b''
        assert packsize == 0
        assert unpacksize == 0
