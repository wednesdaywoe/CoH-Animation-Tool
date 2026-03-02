# City of Heroes Animation Tools for Blender

A Blender 4.x addon for importing and exporting City of Heroes animations, replacing the legacy 3DS Max 2011 + GetAnimation2 workflow with a free, modern pipeline.

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Binary Animation | `.anim` | Direct game format — read and write the same files CoH loads |
| Text Animation | `.animx` | 3DS Max animation exchange format (used by GetAnimation2) |
| Text Skeleton | `.skelx` | 3DS Max skeleton export format with bind pose hierarchy |

## Installation

1. Download or clone this repository
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **Install...** and select the `io_coh_anim` folder (or a zip of it)
4. Enable **"City of Heroes Animation Tools"** in the addon list

Alternatively, copy the `io_coh_anim` folder into your Blender addons directory:
- Windows: `%APPDATA%\Blender Foundation\Blender\4.x\scripts\addons\`
- Linux: `~/.config/blender/4.x/scripts/addons/`
- macOS: `~/Library/Application Support/Blender/4.x/scripts/addons/`

## Usage

### Sidebar Panel

A **CoH** tab appears in the 3D View sidebar (press `N` to toggle). It provides quick access to all operations and shows info about the active armature (bone count, current action).

### Creating a CoH Armature

**Sidebar > CoH > Create CoH Armature**

Creates a standard CoH humanoid skeleton with all 99 bones in the correct hierarchy. This is useful as a starting point for creating new animations from scratch.

### Importing Animations

#### Binary .anim (game files)

**File > Import > CoH Animation (.anim)** or **Sidebar > Import > Import .anim**

Imports a binary `.anim` file directly from the game data. If the file contains skeleton hierarchy data (e.g. `skel_ready.anim`), a new armature is created automatically. Otherwise, the animation is applied as keyframes to the active armature.

#### Text .animx

**File > Import > CoH Animation Text (.animx)** or **Sidebar > Import > Import .animx**

Imports an ANIMX text file and applies transforms as keyframes to the active CoH armature. Requires an existing armature — create one first or import a skeleton.

#### Skeleton .skelx

**File > Import > CoH Skeleton (.skelx)** or **Sidebar > Import > Import .skelx**

Creates a new armature from a SKELX skeleton file, using the bind pose positions and bone hierarchy defined in the file.

### Exporting Animations

All export operations require an active armature with an animation action.

#### Binary .anim

**File > Export > CoH Animation (.anim)** or **Sidebar > Export > Export .anim**

Exports the current animation as a binary `.anim` file that can be loaded directly by the game. Options:

- **Animation Name** — internal path, e.g. `male/my_custom_anim`
- **Base Animation** — reference skeleton, typically `male/skel_ready2`
- **Body Type** — Male, Female, or Huge

#### Text .animx

**File > Export > CoH Animation Text (.animx)** or **Sidebar > Export > Export .animx**

Exports the animation as an ANIMX text file compatible with GetAnimation2.

#### Skeleton .skelx

**File > Export > CoH Skeleton (.skelx)** or **Sidebar > Export > Export .skelx**

Exports the armature's bind pose and hierarchy as a SKELX text file.

## Typical Workflows

### Viewing a game animation

1. Import a skeleton file: **Import > CoH Animation (.anim)** → select a `skel_ready.anim`
2. With the armature selected, import an animation: **Import > CoH Animation (.anim)** → select e.g. `parkour_run.anim`
3. Press Space to play the animation in the viewport

### Creating a new animation for the game

1. **Create CoH Armature** from the sidebar
2. Pose and keyframe the bones in Blender as usual
3. **Export > CoH Animation (.anim)** to produce a game-ready file

### Converting between formats

- Import `.animx` → Export `.anim` (replaces the GetAnimation2 pipeline)
- Import `.anim` → Export `.animx` (extract game animations to editable text)

## Running Tests

The format parsers and core math can be tested outside of Blender:

```bash
pip install pytest
pytest io_coh_anim/tests/
```

Tests that require sample `.anim` files (placed in `Anim/player_library/animations/`) are skipped automatically if the files aren't present.

## Project Structure

```
io_coh_anim/
├── __init__.py           # Addon registration, menus, sidebar panel
├── operators.py          # Blender import/export operators
├── armature.py           # Armature creation and animation application
├── core/
│   ├── bones.py          # Bone IDs, names, and hierarchy definitions
│   ├── coords.py         # Blender ↔ game coordinate conversions
│   └── transforms.py     # Quaternion math, world/local transforms
├── formats/
│   ├── anim_binary.py    # Binary .anim reader/writer
│   ├── animx.py          # ANIMX text format reader/writer
│   ├── skelx.py          # SKELX text format reader/writer
│   └── compression.py    # 5-byte quaternion & 6-byte position compression
└── tests/
    ├── conftest.py       # Test fixtures and sample file paths
    ├── test_anim_binary.py
    ├── test_animx.py
    ├── test_compression.py
    └── test_coords.py
```

## Requirements

- Blender 4.0 or newer
- Python 3.10+ (bundled with Blender)

## License

Community project for City of Heroes modding.
