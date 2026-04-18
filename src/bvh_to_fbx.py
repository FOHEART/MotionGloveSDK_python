"""bvh_to_fbx.py
在 Blender 后台模式下将 BVH 文件批量转换为 FBX。

用法（命令行）：
    blender --background --python scripts/bvh_to_fbx.py -- csvfile/
    blender --background --python scripts/bvh_to_fbx.py -- csvfile/stance4.bvh
    blender --background --python scripts/bvh_to_fbx.py -- csvfile/ --scale 1.0

参数（-- 之后）：
    input       BVH 文件路径 或 包含 BVH 文件的目录
    --scale     导入缩放比例，默认 0.01（厘米→米）
    --fps       动画帧率，默认从文件自动读取
"""

import sys
import argparse
from pathlib import Path

import bpy


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def convert(bvh_path: Path, scale: float, fps: int | None) -> Path:
    clear_scene()

    bpy.ops.import_anim.bvh(
        filepath=str(bvh_path),
        global_scale=scale,
        use_fps_scale=False,
        update_scene_fps=True,
        update_scene_duration=True,
        rotate_mode="NATIVE",
        axis_forward="-Z",
        axis_up="Y",
    )

    if fps is not None:
        bpy.context.scene.render.fps = fps

    fbx_path = bvh_path.with_suffix(".fbx")
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=False,
        apply_scale_options="FBX_SCALE_NONE",
        axis_forward="-Z",
        axis_up="Y",
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_simplify_factor=0.0,
        add_leaf_bones=False,
    )

    return fbx_path


def main() -> None:
    # -- 之后的参数才是脚本参数
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        print("[bvh_to_fbx] 未传入参数，退出。")
        sys.exit(1)

    parser = argparse.ArgumentParser(prog="bvh_to_fbx.py")
    parser.add_argument("input", help="BVH 文件或目录")
    parser.add_argument("--scale", type=float, default=0.01,
                        help="导入缩放比例（默认 0.01，厘米→米）")
    parser.add_argument("--fps", type=int, default=None,
                        help="强制指定帧率（默认从 BVH 自动读取）")
    args = parser.parse_args(script_args)

    input_path = Path(args.input)
    if input_path.is_dir():
        bvh_files = sorted(input_path.glob("*.bvh"))
    elif input_path.is_file():
        bvh_files = [input_path]
    else:
        print(f"[bvh_to_fbx] 路径不存在：{input_path}")
        sys.exit(1)

    if not bvh_files:
        print(f"[bvh_to_fbx] 未找到 BVH 文件：{input_path}")
        sys.exit(1)

    for bvh in bvh_files:
        print(f"[bvh_to_fbx] 转换：{bvh}")
        fbx = convert(bvh, args.scale, args.fps)
        print(f"[bvh_to_fbx] 完成：{fbx}")


main()
