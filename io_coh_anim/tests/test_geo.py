"""Tests for GEO binary format reading and writing."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from io_coh_anim.formats.geo import read_geo, write_geo, GeoFile, GeoModel, GeoHeader, TexID
from io_coh_anim.tests.conftest import (
    GEO_CAPSULE, GEO_FEM_BOOT, GEO_STATUE,
    GEO_OBJECT_DIR, GEO_PLAYER_DIR, GEO_DIR,
    skip_no_geo,
)


@skip_no_geo
class TestReadGeo:
    """Test reading real .geo files."""

    def test_read_capsule(self):
        geo = read_geo(GEO_CAPSULE)
        assert geo.version == 8
        assert len(geo.models) > 0

    def test_read_capsule_geometry(self):
        geo = read_geo(GEO_CAPSULE)
        model = geo.models[0]
        assert model.vert_count > 0
        assert model.tri_count > 0
        assert len(model.vertices) == model.vert_count
        assert len(model.triangles) == model.tri_count

    def test_read_capsule_normals(self):
        geo = read_geo(GEO_CAPSULE)
        model = geo.models[0]
        if model.normals:
            assert len(model.normals) == model.vert_count
            # Normals should be roughly unit length
            for n in model.normals[:10]:
                length_sq = sum(c * c for c in n)
                assert 0.5 < length_sq < 1.5, f"Bad normal length: {n}"

    def test_read_capsule_uvs(self):
        geo = read_geo(GEO_CAPSULE)
        model = geo.models[0]
        if model.uvs:
            assert len(model.uvs) == model.vert_count
            for uv in model.uvs[:10]:
                assert len(uv) == 2

    def test_read_capsule_tex_names(self):
        geo = read_geo(GEO_CAPSULE)
        assert len(geo.tex_names) > 0

    def test_read_fem_boot(self):
        """Player library GEO should have skinning data."""
        if not os.path.exists(GEO_FEM_BOOT):
            pytest.skip("fem_boot.geo not found")
        geo = read_geo(GEO_FEM_BOOT)
        assert len(geo.models) > 0
        model = geo.models[0]
        assert model.vert_count > 0

    def test_read_statue(self):
        if not os.path.exists(GEO_STATUE):
            pytest.skip("statue geo not found")
        geo = read_geo(GEO_STATUE)
        assert len(geo.models) > 0
        for model in geo.models:
            assert model.vert_count >= 0
            if model.vert_count > 0:
                assert len(model.vertices) == model.vert_count

    def test_read_multiple_geo_files(self):
        """Read a batch of GEO files without errors."""
        geo_files = []
        for root, dirs, files in os.walk(GEO_DIR):
            for fname in files:
                if fname.endswith('.geo'):
                    geo_files.append(os.path.join(root, fname))
            if len(geo_files) >= 20:
                break

        assert len(geo_files) > 0, "No GEO files found"
        for filepath in geo_files[:20]:
            try:
                geo = read_geo(filepath)
                assert geo.version >= 1
                assert len(geo.models) >= 0
            except Exception as e:
                pytest.fail(f"Failed to read {filepath}: {e}")


class TestWriteGeo:
    """Test writing GEO files (no sample files needed)."""

    def test_write_minimal(self):
        """Write and read back a minimal GEO file."""
        geo = GeoFile(
            version=8,
            headers=[GeoHeader(name="test.wrl", model_count=1)],
            models=[
                GeoModel(
                    name="GEO_test",
                    vert_count=3,
                    tri_count=1,
                    vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
                    normals=[(0.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 0.0, 1.0)],
                    uvs=[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
                    triangles=[(0, 1, 2)],
                    tex_ids=[TexID(id=0, count=1)],
                    radius=1.0,
                    min=(0.0, 0.0, 0.0),
                    max=(1.0, 1.0, 0.0),
                ),
            ],
            tex_names=["test_texture"],
            obj_names=["GEO_test"],
        )

        with tempfile.NamedTemporaryFile(suffix='.geo', delete=False) as f:
            tmp_path = f.name

        try:
            write_geo(tmp_path, geo)
            reloaded = read_geo(tmp_path)

            assert reloaded.version == 8
            assert len(reloaded.models) == 1
            model = reloaded.models[0]
            assert model.vert_count == 3
            assert model.tri_count == 1
            assert len(model.vertices) == 3
            assert len(model.triangles) == 1

            # Verify vertex positions within delta compression tolerance
            for orig, reloaded_v in zip(geo.models[0].vertices, model.vertices):
                for a, b in zip(orig, reloaded_v):
                    assert abs(a - b) < 0.01, f"Vertex mismatch: {orig} vs {reloaded_v}"
        finally:
            os.unlink(tmp_path)

    def test_write_quad(self):
        """Write a quad (2 triangles, 4 vertices)."""
        geo = GeoFile(
            version=8,
            headers=[GeoHeader(name="quad.wrl", model_count=1)],
            models=[
                GeoModel(
                    name="GEO_quad",
                    vert_count=4,
                    tri_count=2,
                    vertices=[
                        (-1.0, -1.0, 0.0),
                        (1.0, -1.0, 0.0),
                        (1.0, 1.0, 0.0),
                        (-1.0, 1.0, 0.0),
                    ],
                    normals=[
                        (0.0, 0.0, 1.0),
                        (0.0, 0.0, 1.0),
                        (0.0, 0.0, 1.0),
                        (0.0, 0.0, 1.0),
                    ],
                    uvs=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)],
                    triangles=[(0, 1, 2), (0, 2, 3)],
                    tex_ids=[TexID(id=0, count=2)],
                    radius=1.414,
                    min=(-1.0, -1.0, 0.0),
                    max=(1.0, 1.0, 0.0),
                ),
            ],
            tex_names=["quad_tex"],
            obj_names=["GEO_quad"],
        )

        with tempfile.NamedTemporaryFile(suffix='.geo', delete=False) as f:
            tmp_path = f.name

        try:
            write_geo(tmp_path, geo)
            reloaded = read_geo(tmp_path)

            model = reloaded.models[0]
            assert model.vert_count == 4
            assert model.tri_count == 2
            assert len(model.triangles) == 2
        finally:
            os.unlink(tmp_path)


class TestSplitVertices:
    """Test GEO files with split vertices (different normals per face-corner)."""

    def test_split_normals_round_trip(self):
        """Vertices sharing a position but with different normals should
        survive a write → read round-trip as separate GEO vertices."""
        # Two triangles sharing an edge (verts 1,2) but with different normals
        # — simulates a hard edge / UV seam where vertices are split
        geo = GeoFile(
            version=8,
            headers=[GeoHeader(name="split.wrl", model_count=1)],
            models=[
                GeoModel(
                    name="GEO_split",
                    vert_count=6,
                    tri_count=2,
                    vertices=[
                        # Triangle 1: face pointing +Z
                        (0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0),
                        (0.0, 1.0, 0.0),
                        # Triangle 2: shares edge but different normals (split verts)
                        (1.0, 0.0, 0.0),   # same position as vert 1
                        (0.0, 1.0, 0.0),   # same position as vert 2
                        (1.0, 1.0, 0.0),
                    ],
                    normals=[
                        # Face 1 normals point +Z
                        (0.0, 0.0, 1.0),
                        (0.0, 0.0, 1.0),
                        (0.0, 0.0, 1.0),
                        # Face 2 normals point +Y (different — this is the split)
                        (0.0, 1.0, 0.0),
                        (0.0, 1.0, 0.0),
                        (0.0, 1.0, 0.0),
                    ],
                    uvs=[
                        (0.0, 0.0), (1.0, 0.0), (0.0, 1.0),
                        (0.0, 0.0), (1.0, 0.0), (1.0, 1.0),
                    ],
                    triangles=[(0, 1, 2), (3, 4, 5)],
                    tex_ids=[TexID(id=0, count=2)],
                    radius=1.414,
                    min=(0.0, 0.0, 0.0),
                    max=(1.0, 1.0, 0.0),
                ),
            ],
            tex_names=["split_tex"],
            obj_names=["GEO_split"],
        )

        with tempfile.NamedTemporaryFile(suffix='.geo', delete=False) as f:
            tmp_path = f.name

        try:
            write_geo(tmp_path, geo)
            reloaded = read_geo(tmp_path)

            model = reloaded.models[0]
            assert model.vert_count == 6, "Split vertices must be preserved"
            assert model.tri_count == 2
            assert len(model.normals) == 6

            # Verify the two sets of normals are distinct
            # Verts 0-2 should have normals near (0,0,1)
            for n in model.normals[:3]:
                assert abs(n[2]) > 0.9, f"Expected +Z normal, got {n}"

            # Verts 3-5 should have normals near (0,1,0)
            for n in model.normals[3:]:
                assert abs(n[1]) > 0.9, f"Expected +Y normal, got {n}"
        finally:
            os.unlink(tmp_path)

    def test_split_uvs_round_trip(self):
        """Vertices at a UV seam should be separate GEO vertices."""
        # Same positions, same normals, but different UVs (UV seam)
        geo = GeoFile(
            version=8,
            headers=[GeoHeader(name="uvsplit.wrl", model_count=1)],
            models=[
                GeoModel(
                    name="GEO_uvsplit",
                    vert_count=6,
                    tri_count=2,
                    vertices=[
                        (0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0),
                        (0.0, 1.0, 0.0),
                        (1.0, 0.0, 0.0),   # same pos as vert 1
                        (0.0, 1.0, 0.0),   # same pos as vert 2
                        (1.0, 1.0, 0.0),
                    ],
                    normals=[(0.0, 0.0, 1.0)] * 6,
                    uvs=[
                        # UV island 1
                        (0.0, 0.0), (0.5, 0.0), (0.0, 0.5),
                        # UV island 2 (different UVs at shared positions)
                        (0.5, 0.5), (1.0, 0.5), (1.0, 1.0),
                    ],
                    triangles=[(0, 1, 2), (3, 4, 5)],
                    tex_ids=[TexID(id=0, count=2)],
                    radius=1.414,
                    min=(0.0, 0.0, 0.0),
                    max=(1.0, 1.0, 0.0),
                ),
            ],
            tex_names=["uvsplit_tex"],
            obj_names=["GEO_uvsplit"],
        )

        with tempfile.NamedTemporaryFile(suffix='.geo', delete=False) as f:
            tmp_path = f.name

        try:
            write_geo(tmp_path, geo)
            reloaded = read_geo(tmp_path)

            model = reloaded.models[0]
            assert model.vert_count == 6, "UV-split vertices must be preserved"
            assert len(model.uvs) == 6

            # UVs for vert 1 and vert 3 (same position) should differ
            uv1 = model.uvs[1]
            uv3 = model.uvs[3]
            assert abs(uv1[0] - uv3[0]) > 0.01 or abs(uv1[1] - uv3[1]) > 0.01, \
                f"UV seam verts should have different UVs: {uv1} vs {uv3}"
        finally:
            os.unlink(tmp_path)


@skip_no_geo
class TestRoundTrip:
    """Test read → write → read round-trips with real files."""

    def test_round_trip_capsule(self):
        """Round-trip the capsule GEO file."""
        original = read_geo(GEO_CAPSULE)

        with tempfile.NamedTemporaryFile(suffix='.geo', delete=False) as f:
            tmp_path = f.name

        try:
            write_geo(tmp_path, original)
            reloaded = read_geo(tmp_path)

            assert len(reloaded.models) == len(original.models)
            for orig_m, new_m in zip(original.models, reloaded.models):
                assert orig_m.vert_count == new_m.vert_count
                assert orig_m.tri_count == new_m.tri_count
        finally:
            os.unlink(tmp_path)
