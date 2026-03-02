"""Tests for DDS and .texture format handling."""

import os
import sys
import struct
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from io_coh_anim.formats.dds import (
    read_dds, write_dds, dds_mip_size,
    compress_image, decompress_image,
    _compress_dxt1_block, _decompress_dxt1_block,
    _compress_dxt5_block, _decompress_dxt5_block,
    generate_mipmaps,
    DDS_MAGIC, FOURCC_DXT1, FOURCC_DXT5,
)
from io_coh_anim.formats.texture import (
    read_texture, write_texture, TextureData,
)


class TestDXT1Block:
    """Test DXT1 block compression/decompression."""

    def test_solid_red(self):
        """Solid red block should round-trip."""
        pixels = [(255, 0, 0, 255)] * 16
        compressed = _compress_dxt1_block(pixels)
        assert len(compressed) == 8
        decompressed = _decompress_dxt1_block(compressed)
        for r, g, b, a in decompressed:
            assert r > 200, f"Red too low: {r}"
            assert g < 30, f"Green too high: {g}"
            assert b < 30, f"Blue too high: {b}"

    def test_solid_black(self):
        """Solid black block."""
        pixels = [(0, 0, 0, 255)] * 16
        compressed = _compress_dxt1_block(pixels)
        decompressed = _decompress_dxt1_block(compressed)
        for r, g, b, a in decompressed:
            assert r < 10 and g < 10 and b < 10

    def test_solid_white(self):
        """Solid white block."""
        pixels = [(255, 255, 255, 255)] * 16
        compressed = _compress_dxt1_block(pixels)
        decompressed = _decompress_dxt1_block(compressed)
        for r, g, b, a in decompressed:
            assert r > 240 and g > 240 and b > 240

    def test_gradient(self):
        """Gradient block — values should be in the right range."""
        pixels = [(i * 16, i * 16, i * 16, 255) for i in range(16)]
        compressed = _compress_dxt1_block(pixels)
        assert len(compressed) == 8
        decompressed = _decompress_dxt1_block(compressed)
        # DXT1 only has 4 colors, so precision is limited
        assert len(decompressed) == 16


class TestDXT5Block:
    """Test DXT5 block compression/decompression."""

    def test_solid_with_alpha(self):
        """Solid color with semi-transparent alpha."""
        pixels = [(128, 64, 200, 128)] * 16
        compressed = _compress_dxt5_block(pixels)
        assert len(compressed) == 16
        decompressed = _decompress_dxt5_block(compressed)
        for r, g, b, a in decompressed:
            assert abs(a - 128) < 10, f"Alpha mismatch: {a}"

    def test_varying_alpha(self):
        """Block with varying alpha values."""
        pixels = [(128, 128, 128, i * 16) for i in range(16)]
        compressed = _compress_dxt5_block(pixels)
        assert len(compressed) == 16
        decompressed = _decompress_dxt5_block(compressed)
        assert len(decompressed) == 16

    def test_fully_transparent(self):
        """Fully transparent block."""
        pixels = [(0, 0, 0, 0)] * 16
        compressed = _compress_dxt5_block(pixels)
        decompressed = _decompress_dxt5_block(compressed)
        for _, _, _, a in decompressed:
            assert a < 5, f"Alpha should be ~0: {a}"

    def test_fully_opaque(self):
        """Fully opaque block."""
        pixels = [(200, 100, 50, 255)] * 16
        compressed = _compress_dxt5_block(pixels)
        decompressed = _decompress_dxt5_block(compressed)
        for _, _, _, a in decompressed:
            assert a > 250, f"Alpha should be ~255: {a}"


class TestDDSImage:
    """Test full DDS image compression/decompression."""

    def test_4x4_dxt1(self):
        """Compress and decompress a single 4x4 block as DXT1."""
        pixels = [(255, 0, 0, 255)] * 16
        compressed = compress_image(pixels, 4, 4, 'DXT1')
        assert len(compressed) == 8
        decompressed = decompress_image(compressed, 4, 4, 'DXT1')
        assert len(decompressed) == 16

    def test_4x4_dxt5(self):
        """Compress and decompress a single 4x4 block as DXT5."""
        pixels = [(0, 255, 0, 128)] * 16
        compressed = compress_image(pixels, 4, 4, 'DXT5')
        assert len(compressed) == 16
        decompressed = decompress_image(compressed, 4, 4, 'DXT5')
        assert len(decompressed) == 16

    def test_8x8_image(self):
        """8x8 image = 4 blocks."""
        pixels = [(i % 256, (i * 3) % 256, (i * 7) % 256, 255) for i in range(64)]
        compressed = compress_image(pixels, 8, 8, 'DXT5')
        expected_size = dds_mip_size(8, 8, 'DXT5')
        assert len(compressed) == expected_size
        decompressed = decompress_image(compressed, 8, 8, 'DXT5')
        assert len(decompressed) == 64

    def test_non_power_of_two(self):
        """Non-power-of-2 dimensions should still work."""
        pixels = [(128, 128, 128, 255)] * (5 * 7)
        compressed = compress_image(pixels, 5, 7, 'DXT5')
        decompressed = decompress_image(compressed, 5, 7, 'DXT5')
        assert len(decompressed) == 35


class TestDDSFile:
    """Test DDS file read/write."""

    def test_write_read_dxt1(self):
        """Write and read back a DXT1 DDS file."""
        pixels = [(200, 100, 50, 255)] * (8 * 8)
        dds_data = write_dds(pixels, 8, 8, fmt='DXT1', mipmaps=False)

        assert dds_data[:4] == DDS_MAGIC
        info = read_dds(dds_data)
        assert info['width'] == 8
        assert info['height'] == 8
        assert info['format'] == 'DXT1'

    def test_write_read_dxt5(self):
        """Write and read back a DXT5 DDS file."""
        pixels = [(200, 100, 50, 128)] * (16 * 16)
        dds_data = write_dds(pixels, 16, 16, fmt='DXT5', mipmaps=True)

        info = read_dds(dds_data)
        assert info['width'] == 16
        assert info['height'] == 16
        assert info['format'] == 'DXT5'
        assert info['mipmap_count'] > 1

    def test_dds_from_bytes(self):
        """Write DDS from flat RGBA bytes."""
        flat_bytes = bytes([128, 64, 32, 255] * 16)
        dds_data = write_dds(flat_bytes, 4, 4, fmt='DXT5', mipmaps=False)
        info = read_dds(dds_data)
        assert info['width'] == 4
        assert info['height'] == 4


class TestMipmaps:
    """Test mipmap generation."""

    def test_power_of_two(self):
        """16x16 should generate 5 levels: 16, 8, 4, 2, 1."""
        pixels = [(128, 128, 128, 255)] * (16 * 16)
        mips = list(generate_mipmaps(pixels, 16, 16))
        assert len(mips) == 5
        assert mips[0][:2] == (16, 16)
        assert mips[1][:2] == (8, 8)
        assert mips[2][:2] == (4, 4)
        assert mips[3][:2] == (2, 2)
        assert mips[4][:2] == (1, 1)

    def test_single_pixel(self):
        """1x1 image should have 1 mip level."""
        pixels = [(255, 0, 0, 255)]
        mips = list(generate_mipmaps(pixels, 1, 1))
        assert len(mips) == 1

    def test_averaging(self):
        """Mipmaps should average pixel values."""
        pixels = [
            (0, 0, 0, 255), (200, 0, 0, 255),
            (0, 200, 0, 255), (0, 0, 200, 255),
        ]
        mips = list(generate_mipmaps(pixels, 2, 2))
        assert len(mips) == 2
        # 1x1 level should be average of all 4
        avg = mips[1][2][0]
        assert avg[0] == 50  # (0+200+0+0)/4
        assert avg[1] == 50  # (0+0+200+0)/4
        assert avg[2] == 50  # (0+0+0+200)/4


class TestMipSize:
    """Test mip size calculations."""

    def test_dxt1_sizes(self):
        assert dds_mip_size(4, 4, 'DXT1') == 8
        assert dds_mip_size(8, 8, 'DXT1') == 32
        assert dds_mip_size(16, 16, 'DXT1') == 128
        assert dds_mip_size(256, 256, 'DXT1') == 32768

    def test_dxt5_sizes(self):
        assert dds_mip_size(4, 4, 'DXT5') == 16
        assert dds_mip_size(8, 8, 'DXT5') == 64
        assert dds_mip_size(16, 16, 'DXT5') == 256
        assert dds_mip_size(256, 256, 'DXT5') == 65536

    def test_minimum_block(self):
        """1x1 and 2x2 should still use at least 1 block."""
        assert dds_mip_size(1, 1, 'DXT1') == 8
        assert dds_mip_size(1, 1, 'DXT5') == 16
        assert dds_mip_size(2, 2, 'DXT1') == 8


class TestTextureFormat:
    """Test .texture file read/write."""

    def test_write_read_texture(self):
        """Write and read back a .texture file."""
        pixels = [(200, 100, 50, 255)] * (8 * 8)
        dds_data = write_dds(pixels, 8, 8, fmt='DXT5', mipmaps=True)

        with tempfile.NamedTemporaryFile(suffix='.texture', delete=False) as f:
            tmp_path = f.name

        try:
            write_texture(tmp_path, dds_data, name="test_texture",
                          width=8, height=8, alpha=False)
            tex = read_texture(tmp_path)

            assert tex.name == "test_texture"
            assert tex.width == 8
            assert tex.height == 8
            assert tex.dds_data[:4] == DDS_MAGIC
        finally:
            os.unlink(tmp_path)

    def test_texture_with_alpha(self):
        """Texture with alpha flag set."""
        pixels = [(200, 100, 50, 128)] * (4 * 4)
        dds_data = write_dds(pixels, 4, 4, fmt='DXT5', mipmaps=False)

        with tempfile.NamedTemporaryFile(suffix='.texture', delete=False) as f:
            tmp_path = f.name

        try:
            write_texture(tmp_path, dds_data, name="alpha_tex",
                          width=4, height=4, alpha=True)
            tex = read_texture(tmp_path)

            assert tex.name == "alpha_tex"
            assert tex.alpha is True
        finally:
            os.unlink(tmp_path)

    def test_texture_dds_content(self):
        """Verify DDS data survives the .texture wrapper."""
        pixels = [(i * 4, i * 2, i, 255) for i in range(64)]
        dds_data = write_dds(pixels, 8, 8, fmt='DXT1', mipmaps=False)

        with tempfile.NamedTemporaryFile(suffix='.texture', delete=False) as f:
            tmp_path = f.name

        try:
            write_texture(tmp_path, dds_data, name="content_test",
                          width=8, height=8)
            tex = read_texture(tmp_path)

            # DDS data should be identical
            assert tex.dds_data == dds_data
        finally:
            os.unlink(tmp_path)

    def test_long_name(self):
        """Texture with a long name path."""
        name = "textures/environment/city/building_wall_brick_01"
        pixels = [(128, 128, 128, 255)] * 16
        dds_data = write_dds(pixels, 4, 4, fmt='DXT1', mipmaps=False)

        with tempfile.NamedTemporaryFile(suffix='.texture', delete=False) as f:
            tmp_path = f.name

        try:
            write_texture(tmp_path, dds_data, name=name,
                          width=4, height=4)
            tex = read_texture(tmp_path)
            assert tex.name == name
        finally:
            os.unlink(tmp_path)
