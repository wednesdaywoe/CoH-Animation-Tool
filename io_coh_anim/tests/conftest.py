"""Shared test fixtures and paths."""

import os
import pytest

# Sample data directory
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "Anim", "player_library", "animations")

MALE_DIR = os.path.join(SAMPLE_DIR, "male")
FEM_DIR = os.path.join(SAMPLE_DIR, "fem")
HUGE_DIR = os.path.join(SAMPLE_DIR, "huge")

# Specific test files
PARKOUR_RUN = os.path.join(MALE_DIR, "parkour_run.anim")
BLASTER_BARRAGE = os.path.join(MALE_DIR, "blaster_barrage.anim")
EMOTE_DRINK = os.path.join(MALE_DIR, "emote_drink_mug.anim")
SKEL_READY = os.path.join(SAMPLE_DIR, "n_backpack_wickerbasketa", "skel_ready.anim")


def has_sample_files():
    """Check if sample .anim files are available."""
    return os.path.exists(PARKOUR_RUN)


skip_no_samples = pytest.mark.skipif(
    not has_sample_files(),
    reason="Sample .anim files not found"
)

# GEO sample data
GEO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "Geo")
GEO_OBJECT_DIR = os.path.join(GEO_DIR, "object_library")
GEO_PLAYER_DIR = os.path.join(GEO_DIR, "player_library")

# Specific GEO test files
GEO_CAPSULE = os.path.join(GEO_OBJECT_DIR, "anniversary", "anniversary_capsule_hero.geo")
GEO_FEM_BOOT = os.path.join(GEO_PLAYER_DIR, "fem_boot.geo")
GEO_STATUE = os.path.join(GEO_OBJECT_DIR, "city_zones", "elements", "hero_statues",
                           "male_statue_atlas", "male_statue_atlus.geo")


def has_geo_files():
    """Check if sample .geo files are available."""
    return os.path.exists(GEO_CAPSULE)


skip_no_geo = pytest.mark.skipif(
    not has_geo_files(),
    reason="Sample .geo files not found"
)
