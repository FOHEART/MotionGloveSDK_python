"""
Translator helper module for MotionGlove 3D Viewer.
Handles language configuration and Qt translator installation.
"""

import os
from PySide6.QtCore import QTranslator


def install_configured_translator(app, script_dir: str) -> tuple:
    """
    Install or update the configured translator for the Qt application.
    
    Args:
        app: QApplication instance
        script_dir: Path to the script directory (for locating translations)
    
    Returns:
        Tuple of (translator, lang_code)
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
