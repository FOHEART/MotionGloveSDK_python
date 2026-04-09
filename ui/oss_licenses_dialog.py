"""开源声明对话框

列出本项目所使用的所有第三方开源库及其许可证信息。
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox,
)
from PySide6.QtCore import Qt

_LICENSES_TEXT = """\
<h2>开源声明</h2>
<p>本项目使用了以下第三方开源组件，感谢各开源社区的贡献。</p>
<hr>

<h3>VTK (Visualization Toolkit) 9.6.0</h3>
<p><b>许可证：</b>BSD 3-Clause License<br>
<b>版权：</b>Copyright &copy; 1993-2015 Ken Martin, Will Schroeder, Bill Lorensen<br>
<b>主页：</b>https://vtk.org</p>
<p>Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met: (1) Redistributions
of source code must retain the above copyright notice; (2) Redistributions in
binary form must reproduce the above copyright notice; (3) Neither the name of the
copyright holder nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written permission.</p>
<hr>

<h3>NumPy 2.2.6</h3>
<p><b>许可证：</b>BSD 3-Clause License<br>
<b>版权：</b>Copyright &copy; 2005-2024 NumPy Developers</p>
<p>Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the BSD 3-Clause conditions are met.</p>
<hr>

<h3>Matplotlib 3.10.8</h3>
<p><b>许可证：</b>Matplotlib License (PSF-compatible)<br>
<b>版权：</b>Copyright &copy; 2012- Matplotlib Development Team<br>
<b>主页：</b>https://matplotlib.org</p>
<p>Matplotlib only uses BSD compatible code, and its license is based on the PSF
license. See https://matplotlib.org/stable/users/project/license.html for details.</p>
<hr>

<h3>Pillow 12.1.1</h3>
<p><b>许可证：</b>HPND License (MIT-CMU)<br>
<b>版权：</b>Copyright &copy; 1997-2011 Secret Labs AB / Fredrik Lundh; Copyright &copy; 2010- Jeffrey A. Clark<br>
<b>主页：</b>https://python-pillow.org</p>
<p>Permission to use, copy, modify, and distribute this software and its documentation
for any purpose and without fee is hereby granted.</p>
<hr>

<h3>PySide6 / shiboken6 6.5.3</h3>
<p><b>许可证：</b>GNU Lesser General Public License v3.0 (LGPL-3.0)<br>
<b>版权：</b>Copyright &copy; The Qt Company Ltd.<br>
<b>主页：</b>https://www.qt.io/qt-for-python</p>
<p>This library is free software; you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free Software
Foundation; either version 3 of the License, or (at your option) any later version.</p>
<hr>

<h3>pyparsing 3.3.2</h3>
<p><b>许可证：</b>MIT License<br>
<b>版权：</b>Copyright &copy; 2003-2025 Paul McGuire</p>
<p>Permission is hereby granted, free of charge, to any person obtaining a copy of
this software to deal in the Software without restriction.</p>
<hr>

<h3>python-dateutil 2.9.0</h3>
<p><b>许可证：</b>Apache License 2.0<br>
<b>版权：</b>Copyright &copy; 2017- Paul Ganssle and dateutil contributors</p>
<p>Licensed under the Apache License, Version 2.0. You may obtain a copy at
http://www.apache.org/licenses/LICENSE-2.0</p>
<hr>

<h3>packaging 26.0</h3>
<p><b>许可证：</b>Apache License 2.0 OR BSD 2-Clause<br>
<b>版权：</b>Copyright &copy; Donald Stufft and contributors</p>
<hr>

<h3>fonttools 4.62.0</h3>
<p><b>许可证：</b>MIT License<br>
<b>版权：</b>Copyright &copy; 2017- Just van Rossum and contributors</p>
<hr>

<h3>contourpy 1.3.2</h3>
<p><b>许可证：</b>BSD 3-Clause License<br>
<b>版权：</b>Copyright &copy; 2021-2025 ContourPy Developers</p>
<hr>

<h3>cycler 0.12.1</h3>
<p><b>许可证：</b>BSD 3-Clause License<br>
<b>版权：</b>Copyright &copy; 2015- Matplotlib Project</p>
<hr>

<h3>kiwisolver 1.4.9</h3>
<p><b>许可证：</b>BSD 3-Clause License<br>
<b>版权：</b>Copyright &copy; 2013-2025 Nucleic Development Team</p>
<hr>

<h3>six 1.17.0</h3>
<p><b>许可证：</b>MIT License<br>
<b>版权：</b>Copyright &copy; 2010-2024 Benjamin Peterson</p>
<hr>

<h3>HarmonyOS Sans SC Regular</h3>
<p><b>来源：</b>Huawei Technologies Co., Ltd.<br>
<b>用途：</b>3D 视图中文叠加文字渲染</p>
<p>本字体文件由华为技术有限公司提供，仅用于 MotionGlove 3D 视图界面的中文显示。
如需了解完整许可条款，请访问华为官方网站。</p>
<hr>
<p style="color: gray; font-size: small;">
以上信息仅供参考。各库的完整许可证文本请参阅对应项目的官方源码仓库。
</p>
"""


class OssLicensesDialog(QDialog):
    """显示第三方开源库许可证声明的对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("开源声明")
        self.resize(680, 520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_LICENSES_TEXT)
        layout.addWidget(browser)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
