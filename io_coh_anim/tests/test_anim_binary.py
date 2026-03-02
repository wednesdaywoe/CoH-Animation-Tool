"""Tests for binary .anim file reading and writing."""

import os
import sys
import tempfile
import struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from io_coh_anim.formats.anim_binary import read_anim, write_anim, AnimData, BoneTrackData
from io_coh_anim.tests.conftest import (
    PARKOUR_RUN, BLASTER_BARRAGE, EMOTE_DRINK, SKEL_READY,
    skip_no_samples, MALE_DIR, SAMPLE_DIR,
)


@skip_no_samples
class TestReadAnim:
    """Test reading real .anim files."""

    def test_read_parkour_run(self):
        anim = read_anim(PARKOUR_RUN)
        assert anim.name == "male/parkour_run"
        assert anim.base_anim_name == "male/skel_ready2"
        assert anim.length > 0
        assert len(anim.bone_tracks) > 0
        # Verified from hex dump: 33 bone tracks
        assert len(anim.bone_tracks) == 33

    def test_read_parkour_run_bones(self):
        anim = read_anim(PARKOUR_RUN)
        bone_names = [bt.bone_name for bt in anim.bone_tracks]
        # Should contain standard humanoid bones
        assert "HIPS" in bone_names
        assert "CHEST" in bone_names
        assert "HEAD" in bone_names

    def test_read_parkour_run_rotations(self):
        anim = read_anim(PARKOUR_RUN)
        hips = next(bt for bt in anim.bone_tracks if bt.bone_name == "HIPS")
        assert len(hips.rotations) > 0
        # Each rotation is a quaternion (w, x, y, z)
        for q in hips.rotations:
            assert len(q) == 4
            # Should be roughly unit length
            length_sq = sum(c * c for c in q)
            assert 0.9 < length_sq < 1.1, f"Non-unit quaternion: {q} (len²={length_sq})"

    def test_read_parkour_run_positions(self):
        anim = read_anim(PARKOUR_RUN)
        hips = next(bt for bt in anim.bone_tracks if bt.bone_name == "HIPS")
        assert len(hips.positions) > 0
        for pos in hips.positions:
            assert len(pos) == 3

    def test_read_skel_file(self):
        anim = read_anim(SKEL_READY)
        assert "skel_ready" in anim.name
        assert anim.hierarchy is not None
        assert anim.hierarchy.root >= 0

    def test_read_blaster_barrage(self):
        anim = read_anim(BLASTER_BARRAGE)
        assert anim.name == "male/blaster_barrage"
        assert len(anim.bone_tracks) > 0

    def test_read_emote_drink(self):
        anim = read_anim(EMOTE_DRINK)
        assert "emote_drink_mug" in anim.name
        assert len(anim.bone_tracks) > 0

    def test_read_all_male_anims(self):
        """Read all male animations without errors."""
        if not os.path.exists(MALE_DIR):
            pytest.skip("Male anim directory not found")
        for fname in os.listdir(MALE_DIR):
            if fname.endswith(".anim"):
                filepath = os.path.join(MALE_DIR, fname)
                anim = read_anim(filepath)
                assert anim.name, f"Empty name in {fname}"
                assert len(anim.bone_tracks) > 0, f"No bone tracks in {fname}"


@skip_no_samples
class TestWriteAnim:
    """Test writing and round-tripping .anim files."""

    def test_round_trip_parkour(self):
        """Read → write → read should produce equivalent data."""
        original = read_anim(PARKOUR_RUN)

        with tempfile.NamedTemporaryFile(suffix='.anim', delete=False) as f:
            tmp_path = f.name

        try:
            write_anim(tmp_path, original)
            reloaded = read_anim(tmp_path)

            assert reloaded.name == original.name
            assert reloaded.base_anim_name == original.base_anim_name
            assert len(reloaded.bone_tracks) == len(original.bone_tracks)

            for orig_bt, new_bt in zip(original.bone_tracks, reloaded.bone_tracks):
                assert orig_bt.bone_name == new_bt.bone_name
                assert len(orig_bt.rotations) == len(new_bt.rotations)
                assert len(orig_bt.positions) == len(new_bt.positions)
        finally:
            os.unlink(tmp_path)

    def test_write_minimal(self):
        """Write a minimal animation."""
        anim = AnimData(
            name="test/minimal",
            base_anim_name="test/skel_test",
            length=2.0,
            bone_tracks=[
                BoneTrackData(
                    bone_id=0,
                    bone_name="HIPS",
                    rotations=[(1, 0, 0, 0), (0.707, 0.707, 0, 0)],
                    positions=[(0, 0, 0), (0, 0.5, 0)],
                ),
            ],
        )

        with tempfile.NamedTemporaryFile(suffix='.anim', delete=False) as f:
            tmp_path = f.name

        try:
            write_anim(tmp_path, anim)

            # Verify header
            with open(tmp_path, 'rb') as f:
                header_size = struct.unpack('<i', f.read(4))[0]
                assert header_size > 0
                name_bytes = f.read(256)
                name = name_bytes.split(b'\x00')[0].decode('ascii')
                assert name == "test/minimal"

            # Read back
            reloaded = read_anim(tmp_path)
            assert reloaded.name == "test/minimal"
            assert len(reloaded.bone_tracks) == 1
            assert reloaded.bone_tracks[0].bone_name == "HIPS"
        finally:
            os.unlink(tmp_path)


class TestWriteAnimNoSamples:
    """Tests that don't require sample files."""

    def test_write_empty(self):
        """Write an animation with no bones."""
        anim = AnimData(name="test/empty", length=0.0)

        with tempfile.NamedTemporaryFile(suffix='.anim', delete=False) as f:
            tmp_path = f.name

        try:
            write_anim(tmp_path, anim)
            reloaded = read_anim(tmp_path)
            assert reloaded.name == "test/empty"
            assert len(reloaded.bone_tracks) == 0
        finally:
            os.unlink(tmp_path)
