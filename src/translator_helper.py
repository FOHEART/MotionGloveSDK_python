"""
@file  translator_helper.py
@brief MotionGlove 3D 查看器的 Qt 翻译器辅助模块。
@details 处理语言配置（config.json 的 language 字段）与 Qt 翻译器安装；
         语言文件位于 script_dir/translations/<lang>.qm，缺失时降级英文。
"""

import os
from PySide6.QtCore import QTranslator


def install_configured_translator(app, script_dir: str) -> tuple:
    """@brief 安装或更新 Qt 应用配置好的翻译器。

    @details 语言代码从 config.json 的 language 字段读取（默认 "en"）。
             已安装过相同语言时直接复用；语言变化时先移除旧翻译器再装新。
             翻译文件缺失或加载失败时仅打印告警，不抛异常。

    @param app        QApplication 实例（在其上调用 installTranslator）。
    @param script_dir 脚本目录绝对路径（用于定位 translations 子目录）。
    @return (translator, lang_code) 二元组：安装的 QTranslator 与语言代码。
    """
    try:
        from src.config_io import read_config
        cfg = read_config()
        lang_code = cfg.get("language", "en")
    except Exception:
        lang_code = "en"

    existing_translator = getattr(app, "_motionglove_translator", None)
    existing_lang = getattr(app, "_motionglove_language", None)
    if existing_translator is not None and existing_lang == lang_code:
        return existing_translator, lang_code

    if existing_translator is not None:
        app.removeTranslator(existing_translator)

    translator = QTranslator()
    qm_path = os.path.join(script_dir, "translations", f"{lang_code}.qm")
    try:
        if os.path.exists(qm_path) and translator.load(qm_path):
            app.installTranslator(translator)
        else:
            print(f"Translation not loaded (missing): {qm_path}")
    except Exception as e:
        print(f"Error loading translator: {e}")

    app._motionglove_translator = translator
    app._motionglove_language = lang_code
    return translator, lang_code
