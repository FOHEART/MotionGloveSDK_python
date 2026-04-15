## 1. Update data model — `src/definitions.py`

- [x] 1.1 Add 10 new `BoneIndex` enum members: `RightHandThumb3End` … `LeftHandPinky3End` in the correct tree order (after each `*3` bone, right hand first then left hand)
- [x] 1.2 Update `KHHS32_SKELETON_COUNT` → rename to `KHHS42_SKELETON_COUNT = 42` (keep a `KHHS32_SKELETON_COUNT = 32` alias if needed for CSV compatibility, otherwise just update the constant)
- [x] 1.3 Extend `BONE_NAMES` list with the 10 new names in index order

## 2. Update 3D viewer constants — `motionGloveSDK_example3_3dView.py`

- [x] 2.1 Replace `KHHS32_SKELETON_COUNT` import/usage with the new 42-bone constant
- [x] 2.2 Remove `FINGERTIP_BONE_LENGTH` constant
- [x] 2.3 Remove `_FINGERTIP_BONES` list
- [x] 2.4 Add 10 new entries to `_BONE_LINKS` for each `*3` → `*3End` connection (right hand then left hand, matching tree order)
- [x] 2.5 Rebuild `_BONE_PARENT` lookup — it is derived from `_BONE_LINKS` automatically, no manual changes needed beyond verifying it covers all 42 bones

## 3. Update actor creation — `_build_vtk_scene`

- [x] 3.1 Change `self._joint_actors` list comprehension to iterate over 42 bones instead of 32
- [x] 3.2 Remove `self._fingertip_actors` creation block (the 10 `BoneLinkActor` instances)
- [x] 3.3 Verify `self._link_actors` now includes the 10 end-node links (automatically, since `_BONE_LINKS` was extended)

## 4. Update render loop — `_on_timer`

- [x] 4.1 Build an `_END_BONE_INDICES` set at module level: indices of all `BoneIndex` members whose name ends with `End`
- [x] 4.2 In the joint-actor render loop, branch on `_END_BONE_INDICES`: call `set_position_only()` for end-nodes (skip quaternion accumulation result), `set_pose()` for all others — existing logic already handles `set_position_only` when `global_quats[i] is None`, so setting `global_quats[i] = None` for end-nodes after accumulation achieves this cleanly
- [x] 4.3 Remove the `_fingertip_actors` render block (the loop over `_FINGERTIP_BONES` with Y-axis quaternion projection)
- [x] 4.4 Remove `self._fingertip_actors` from the DrawConfig sync block in `_on_timer`

## 5. Verify

- [x] 5.1 Run CI smoke test: `MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0 python motionGloveSDK_example3_3dView.py` — must exit cleanly
- [ ] 5.2 Confirm with live 42-bone UDP stream: all 10 fingertip spheres appear at correct positions with no axis tripods
