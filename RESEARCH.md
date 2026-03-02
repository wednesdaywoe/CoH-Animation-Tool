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

---

## File Format Specifications (Reverse-Engineered from Source)

### ANIMX Format (Text-Based Animation Export)

The ANIMX format is a text file exported from 3DS Max by the `coh_anim_exp` plugin. The format is parsed by a struct-based auto-parser in the engine (defined by `import_animx.c`).

**Source:** `utilities/3dsmax/coh_anim_exp/animexp.cpp`
**Parser:** `utilities/3dsmax/coh_anim_imp/import_animx.c`
**Converter:** `utilities/GetAnimation2/src/process_animx.c`

#### Data Structures (from import_animx.c)

```c
typedef struct TAnimX_Transform {
    Vec3 vAxis;         // Rotation axis (3DS Max coordinate frame)
    F32  fAngle;        // Rotation angle (radians from 3DS Max AngAxis)
    Vec3 vTranslation;  // Position (world space in 3DS Max coords)
    Vec3 vScale;        // Scale factors
} TAnimX_Transform;

typedef struct TAnimX_Bone {
    const char*         pcName;       // Bone name (e.g., "HIPS", "CHEST")
    TAnimX_Transform**  eaTransform;  // Array of per-frame transforms
} TAnimX_Bone;

typedef struct TAnimX {
    int          iVersion;       // Format version (currently 200)
    const char*  pcSourceName;   // Source .MAX filename
    int          iTotalFrames;   // Total frame count in animation
    int          iFirstFrame;    // First frame number
    TAnimX_Bone** eaBone;        // Array of bone animation tracks
} TAnimX;
```

#### File Syntax (from animexp.cpp WriteHeader + SampleController + dumpAnimNode)

```
# NCsoft CoH Animation Export
# Generated from 3D Studio Max using:
#		Plugin: 'coh_anim_exp', Version 2, Revision 0
#		Source File: MyAnimation.max

Version 200
SourceName MyAnimation.max
TotalFrames 30
FirstFrame 0

Bone "HIPS"
{
	# frames: 30

	Transform
	{
		Axis 0 0 1
		Angle 0
		Translation 0 0 42.5
		Scale 1 1 1
	}

	Transform
	{
		Axis 0.1 0.2 0.97
		Angle 0.05
		Translation 0.1 0.3 42.8
		Scale 1 1 1
	}

	... (one Transform per frame until the bone stops moving)
}

Bone "WAIST"
{
	# frames: 25

	Transform
	{
		Axis 0 0 1
		Angle 0
		Translation 0 0 5.2
		Scale 1 1 1
	}

	... (more transforms)
}
```

#### Key Details
- **Coordinate space:** 3DS Max right-handed Z-up (X, Y, Z)
- **Rotation format:** Axis-Angle from `AngAxis aax; aax.Set(pmat);`
- **Transform space:** World space relative to parent (CTRL_RELATIVE)
- **Frame truncation:** Bones only export frames until they stop moving (optimization)
- **Minimum 2 frames** required or GA2 rejects the file
- **Bone names** must match the game's bone ID enum names (e.g., "HIPS", "CHEST", "UARMR")
- **GEO_* bones** must be stripped before GA2 processing (causes crash)
- **Whitelist filtering:** Optional `coh_anim_names.txt` file limits which bones are exported

---

### SKELX Format (Text-Based Skeleton Export)

The SKELX format defines the skeleton hierarchy with bind pose transforms. It uses a **nested structure** where child bones are indented within parent bone blocks.

**Source:** `utilities/3dsmax/coh_anim_exp/skelexp.cpp`
**Parser:** `utilities/GetAnimation2/src/process_skelx.c`

#### Data Structures (from process_skelx.c)

```c
typedef struct TSkelX_Bone {
    const char* pcName;      // Bone name
    Vec3 vAxis;              // Rotation axis (bind pose)
    F32  fAngle;             // Rotation angle (bind pose)
    Vec3 vTranslation;       // Position (bind pose)
    Vec3 vScale;             // Scale (bind pose)
    Vec3 vRow0, vRow1, vRow2, vRow3;  // Full 4x3 matrix (validation)
    U32  Children;           // Number of child bones
    TSkelX_Bone** eaBone;    // Array of child bones (recursive)
} TSkelX_Bone;

typedef struct TSkelX {
    int          iVersion;      // Format version (200)
    const char*  pcSourceName;  // Source .MAX filename
    TSkelX_Bone** eaBone;       // Root-level bones
} TSkelX;
```

#### File Syntax (from skelexp.cpp WriteHeader + SampleController + dumpSkelNode)

```
# NCsoft CoH Skeleton Export
# Generated from 3D Studio Max using:
#		Plugin: 'coh_anim_exp', Version 2, Revision 0
#		Source File: SM_Master.max

Version 200
SourceName SM_Master.max

# NODE HIERARCHY
#	|_ Scene Root
#	  |_ HIPS
#	  | |_ WAIST
#	  | | |_ CHEST
#	  | | | |_ NECK
#	  | | | | |_ HEAD
#	  ... (visual hierarchy tree)

Bone "HIPS"
{
    Axis 0 0 1
    Angle 0
    Translation 0 0 42.5
    Scale 1 1 1

    Row0 1 0 0
    Row1 0 1 0
    Row2 0 0 1
    Row3 0 0 42.5

    Children 1

    Bone "WAIST"
    {
        Axis 0 0 1
        Angle 0
        Translation 0 0 5.2
        Scale 1 1 1

        Row0 1 0 0
        Row1 0 1 0
        Row2 0 0 1
        Row3 0 0 5.2

        Children 2

        Bone "CHEST"
        {
            ... (nested children)
        }

        Bone "ULEGR"
        {
            ... (sibling at same level)
        }

    }

}
```

#### Key Details
- **Coordinate space:** Parent-local (CTRL_RELATIVE with identity parent matrix)
- **Always samples frame 0** regardless of animation range (bind pose)
- **Hierarchical nesting:** Child bones are contained within parent bone braces
- **Row0-Row3:** Complete 4x3 transformation matrix included for validation
- **Children count:** Explicitly declared before child bone definitions
- **Indentation:** 4 spaces per depth level (cosmetic)

---

### Binary ANIM Format (Runtime Animation)

The binary ANIM format is written by GetAnimation2 and read directly by the game engine. Files are loaded as a single memory block with internal pointer offsets.

**Source:** `utilities/GetAnimation2/src/outputanim.c`
**Structures:** `Common/seq/animtrack.h`
**Loader:** `Common/seq/animtrack.c`

#### File Layout

```
Offset 0:
    ┌─────────────────────────────────────────────────────────┐
    │  SkeletonAnimTrack header                               │
    │  (headerSize, name[256], baseAnimName[256], etc.)       │
    ├─────────────────────────────────────────────────────────┤
    │  SkeletonHeirarchy (if this is a _skel file)            │
    │  (heirarchy_root + BoneLink[100])                       │
    ├─────────────────────────────────────────────────────────┤
    │  BoneAnimTrack[] array (bone_track_count entries)        │
    │  (rot_idx, pos_idx, counts, id, flags per bone)         │
    ├─────────────────────────────────────────────────────────┤
    │  Animation Key Data                                      │
    │  ├── Rotation keyframes (5 bytes each, compressed)       │
    │  └── Position keyframes (6 or 12 bytes each)             │
    └─────────────────────────────────────────────────────────┘
```

#### SkeletonAnimTrack (Main Header)

```c
struct SkeletonAnimTrack {
    int   headerSize;                            // Byte offset to animation data (MUST BE FIRST)
    char  name[256];                             // Animation path (e.g., "male/ready2")
    char  baseAnimName[256];                     // Reference skeleton (e.g., "male/skel_ready2")
    F32   max_hip_displacement;                  // For visibility culling
    F32   length;                                // Duration in frames (maxKeyRun - 1)
    BoneAnimTrack* bone_tracks;                  // OFFSET to BoneAnimTrack array (pointer fixup on load)
    int   bone_track_count;                      // Number of bone tracks
    int   rotation_compression_type;             // Bitfield: ROTATION_COMPRESSED_TO_5_BYTES etc.
    int   position_compression_type;             // Bitfield: POSITION_COMPRESSED_TO_6_BYTES etc.
    const SkeletonHeirarchy* skeletonHeirarchy;  // OFFSET to hierarchy (NULL if not _skel file)
    const SkeletonAnimTrack* backupAnimTrack;    // Runtime only (NULL on disk)
    int   loadstate;                             // Runtime only
    F32   lasttimeused;                          // Runtime only
    int   fileAge;                               // Runtime only
    int   spare_room[9];                         // Reserved padding
};
```

#### BoneAnimTrack (Per-Bone Track)

```c
typedef struct {
    const void* rot_idx;         // OFFSET to rotation key data
    const void* pos_idx;         // OFFSET to position key data
    U16  rot_fullkeycount;       // Number of rotation keyframes
    U16  pos_fullkeycount;       // Number of position keyframes
    U16  rot_count;              // Runtime count (after delta coding)
    U16  pos_count;              // Runtime count
    char id;                     // BoneId enum value
    char flags;                  // Compression flags for this bone
    unsigned short pack_pad;     // Explicit padding
} BoneAnimTrack;
```

#### SkeletonHeirarchy (Bone Tree, only in _skel files)

```c
typedef struct {
    int      heirarchy_root;                      // Index of root bone
    BoneLink skeleton_heirarchy[BONES_ON_DISK];   // 100 entries
} SkeletonHeirarchy;

typedef struct {
    int    child;    // First child bone index (-1 = no child)
    int    next;     // Next sibling bone index (-1 = no sibling)
    BoneId id;       // Bone ID (redundant verification)
} BoneLink;
```

#### Pointer Fixup on Load

All pointer fields (`bone_tracks`, `rot_idx`, `pos_idx`, `skeletonHeirarchy`) are stored as **byte offsets from the start of the file**. On load, the engine adds the base allocation address:

```c
skeleton->bone_tracks = (void*)((size_t)skeleton->bone_tracks + (size_t)skeleton);
for (i = 0; i < skeleton->bone_track_count; i++) {
    bt = &skeleton->bone_tracks[i];
    bt->pos_idx = (void*)((size_t)bt->pos_idx + (size_t)skeleton);
    bt->rot_idx = (void*)((size_t)bt->rot_idx + (size_t)skeleton);
}
if (skeleton->skeletonHeirarchy)
    skeleton->skeletonHeirarchy = (void*)((size_t)skeleton->skeletonHeirarchy + (size_t)skeleton);
```

#### Compression Constants

```c
// Rotation flags
#define ROTATION_UNCOMPRESSED           (1 << 0)  // 16 bytes: 4 floats (quaternion)
#define ROTATION_COMPRESSED_TO_5_BYTES  (1 << 1)  // 5 bytes: quantized quaternion
#define ROTATION_COMPRESSED_TO_8_BYTES  (1 << 2)  // 8 bytes: 4 shorts
#define ROTATION_DELTACODED             (1 << 5)
#define ROTATION_COMPRESSED_NONLINEAR   (1 << 7)

// Position flags
#define POSITION_UNCOMPRESSED           (1 << 3)  // 12 bytes: 3 floats (Vec3)
#define POSITION_COMPRESSED_TO_6_BYTES  (1 << 4)  // 6 bytes: 3 shorts
#define POSITION_DELTACODED             (1 << 6)

// Compression factors
#define CFACTOR_6BYTE_POS  32000       // Multiply float to get short
#define EFACTOR_6BYTE_POS  0.00003125  // 1/32000, multiply short to get float
#define CFACTOR_8BYTE_QUAT 10000
#define EFACTOR_8BYTE_QUAT 0.0001

// Limits
#define BONES_ON_DISK       100
#define MAX_ANIM_FILE_NAME_LEN 256
```

#### 5-Byte Quaternion Compression

The primary rotation compression used by GetAnimation2:

```
Compression (compressQuatToFiveBytes):
1. Normalize quaternion q = (x, y, z, w)
2. Force largest component to be positive (negate all if needed)
3. Identify which component to drop (largest, implicitly reconstructed)
4. Quantize remaining 3 components into ~13 bits each
5. Pack into 5 bytes (40 bits total)

Decompression (animExpand5ByteQuat / unPack5ByteQuat):
1. Read 5 bytes
2. Extract 3 quantized components + missing component index
3. Dequantize to floats
4. Reconstruct 4th component: missing = sqrt(1 - x² - y² - z²)
5. Output normalized quaternion
```

#### 6-Byte Position Compression

```
Compression (used when all components < 1.0):
  stored_value = (S16)(float_value * 32000)

Decompression:
  float_value = (F32)stored_value * (1.0f / 32000.0f)

Fallback to uncompressed (12 bytes) if any component >= 1.0
```

---

## Coordinate System Conversion

**3DS Max:** Right-handed, Z-up (X_right, Y_forward, Z_up)
**Game Engine:** Left-handed, Y-up (-X_left, Z_forward, -Y_?)

```c
// 3DS Max → Game (from processanim.c)
void ConvertCoordsFrom3DSMAX(Vec3 out, const Vec3 in) {
    out[0] = -in[0];    // Negate X
    out[1] =  in[2];    // Z → Y (up axis)
    out[2] = -in[1];    // Negate Y → Z
}

// Game → 3DS Max (inverse)
void ConvertCoordsGameTo3DSMAX(Vec3 out, const Vec3 in) {
    out[0] = -in[0];    // Negate X back
    out[1] = -in[2];    // Z → -Y
    out[2] =  in[1];    // Y → Z
}
```

**Blender** uses right-handed Y-up (X_right, Y_forward, Z_up) — similar to VRML:
```c
// VRML → 3DS Max (from processanim.c)
void ConvertCoordsVRMLTo3DSMAX(Vec3 out, const Vec3 in) {
    out[0] =  in[0];    // X stays
    out[1] = -in[2];    // Z → -Y
    out[2] =  in[1];    // Y → Z
}
```

So **Blender → Game** would be:
```
game[0] = -blender[0]   // Negate X (left-hand flip)
game[1] =  blender[2]   // Z → Y (Blender Z-up → Game Y-up)
game[2] =  blender[1]   // Y → Z
```
Wait — Blender is Z-up like 3DS Max, so:
```
Blender (right-hand Z-up) → Game (left-hand Y-up):
  game.x = -blender.x
  game.y =  blender.z
  game.z = -blender.y
  (Same as 3DS Max → Game conversion)
```

### World-to-Local Transform (Critical for Child Bones)

GetAnimation2 converts ANIMX world-space transforms to parent-relative local space:

```
For child bones (animxTransformJointKeysRelative):
1. Convert both parent and child from axis-angle to quaternion
2. qLocal = inverse(qParent) * qChild
3. vLocalPos = rotate(inverse(qParent), vChild - vParent)

For root bones (animxTransformJointKeysRoot):
1. Only apply coordinate conversion (3DS Max → Game)
2. No parent-relative transform needed
```

**Important:** The angle is negated during axis-angle → quaternion conversion:
```c
axisAngleToQuat(axis, -angle, quat);  // Note the negation
```

### Bind Pose Frame Insertion

GetAnimation2 inserts the skeleton's bind pose as frame 0:
```
frame0.axis = skeleton.rotate[0:3]
frame0.angle = skeleton.rotate[3]
frame0.translation = skeleton.translate
frame0.scale = (1, 1, 1)
// Inserted at index 0, shifting all animation frames forward
```

---

## Bone System

### Bone IDs (from Common/seq/bones.h)

119 total bones. The AUTO_ENUM macro generates string names by stripping the `BONEID_` prefix.
Node names in 3DS Max rigs must match these names exactly (case-insensitive).

```
ID  Enum Name            Node Name    Description
--  ------------------   ----------   ---------------------------------
0   BONEID_HIPS          HIPS         Root/pelvis bone
1   BONEID_WAIST         WAIST        Lower torso
2   BONEID_CHEST         CHEST        Upper torso
3   BONEID_NECK          NECK         Neck
4   BONEID_HEAD          HEAD         Head
5   BONEID_COL_R         COL_R        Right clavicle
6   BONEID_COL_L         COL_L        Left clavicle
7   BONEID_UARMR         UARMR        Right upper arm
8   BONEID_UARML         UARML        Left upper arm
9   BONEID_LARMR         LARMR        Right forearm
10  BONEID_LARML         LARML        Left forearm
11  BONEID_HANDR         HANDR        Right hand
12  BONEID_HANDL         HANDL        Left hand
13  BONEID_F1_R          F1_R         Right index finger
14  BONEID_F1_L          F1_L         Left index finger
15  BONEID_F2_R          F2_R         Right middle finger
16  BONEID_F2_L          F2_L         Left middle finger
17  BONEID_T1_R          T1_R         Right ring finger
18  BONEID_T1_L          T1_L         Left ring finger
19  BONEID_T2_R          T2_R         Right pinky
20  BONEID_T2_L          T2_L         Left pinky
21  BONEID_T3_R          T3_R         Right thumb
22  BONEID_T3_L          T3_L         Left thumb
23  BONEID_ULEGR         ULEGR        Right upper leg
24  BONEID_ULEGL         ULEGL        Left upper leg
25  BONEID_LLEGR         LLEGR        Right lower leg
26  BONEID_LLEGL         LLEGL        Left lower leg
27  BONEID_FOOTR         FOOTR        Right foot
28  BONEID_FOOTL         FOOTL        Left foot
29  BONEID_TOER          TOER         Right toe
30  BONEID_TOEL          TOEL         Left toe
31  BONEID_FACE          FACE         Face root
32  BONEID_DUMMY         DUMMY        Dummy bone
33  BONEID_BREAST        BREAST       Breast/chest piece
34  BONEID_BELT          BELT         Belt
35  BONEID_GLOVEL        GLOVEL       Left glove (note: L before R!)
36  BONEID_GLOVER        GLOVER       Right glove
37  BONEID_BOOTL         BOOTL        Left boot
38  BONEID_BOOTR         BOOTR        Right boot
39  BONEID_RINGL         RINGL        Left ring
40  BONEID_RINGR         RINGR        Right ring
41  BONEID_WEPL          WEPL         Left weapon
42  BONEID_WEPR          WEPR         Right weapon
43  BONEID_HAIR          HAIR         Hair
44  BONEID_EYES          EYES         Eyes
45  BONEID_EMBLEM        EMBLEM       Chest emblem
46  BONEID_SPADL         SPADL        Left shoulder pad
47  BONEID_SPADR         SPADR        Right shoulder pad
48  BONEID_BACK          BACK         Back attachment
49  BONEID_NECKLINE      NECKLINE     Neckline costume piece
50  BONEID_CLAWL         CLAWL        Left claw
51  BONEID_CLAWR         CLAWR        Right claw
52  BONEID_GUN           GUN          Gun bone
53  BONEID_RWING1        RWING1       Right wing 1
54  BONEID_RWING2        RWING2       Right wing 2
55  BONEID_RWING3        RWING3       Right wing 3
56  BONEID_RWING4        RWING4       Right wing 4
57  BONEID_LWING1        LWING1       Left wing 1
58  BONEID_LWING2        LWING2       Left wing 2
59  BONEID_LWING3        LWING3       Left wing 3
60  BONEID_LWING4        LWING4       Left wing 4
61  BONEID_MYSTIC        MYSTIC       Mystic effect bone
62  BONEID_SLEEVEL       SLEEVEL      Left sleeve
63  BONEID_SLEEVER       SLEEVER      Right sleeve
64  BONEID_ROBE          ROBE         Robe
65  BONEID_BENDMYSTIC    BENDMYSTIC   Bendable mystic
66  BONEID_COLLAR        COLLAR       Collar
67  BONEID_BROACH        BROACH       Broach/pin
68  BONEID_BOSOMR        BOSOMR       Right bosom
69  BONEID_BOSOML        BOSOML       Left bosom
70  BONEID_TOP           TOP          Shirt/top
71  BONEID_SKIRT         SKIRT        Skirt
72  BONEID_SLEEVES       SLEEVES      Sleeves (combined)
73  BONEID_BROW          BROW         Eyebrow
74  BONEID_CHEEKS        CHEEKS       Cheeks
75  BONEID_CHIN          CHIN         Chin
76  BONEID_CRANIUM       CRANIUM      Cranium/forehead
77  BONEID_JAW           JAW          Jaw
78  BONEID_NOSE          NOSE         Nose
79  BONEID_HIND_ULEGL    HIND_ULEGL   Quadruped hind left upper leg
80  BONEID_HIND_LLEGL    HIND_LLEGL   Quadruped hind left lower leg
81  BONEID_HIND_FOOTL    HIND_FOOTL   Quadruped hind left foot
82  BONEID_HIND_TOEL     HIND_TOEL    Quadruped hind left toe
83  BONEID_HIND_ULEGR    HIND_ULEGR   Quadruped hind right upper leg
84  BONEID_HIND_LLEGR    HIND_LLEGR   Quadruped hind right lower leg
85  BONEID_HIND_FOOTR    HIND_FOOTR   Quadruped hind right foot
86  BONEID_HIND_TOER     HIND_TOER    Quadruped hind right toe
87  BONEID_FORE_ULEGL    FORE_ULEGL   Quadruped fore left upper leg
88  BONEID_FORE_LLEGL    FORE_LLEGL   Quadruped fore left lower leg
89  BONEID_FORE_FOOTL    FORE_FOOTL   Quadruped fore left foot
90  BONEID_FORE_TOEL     FORE_TOEL    Quadruped fore left toe
91  BONEID_FORE_ULEGR    FORE_ULEGR   Quadruped fore right upper leg
92  BONEID_FORE_LLEGR    FORE_LLEGR   Quadruped fore right lower leg
93  BONEID_FORE_FOOTR    FORE_FOOTR   Quadruped fore right foot
94  BONEID_FORE_TOER     FORE_TOER    Quadruped fore right toe
95  BONEID_LEG_L_JET1    LEG_L_JET1   Left leg jet thruster 1
96  BONEID_LEG_L_JET2    LEG_L_JET2   Left leg jet thruster 2
97  BONEID_LEG_R_JET1    LEG_R_JET1   Right leg jet thruster 1
98  BONEID_LEG_R_JET2    LEG_R_JET2   Right leg jet thruster 2
```

Special pseudo-bones: `TEX_1` (mapped to ID 0) and `TEX_2` (mapped to ID 1) for scrolling texture animations.

### Standard Humanoid Hierarchy

```
HIPS (root)
├── WAIST
│   └── CHEST
│       ├── NECK
│       │   └── HEAD
│       │       ├── FACE
│       │       │   ├── BROW, CHEEKS, CHIN, CRANIUM, JAW, NOSE
│       │       │   └── EYES
│       │       └── HAIR
│       ├── COL_R
│       │   └── UARMR
│       │       └── LARMR
│       │           └── HANDR
│       │               ├── F1_R, F2_R
│       │               └── T1_R → T2_R → T3_R
│       ├── COL_L
│       │   └── UARML
│       │       └── LARML
│       │           └── HANDL
│       │               ├── F1_L, F2_L
│       │               └── T1_L → T2_L → T3_L
│       ├── EMBLEM, BREAST, COLLAR, BROACH, TOP
│       ├── MYSTIC, BENDMYSTIC, ROBE
│       └── RWING1-4, LWING1-4, BACK
├── ULEGR
│   └── LLEGR
│       └── FOOTR
│           └── TOER
├── ULEGL
│   └── LLEGL
│       └── FOOTL
│           └── TOEL
├── BELT, SKIRT
└── (costume bones: GLOVEL/R, BOOTL/R, WEPL/R, etc.)
```

---

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
    skel_ready2.skelx    (skeleton file, must have skel_ prefix)
    animation1.animx
    animation2.animx
```
Run GA2 from the body type folder level.

### GA2 Processing Pipeline (from mainanim.c)

1. Scan folder recursively for `.ANIMX` and `.SKELX` files
2. Find the unique base skeleton (`skel_*.skelx`) in each folder
3. Load and convert skeleton (`LoadSkeletonSKELX`):
   - Parse text → TSkelX bone tree
   - Convert coords: 3DS Max → Game
   - Assign bone IDs from name lookup
   - Prune non-animation bones
   - Build Node tree with bind poses
4. For each `.ANIMX` file (`animConvert_ANIMX_To_AnimTrack`):
   - Parse text → TAnimX bone/frame data
   - Build bone mapping (animation bone → skeleton bone)
   - Insert bind pose at frame 0
   - Convert coords: 3DS Max → Game
   - Convert world space → parent-local space
   - Build compressed BoneAnimTracks
   - Write binary `.anim` file

### Animation Name Convention

```
Input:  player_library/animations/male/models/ready2.ANIMX
Output: player_library/animations/male/ready2.anim
Name:   "male/ready2" (stored in binary header)
```

If the animation name contains `skel_`, the SkeletonHeirarchy is embedded in the output.

---

## Implementation Strategy

### Phase 1: ANIMX/SKELX Support (Replaces 3DS Max)
- Blender addon that imports/exports ANIMX and SKELX text formats
- Includes master rig setup in Blender matching CoH bone hierarchy
- Users still need GA2 for final ANIMX → ANIM conversion
- Fastest path to a working tool

**Key implementation tasks:**
1. Build CoH armature in Blender with correct bone names and hierarchy
2. ANIMX exporter: sample bone transforms per frame, write text format
3. SKELX exporter: write bone hierarchy with bind pose transforms
4. Handle coordinate conversion: Blender (right-hand Z-up) → 3DS Max convention
5. Handle transform space: Blender local → world space (matching 3DS Max CTRL_RELATIVE)
6. ANIMX importer: parse text, create keyframes on armature
7. SKELX importer: parse text, build armature

### Phase 2: Direct ANIM Binary Support (Replaces GA2)
- Add binary ANIM read/write to the Blender addon
- Implement 5-byte quaternion compression/decompression
- Implement 6-byte position compression
- Handle pointer offset fixup for binary format
- Implement world-to-local transform conversion
- Implement bind pose frame insertion
- Complete standalone workflow: Blender → .ANIM directly

**Key implementation tasks:**
1. Binary ANIM reader with pointer fixup
2. Binary ANIM writer with offset calculation
3. 5-byte quaternion compress/decompress
4. 6-byte position compress/decompress
5. Skeleton hierarchy serialization
6. World-to-local bone transform conversion
7. SKEL file reading (for skeleton reference)

---

## Reference Blender Plugins (Architecture Examples)
- [io_anim_seanim](https://github.com/SE2Dev/io_anim_seanim) - SEAnim import/export
- [Blender_io-scene-ANIM](https://github.com/PositionWizard/Blender_io-scene-ANIM) - Maya ANIM import/export
- [io_anim_hkx](https://github.com/opparco/io_anim_hkx) - Skyrim HKX animation import/export

## Key Resources
- [OuroDev Wiki - Creating Animations](https://wiki.ourodev.com/Creating_new_Animations_(3DS_MAX))
- Source: `utilities/3dsmax/coh_anim_exp/` - ANIMX/SKELX exporter
- Source: `utilities/3dsmax/coh_anim_imp/` - ANIMX importer
- Source: `utilities/GetAnimation2/` - ANIMX→ANIM converter
- Source: `Common/seq/animtrack.h` - Binary format structures
- Source: `Common/seq/bones.h` - Bone ID definitions

## Source File Quick Reference

| File | Purpose |
|------|---------|
| `utilities/3dsmax/coh_anim_exp/animexp.cpp` | ANIMX text format writer (3DS Max plugin) |
| `utilities/3dsmax/coh_anim_exp/skelexp.cpp` | SKELX text format writer (3DS Max plugin) |
| `utilities/3dsmax/coh_anim_imp/import_animx.c` | ANIMX text format parser/data structures |
| `utilities/GetAnimation2/src/process_animx.c` | ANIMX → binary conversion logic |
| `utilities/GetAnimation2/src/process_skelx.c` | SKELX → Node tree conversion |
| `utilities/GetAnimation2/src/processanim.c` | Coord conversion, bone assignment, hierarchy |
| `utilities/GetAnimation2/src/outputanim.c` | Binary ANIM file writer |
| `utilities/GetAnimation2/src/mainanim.c` | Main GA2 processing pipeline |
| `Common/seq/animtrack.h` | Binary format struct definitions |
| `Common/seq/animtrack.c` | Binary format loader with pointer fixup |
| `Common/seq/bones.h` | Bone ID enum (119 bones) |
| `Common/seq/bones.c` | Bone name ↔ ID lookup functions |

## Important Technical Notes
- Body types: `male`, `fem`, `huge` — each has its own skeleton
- GEO_* bones in ANIMX must be stripped or GA2 crashes
- Bone names are case-insensitive in lookups
- ANIM files contain an internal path reference to their SKEL file
- The matching SKEL file must be accessible at the referenced path
- Frame 0 is always the bind pose (inserted by GA2)
- Animation data starts at frame 1 in the binary format
- Position compression threshold: all components must be < 1.0 for 6-byte mode
- Quaternion compression: largest component dropped, 3 remaining quantized to ~13 bits each
- `BONES_ON_DISK = 100` (maximum bones written to file, though `BONEID_COUNT = 119`)
- Delta coding flags exist but may not be used by standard GA2 output
