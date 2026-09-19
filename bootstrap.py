"""Prepare the desktop environment using only the project's offline wheels."""
import hashlib
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import sysconfig
import venv

ROOT = Path(__file__).resolve().parent

def runtime_dir():
    return ROOT / ".runtime" / ("py" + str(sys.version_info.major) + str(sys.version_info.minor))

def ensure_environment():
    if (sys.platform != "win32" or platform.python_implementation() != "CPython"
            or struct.calcsize("P") != 8 or sysconfig.get_platform() != "win-amd64"
            or not (3, 10) <= sys.version_info[:2] <= (3, 14)
            or sysconfig.get_config_var("Py_GIL_DISABLED")):
        raise RuntimeError("离线桌面版需要 Windows x64 和标准版 Python 3.10–3.14（64 位）。")
    destination = runtime_dir()
    python = destination / "Scripts" / "python.exe"
    requirements = ROOT / "requirements-offline.txt"
    wheels = ROOT / "vendor" / "wheels"
    manifest_path = wheels / "SHA256.json"
    if not manifest_path.is_file():
        raise RuntimeError("缺少 vendor/wheels 离线依赖包，请重新下载完整项目。")
    fingerprint = hashlib.sha256(requirements.read_bytes() + manifest_path.read_bytes()
                                 + str(ROOT).encode() + sys.base_prefix.encode()).hexdigest()
    marker = destination / "ready.txt"
    if python.is_file() and marker.is_file() and marker.read_text() == fingerprint:
        return python
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A process-held lock is released automatically even if setup is interrupted.
    import msvcrt
    with (destination.parent / "setup.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("另一个窗口正在准备运行环境，请稍后重新打开。") from None
        if python.is_file() and marker.is_file() and marker.read_text() == fingerprint:
            return python
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest:
            raise RuntimeError("离线依赖清单为空，请重新下载完整项目。")
        for name, digest in manifest.items():
            if Path(name).name != name or not name.endswith(".whl"):
                raise RuntimeError("离线依赖清单格式错误。")
            path = wheels / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise RuntimeError("离线依赖缺失或损坏：" + name + "；请重新下载完整项目。")
        marker.unlink(missing_ok=True)
        if sys.stdout is not None:
            print("正在从项目离线安装运行依赖，首次启动请稍候…", flush=True)
        log_path = ROOT / ".runtime" / "setup.log"
        with log_path.open("w", encoding="utf-8") as log:
            # Keep ensurepip output visible in the log even with pythonw.
            venv.EnvBuilder(with_pip=False).create(destination)
            flags = subprocess.CREATE_NO_WINDOW
            for command in ([str(python), "-I", "-m", "ensurepip", "--upgrade"],
                            [str(python), "-I", "-m", "pip", "--isolated", "install",
                             "--no-index", "--no-cache-dir", "--find-links", str(wheels),
                             "--only-binary=:all:", "-r", str(requirements)],
                            [str(python), "-I", "-c",
                             "from PySide6 import QtCore, QtGui, QtWidgets, QtQml, QtQuick, QtQuickControls2; import jsonschema"]):
                result = subprocess.run(command, stdout=log, stderr=log, creationflags=flags)
                if result.returncode:
                    raise RuntimeError("自动准备环境失败，请查看 " + str(log_path)
                                       + "。关闭程序后重试可继续安装。")
        marker.write_text(fingerprint)
    return python

def launch_if_needed():
    """Return a child exit code, or None when already inside the prepared venv."""
    python = ensure_environment()
    if Path(sys.prefix).resolve() == runtime_dir().resolve():
        return None
    windowless = sys.executable.lower().endswith("pythonw.exe")
    executable = python.with_name("pythonw.exe") if windowless else python
    entry = ROOT / ("gui.pyw" if windowless else "gui.py")
    return subprocess.call([str(executable), str(entry)], cwd=ROOT)
