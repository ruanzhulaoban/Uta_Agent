"""Windows desktop entry point without a console window."""
import ctypes
import traceback


if __name__ == "__main__":
    try:
        from gui import main

        exit_code = main()
        if exit_code:
            ctypes.windll.user32.MessageBoxW(
                None,
                "启动失败。请确认下载并解压了完整项目。\n"
                "自动安装日志位于 .runtime/setup.log。\n\n"
                "可运行 python gui.py 查看详细诊断。",
                "utaagent 启动失败",
                0x10,
            )
    except Exception:
        ctypes.windll.user32.MessageBoxW(
            None, traceback.format_exc(), "utaagent 启动失败", 0x10
        )
        exit_code = 1
    raise SystemExit(exit_code)
