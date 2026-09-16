"""Qt Quick desktop entry point."""
import sys
import os
from pathlib import Path

def main():
    try:
        import PySide6
        dll_directory = os.add_dll_directory(str(Path(PySide6.__file__).parent)) if os.name == "nt" else None
        from PySide6.QtQuick import QQuickWindow
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
        from utaagent_core.desktop import Backend
    except ImportError:
        print("请先运行：python -m pip install -r requirements-gui.txt")
        return 1
    app = QApplication(sys.argv)
    app.setOrganizationName("Utaagent")
    app.setApplicationName("歌词手帖")
    QQuickStyle.setStyle("Basic")
    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parent / "utaagent_core" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
