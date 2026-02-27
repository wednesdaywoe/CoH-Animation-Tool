# City of Heroes Animation Tool - Research & Planning

## Project Goal

Build a Blender plugin to import/export City of Heroes .ANIM animation files, replacing the legacy 3DS Max 2011 + GetAnimation2 workflow entirely.

## Current Workflow (The goal is to replace this with an easier, modern solution)

```
3DS Max 2011 + Master Rig → Export ANIMX → Edit ANIMX → GetAnimation2 → .ANIM → PIGG → Game
```

### Detailed Steps
1. Open 3DS Max 2011 with master rig file (e.g., SM_Master.max)
2. Create animation using the rig
3. Load ANIMX export plugin (Customize > Manage Plugins)
4. Export to ANIMX format (File > Export)
5. Edit ANIMX in text editor:
   - Fix `TotalFrames` to match intended frame count
   - Find bone `GEO_gun`, delete it and everything below it (prevents GA2 crash)
6. Generate SKELX from existing ANIM: `GetAnimation2 -s <existing.anim>`
7. Set up folder structure: `{bodytype}/models/{SKELX + ANIMX}`
8. Run `GetAnimation2.exe -noperforce` from the body type folder
9. Pack resulting .ANIM into PIGG or use file override for testing

### Target Workflow
```
Blender + CoH Rig → Export .ANIM directly → PIGG → Game
         OR
Blender + CoH Rig → Export ANIMX/SKELX → GetAnimation2 → .ANIM → PIGG → Game
```

## File Formats

### ANIMX (Text-Based Intermediate)
- Custom text format exported from 3DS Max
- Contains: frame count, bone names, keyframe data per bone
- May include geometry bones (GEO_*) that must be stripped
- Editable in any text editor
- **Need sample files to reverse-engineer exact syntax**

### SKELX (Text-Based Skeleton)
- Bone hierarchy definition
- Generated from .ANIM files via `GetAnimation2 -s`
- Required alongside ANIMX when building .ANIM files
- **Need sample files to reverse-engineer exact syntax**

### ANIM (Binary Runtime)
- Binary animation format used by the game engine
- Contains embedded reference to its SKEL file path
- Associated with body types: `male`, `fem`, `huge`
- Stored in PIGG archives
- Can be inspected via `GetAnimation2 -e <file.anim>` (converts to human-readable text)
- Can be reversed via `GetAnimation2 -s <file.anim>` (outputs SKELX + ANIMX)

### SKEL (Binary Runtime Skeleton)
- Binary skeleton used at runtime
- Referenced by ANIM files internally

### PIGG (Game Archive)
- Archive format for game assets
- Tools exist: Piglet, pigg tool from source, cohtools (Python)

## GetAnimation2 (GA2) Reference

```
GetAnimation2.exe [flags]

Flags:
  -monitor           Watch folder for animation changes
  -prescan           Scan hierarchy on monitor start
  -f                 Force reprocess all animations
  -noperforce        Work offline (no Perforce VCS). Required for custom animations.
  -e <.anim>         Convert .anim to human-readable text (debug/inspection)
  -s <.anim> <dest>  Convert .anim to .SKELX and .ANIMX source files
  -batch_src         Batch convert old .WRL-associated .anim files (dangerous)
  -?                 Help
```

### GA2 Folder Structure Requirement
```
male/               (or fem/ or huge/)
  models/
    skeleton.skelx
    animation1.animx
    animation2.animx
```
Run GA2 from the body type folder level.

## Implementation Strategy

### Phase 1: ANIMX/SKELX Support (Replaces 3DS Max)
- Blender addon that imports/exports ANIMX and SKELX text formats
- Includes master rig setup in Blender matching CoH bone hierarchy
- Users still need GA2 for final ANIMX → ANIM conversion
- Fastest path to a working tool

### Phase 2: Direct ANIM Binary Support (Replaces GA2)
- Add binary ANIM read/write to the Blender addon
- Requires understanding the binary format (from OuroDev source)
- Eliminates need for GA2 entirely
- Complete standalone workflow

## Reference Blender Plugins (Architecture Examples)
- [io_anim_seanim](https://github.com/SE2Dev/io_anim_seanim) - SEAnim import/export
- [Blender_io-scene-ANIM](https://github.com/PositionWizard/Blender_io-scene-ANIM) - Maya ANIM import/export
- [io_anim_hkx](https://github.com/opparco/io_anim_hkx) - Skyrim HKX animation import/export

## Key Resources
- [OuroDev Wiki - Creating Animations](https://wiki.ourodev.com/Creating_new_Animations_(3DS_MAX))
- [OuroDev GitLab](https://git.ourodev.com) (private, contains GA2 source)
- [SEGS Project](https://github.com/Segs/Segs) (C++ server emulator, may have format info)
- [cohtools](https://github.com/mobbyg/cohtools) (Python PIGG/texture tools)

## Important Technical Notes
- Body types: `male`, `fem`, `huge` — each has its own skeleton
- GEO_* bones in ANIMX must be stripped or GA2 crashes (it looks for geometry files that don't exist)
- ANIM files contain an internal path reference to their SKEL file (e.g., `debug/skel_ready2.anim`)
- The matching SKEL file must be accessible at the referenced path for the game to work
- Master rig files from the "Scrapyarders dump" define the bone hierarchy

## Files Needed to Proceed
1. **Sample ANIMX file** — to reverse-engineer the text format and build the parser
2. **Sample SKELX file** — to understand bone hierarchy format
3. **Sample ANIM file** — for binary format analysis (Phase 2)
4. **GetAnimation2 source code** — from OuroDev source tree (for binary format reference)
5. **ANIMX export plugin source** — from OuroDev source (to understand what 3DS Max exports)
6. **Master rig file info** — bone names, hierarchy, to recreate in Blender
