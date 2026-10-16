#!/usr/bin/env python3
"""Regenerate android/res/values-zh-rTW from values-zh (Simplified Chinese).

Local patch, see PATCHES.md. Pipeline: OpenCC s2twp, then the ordered Taiwan
wording table below (text nodes only; resource names and attributes are left
alone), then parity checks against values-zh.

    python3 tools/zh-tw/s2tw.py          # rewrite values-zh-rTW
    python3 tools/zh-tw/s2tw.py --check  # exit 1 if regenerating would change files
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import xml.dom.minidom

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "android", "res", "values-zh")
DST = os.path.join(ROOT, "android", "res", "values-zh-rTW")
FILES = ["strings_crash.xml", "strings_game_settings.xml", "strings_log_analysis.xml", "strings_log_detail.xml"]
APP_NAME = '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n\t<string name="godot_project_name_string">殺戮尖塔2</string>\n</resources>\n'

# Applied in order to every text node. Earlier entries protect phrases that a
# later, shorter entry would otherwise rewrite.
STAGE_1 = [
    ("豎屏（需配合豎屏 MOD）", "直向（需搭配直向 MOD）"), ("豎屏", "直向"), ("橫屏", "橫向"), ("豎向", "直向"), ("需配合", "需搭配"),
    ("併兼容", "並相容"), ("兼容", "相容"), ("同意併發送", "同意並傳送"), ("併發數", "並行數"), ("分塊併發", "分塊並行"), ("頁併發起", "頁並發起"),
    ("加載", "載入"), ("賬號", "帳號"), ("賬戶", "帳戶"), ("賬", "帳"),
    ("重啟遊戲程序", "重新啟動遊戲"), ("結束當前遊戲程序", "結束目前的遊戲"), ("登入程序", "登入流程"),
    ("質量", "品質"), ("獲取", "取得"),
    ("訪問尖塔", "造訪尖塔"), ("訪問網頁", "造訪網頁"), ("訪問", "存取"),
    ("拖動", "拖曳"), ("回退", "備援"), ("聯機", "連線"),
    ("手機令牌動態碼", "行動驗證器代碼"), ("令牌", "權杖"),
    ("彈窗", "對話框"), ("郵箱", "電子郵件"), ("此操作不可撤銷", "此操作無法復原"), ("撤銷本應用", "釋放本應用"),
    ("適配螢幕", "配合螢幕"), ("使用者協議", "使用條款"), ("下載協議", "下載協定"), ("驅動開銷", "驅動程式開銷"),
    ("自定義", "自訂"), ("啟動配置", "啟動設定檔"), ("配置", "設定"),
    ("解壓縮", "解壓"), ("解壓", "解壓縮"), ("壓縮包", "壓縮檔"),
    ("所選專案", "所選項目"), ("兩個專案", "兩個項目"), ("預載入專案", "預載入項目"),
    ("本地", "本機"), ("當前", "目前"), ("檢測", "偵測"), ("通過", "透過"), ("站點", "網站"), ("憑據", "憑證"), ("校驗", "驗證"),
    ("選中", "選取"), ("區域網路", "區域網"), ("區域網", "區域網路"), ("“", "「"), ("”", "」"),
]
STAGE_2 = [
    ("移動最佳化", "行動版最佳化"), ("移動 UI", "行動版 UI"), ("移動端", "行動版"),
    ("高階會員", "進階會員"), ("高階工具", "進階工具"), ("高階畫面", "進階畫面"),
    ("許可權", "權限"), ("前臺服務", "前景服務"), ("後臺", "背景"), ("手柄", "控制器"), ("鍵鼠友好", "鍵鼠友善"), ("問題反饋", "問題回報"),
    ("觸屏", "觸控"), ("文本", "文字"), ("只讀", "唯讀"), ("唯讀取", "只讀取"), ("直鏈", "直連"), ("友鏈", "友站連結"), ("兜底", "備援"),
    ("併為它", "並為它"), ("沒有專案", "沒有項目"), ("介面專案", "介面項目"), ("詳細專案", "詳細項目"),
]
STAGE_2_EXACT = {"高階": "進階"}
# Launch profiles: plain 設定 collides with Settings, so name them 設定檔.
NAME_OVERRIDES = {
    "create_launch_profile": "新增啟動設定檔",
    "launch_profile_name_hint": "設定檔名稱",
    "launch_profile_selected_format": "設定檔：%1$s",
}
STAGE_3 = [("一個設定會選擇", "一個啟動設定檔會選擇"), ("全域性", "全域"), ("例項", "實例"), ("新建", "新增"), ("不能為空", "不能空白"), ("保底", "備援"), ("引數", "參數")]

FORMAT_TOKENS = re.compile(r'%[0-9$]*[sdf]|\\n|\\"|&[a-z]+;')


def convert_text(value):
    for a, b in STAGE_1:
        value = value.replace(a, b)
    for a, b in STAGE_2:
        value = value.replace(a, b)
    value = STAGE_2_EXACT.get(value, value)
    for a, b in STAGE_3:
        value = value.replace(a, b)
    return value


def convert_file(name):
    raw = subprocess.run(["opencc", "-c", "s2twp.json", "-i", os.path.join(SRC, name)],
                         check=True, capture_output=True, text=True).stdout
    out = re.sub(r">([^<]*)<", lambda m: ">" + convert_text(m.group(1)) + "<", raw)
    for key, value in NAME_OVERRIDES.items():
        out = re.sub(rf'(<string name="{key}">)[^<]*(</string>)', lambda m: m.group(1) + value + m.group(2), out)
    return out


def check_parity(name, text):
    src = open(os.path.join(SRC, name), encoding="utf-8").read()
    xml.dom.minidom.parseString(text.encode("utf-8"))
    names = lambda s: re.findall(r'name="([^"]+)"', s)
    if names(src) != names(text):
        raise SystemExit(f"{name}: resource names differ from values-zh")
    if sorted(FORMAT_TOKENS.findall(src)) != sorted(FORMAT_TOKENS.findall(text)):
        raise SystemExit(f"{name}: format specifiers/escapes differ from values-zh")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = {name: convert_file(name) for name in FILES}
    outputs["godot_project_name_string.xml"] = APP_NAME
    for name in FILES:
        check_parity(name, outputs[name])
    stale = []
    for name, text in outputs.items():
        path = os.path.join(DST, name)
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if current != text:
            stale.append(name)
            if not args.check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
    extra = sorted(set(map(os.path.basename, glob.glob(os.path.join(SRC, "strings_*.xml")))) - set(FILES))
    if extra:
        print("values-zh has files this script does not convert yet: " + ", ".join(extra), file=sys.stderr)
    if args.check and (stale or extra):
        print("stale: " + ", ".join(stale or ["-"]), file=sys.stderr)
        sys.exit(1)
    print(("would update: " if args.check else "updated: ") + (", ".join(stale) if stale else "nothing"))


if __name__ == "__main__":
    main()
