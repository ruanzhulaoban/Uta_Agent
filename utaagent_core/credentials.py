"""Windows user environment persistence; never log credential values."""
import os
import re

def read_key(name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return ""
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, kind = winreg.QueryValueEx(key, name)
                if kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) and isinstance(value, str):
                    return value
        except OSError:
            pass
    return os.environ.get(name, "")

def save_key(name, value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*API_KEY", name) or not value or "\x00" in value:
        raise ValueError("请使用以 API_KEY 结尾的环境变量名并填写密钥")
    if os.name != "nt":
        raise OSError("持久环境变量保存目前支持 Windows")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    os.environ[name] = value
    # Notify shells of the changed user environment; existing processes may retain old values.
    import ctypes
    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xffff, 0x001A, 0, "Environment", 2, 1000, ctypes.byref(result))
