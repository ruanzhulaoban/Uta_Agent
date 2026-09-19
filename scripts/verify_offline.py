"""Offline integration checks. Run with .runtime/pyXYZ/Scripts/python.exe."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["PATH"] = os.path.join(os.environ["SystemRoot"], "System32")
for name in ("MECAB_PATH", "MECAB_BIN", "MECAB_DICDIR", "MECABRC"):
    os.environ.pop(name, None)

import bootstrap
from utaagent_core import mecab

class OfflineTests(unittest.TestCase):
    def test_wheel_integrity(self):
        folder = ROOT / "vendor/wheels"
        manifest = json.loads((folder / "SHA256.json").read_text())
        self.assertGreater(len(manifest), 0)
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected)

    def test_bundled_tokenizer_without_system_paths(self):
        parser = mecab.MeCab()
        self.assertTrue(Path(parser.path).is_relative_to(ROOT / "vendor"))
        tokens = parser.parse_line("君の歌を聞きたい。")
        self.assertEqual("".join(t.surface for t in tokens), "君の歌を聞きたい。")
        self.assertEqual(tokens[0].reading, "キミ")

    def test_relocated_native_bundle(self):
        with tempfile.TemporaryDirectory(prefix="歌词 空格 ", dir=ROOT / ".runtime") as temp:
            target = Path(temp) / "mecab"
            shutil.copytree(ROOT / "vendor/mecab", target)
            with patch.object(mecab, "_BUNDLED", target):
                parser = mecab.MeCab()
                self.assertEqual(parser.parse_line("日本語")[0].reading, "ニホンゴ")

    def test_offline_generation_and_qml(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
        from utaagent_core.desktop import Backend, DEFAULTS
        from utaagent_core.library import Library, generate
        with tempfile.TemporaryDirectory(dir=ROOT / ".runtime") as temp:
            library = Library(temp)
            settings = dict(DEFAULTS, no_llm=True)
            with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network request")):
                book_id, _, _ = generate(library, "君の歌を聞きたい。", "离线测试", settings, "", lambda _: None)
            self.assertIn("君", (library.path(book_id) / "book.html").read_text(encoding="utf-8"))
            self.assertEqual(len(library.items()), 1)
            app = QApplication.instance() or QApplication([])
            QQuickStyle.setStyle("Basic")
            backend = Backend(library=library)
            engine = QQmlApplicationEngine()
            engine.rootContext().setContextProperty("backend", backend)
            engine.load(QUrl.fromLocalFile(str(ROOT / "utaagent_core/qml/Main.qml")))
            self.assertTrue(engine.rootObjects(), "QML failed to load")
            app.processEvents()
            for window in engine.rootObjects():
                window.close()
            del engine

    def test_reject_corrupt_install_bundle(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".runtime") as temp:
            root = Path(temp)
            (root / "requirements-offline.txt").write_text("jsonschema==4.25.1")
            wheels = root / "vendor/wheels"
            wheels.mkdir(parents=True)
            (wheels / "SHA256.json").write_text(json.dumps({"missing.whl": "0" * 64}))
            with patch.object(bootstrap, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "missing.whl"):
                    bootstrap.ensure_environment()

if __name__ == "__main__":
    unittest.main()
