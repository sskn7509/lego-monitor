"""
LEGO「まもなく廃番」セール商品監視スクリプト
------------------------------------------
- 指定ページ内の商品リンクを取得
- 前回実行時の一覧(state.json)と比較
- 新しく増えた商品があればntfyに通知
- 最後に今回の一覧をstate.jsonに保存
"""

import os
import json
import requests
from bs4 import BeautifulSoup

# 監視対象URL(LEGO公式 セール×まもなく廃番フィルター)
URL = (
    "https://www.lego.com/ja-jp/categories/sales-and-deals"
    "?filters.i0.key=variants.attributes.flags.key"
    "&filters.i0.values.i0=retiringSoon"
)

STATE_FILE = "state.json"

# ntfyのTopic
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")


def fetch_products():
    """ページを取得し、商品リンクと商品名の辞書を返す"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    products = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/ja-jp/product/" in href:
            name = a.get_text(strip=True)

            if name:
                # クエリパラメータを除いてキーを正規化
                key = href.split("?")[0]
                products[key] = name

    return products


def load_previous_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {}


def save_state(products):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def send_ntfy_message(text):
    """ntfyに通知を送信する"""

    if not NTFY_TOPIC:
        print("NTFY_TOPICが未設定のため、通知をスキップしました。")
        return

    resp = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=text[:4000].encode("utf-8"),
        headers={
            "Title": "LEGO まもなく廃番セール商品",
            "Priority": "high",
        },
        timeout=30,
    )

    if resp.status_code >= 400:
        print(f"ntfy通知の送信に失敗しました: {resp.status_code} {resp.text}")
    else:
        print("ntfyに通知を送信しました。")


def main():
    current = fetch_products()

    if not current:
        print(
            "警告: 商品を1件も取得できませんでした。"
            "ページ構造が変わった可能性があります。"
        )
        return

    previous = load_previous_state()

    new_items = {
        href: name
        for href, name in current.items()
        if href not in previous
    }

    if new_items:
        lines = [
            "【LEGO】まもなく廃番のセール商品が追加されました！"
        ]

        for href, name in new_items.items():
            lines.append(f"・{name}\n{href}")

        send_ntfy_message("\n".join(lines))

    else:
        print("新規商品はありませんでした。")

    save_state(current)


if __name__ == "__main__":
    main()
