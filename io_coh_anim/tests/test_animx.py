"""Tests for ANIMX text format reading and writing."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from io_coh_anim.formats.animx import (
    read_animx, write_animx,
    AnimXData, AnimXBone, AnimXTransform,
)


class TestAnimXParse:
    """Test ANIMX text parsing."""

    SAMPLE_ANIMX = """\
# NCsoft CoH Animation Export
# Generated from 3D Studio Max using:
#\t\tPlugin: 'coh_anim_exp', Version 2, Revision 0
#\t\tSource File: test.max

Version 200
SourceName test.max
TotalFrames 3
FirstFrame 0

Bone "HIPS"
{
\t# frames: 3

\tTransform
\t{
\t\tAxis 0 0 1
\t\tAngle 0
\t\tTranslation 0 0 42.5
\t\tScale 1 1 1
\t}

\tTransform
\t{
\t\tAxis 0.1 0.2 0.97
\t\tAngle 0.05
\t\tTranslation 0.1 0.3 42.8
\t\tScale 1 1 1
\t}

\tTransform
\t{
\t\tAxis 0 0 1
\t\tAngle 0
\t\tTranslation 0 0 42.5
\t\tScale 1 1 1
\t}

}

Bone "WAIST"
{
\t# frames: 2

\tTransform
\t{
\t\tAxis 0 0 1
\t\tAngle 0
\t\tTranslation 0 0 5.2
\t\tScale 1 1 1
\t}

\tTransform
\t{
\t\tAxis 0 0 1
\t\tAngle 0.01
\t\tTranslation 0 0 5.3
\t\tScale 1 1 1
\t}

}

"""

    def test_parse_header(self):
        from io_coh_anim.formats.animx import _parse_animx
        data = _parse_animx(self.SAMPLE_ANIMX)
        assert data.version == 200
        assert data.source_name == "test.max"
        assert data.total_frames == 3
        assert data.first_frame == 0

    def test_parse_bones(self):
        from io_coh_anim.formats.animx import _parse_animx
        data = _parse_animx(self.SAMPLE_ANIMX)
        assert len(data.bones) == 2
        assert data.bones[0].name == "HIPS"
        assert data.bones[1].name == "WAIST"

    def test_parse_transforms(self):
        from io_coh_anim.formats.animx import _parse_animx
        data = _parse_animx(self.SAMPLE_ANIMX)

        hips = data.bones[0]
        assert len(hips.transforms) == 3

        t0 = hips.transforms[0]
        assert t0.axis == (0.0, 0.0, 1.0)
        assert t0.angle == 0.0
        assert t0.translation == (0.0, 0.0, 42.5)
        assert t0.scale == (1.0, 1.0, 1.0)

        t1 = hips.transforms[1]
        assert abs(t1.axis[0] - 0.1) < 1e-6
        assert abs(t1.angle - 0.05) < 1e-6

    def test_parse_waist(self):
        from io_coh_anim.formats.animx import _parse_animx
        data = _parse_animx(self.SAMPLE_ANIMX)

        waist = data.bones[1]
        assert len(waist.transforms) == 2


class TestAnimXRoundTrip:
    """Test ANIMX write → read round-trip."""

    def test_round_trip(self):
        data = AnimXData(
            version=200,
            source_name="roundtrip.blend",
            total_frames=2,
            first_frame=0,
            bones=[
                AnimXBone(
                    name="HIPS",
                    transforms=[
                        AnimXTransform(
                            axis=(0, 0, 1),
                            angle=0,
                            translation=(0, 0, 42.5),
                            scale=(1, 1, 1),
                        ),
                        AnimXTransform(
                            axis=(0.1, 0.2, 0.97),
                            angle=0.05,
                            translation=(0.1, 0.3, 42.8),
                            scale=(1, 1, 1),
                        ),
                    ]
                ),
            ]
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.animx', delete=False) as f:
            tmp_path = f.name

        try:
            write_animx(tmp_path, data)
            reloaded = read_animx(tmp_path)

            assert reloaded.version == 200
            assert reloaded.source_name == "roundtrip.blend"
            assert reloaded.total_frames == 2
            assert len(reloaded.bones) == 1
            assert reloaded.bones[0].name == "HIPS"
            assert len(reloaded.bones[0].transforms) == 2

            t1 = reloaded.bones[0].transforms[1]
            assert abs(t1.angle - 0.05) < 1e-4
        finally:
            os.unlink(tmp_path)
