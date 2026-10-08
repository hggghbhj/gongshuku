# -*- coding: utf-8 -*-
"""playwright chromium 路径自适应。
云电脑浏览器在 /usr/local/bin/chromium；GitHub Actions 由 `playwright install chromium`
装到 ~/.cache/ms-playwright/。返回 None 时用 playwright 自带默认浏览器。
"""
import os,glob

def chromium_path():
    if os.path.exists("/usr/local/bin/chromium"):
        return "/usr/local/bin/chromium"
    for pat in (
        "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        "~/.cache/ms-playwright/chromium*/chrome-linux/chrome",
    ):
        c=sorted(glob.glob(os.path.expanduser(pat)))
        if c:
            return c[0]
    return None
