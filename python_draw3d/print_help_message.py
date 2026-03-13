"""操作提示打印"""

import vtk


def print_help_message():
    print("=" * 55)
    print("  3D Lines Viewer  (VTK {})".format(vtk.vtkVersion.GetVTKVersion()))
    print("=" * 55)
    print("-" * 55)
    print("  鼠标左键  旋转视角")
    print("  鼠标右键  缩放")
    print("  鼠标中键  平移")
    print("  按 空格   重置相机视角")
    print("  按 R 键   重置视角")
    print("  按 Q 键   退出")
    print("=" * 55)
