## ADDED Requirements

### Requirement: 42-bone skeleton data model
The system SHALL define 42 `BoneIndex` enum members and a corresponding `KHHS42_SKELETON_COUNT = 42` constant in `src/definitions.py`. The 10 additional bones SHALL be the end-nodes: `RightHandThumb3End`, `RightHandIndex3End`, `RightHandMiddle3End`, `RightHandRing3End`, `RightHandPinky3End`, `LeftHandThumb3End`, `LeftHandIndex3End`, `LeftHandMiddle3End`, `LeftHandRing3End`, `LeftHandPinky3End`. The `BONE_NAMES` list SHALL contain all 42 names in index order matching the tree in `src/kinemHumanHandsSkeleton42Index_tree.md`.

#### Scenario: BoneIndex covers all 42 bones
- **WHEN** code accesses `BoneIndex.RightHandThumb3End` through `BoneIndex.LeftHandPinky3End`
- **THEN** each resolves to a unique integer index in the range 0–41

#### Scenario: BONE_NAMES list length is 42
- **WHEN** `len(BONE_NAMES)` is evaluated
- **THEN** it equals 42

### Requirement: End-node bones carry position only
End-node bones (names ending with `End`) SHALL have their `position` field populated with the real fingertip world-space coordinates. Their `euler_degree` SHALL be `[0, 0, 0]` and the derived `quat_wxyz` SHALL be the identity quaternion. The renderer SHALL NOT use the rotation data of end-node bones for any visual output.

#### Scenario: End-node position is non-zero
- **WHEN** a 42-bone UDP frame is received and parsed
- **THEN** `frame.skeletons[BoneIndex.RightHandIndex3End].position` contains a non-zero world-space coordinate

#### Scenario: End-node rotation is identity
- **WHEN** a 42-bone UDP frame is received and parsed
- **THEN** `frame.skeletons[BoneIndex.RightHandIndex3End].euler_degree` equals `[0.0, 0.0, 0.0]`
