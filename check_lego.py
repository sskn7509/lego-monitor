"""
LEGO「まもなく廃番」セール商品監視

GitHub Actions
    ↓
Jina Reader
    ↓
LEGO公式ページ
    ↓
商品情報を解析
    ↓
state.jsonと比較
    ↓
新商品・価格変更をntfyで通知
"""

import os
import json
import re
import requests


# ============================================================
# 設定
# ============================================================

LEGO_URL = (
    "https://www.lego.com/ja-jp/categories/sales-and-deals"
    "?filters.i0.key=variants.attributes.flags.key"
    "&filters.i0.values.i0=retiringSoon"
)

JINA_URL = "https://r.jina.ai/"

STATE_FILE = "state.json"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")


# ============================================================
# Jina経由でLEGOページを取得
# ============================================================

def fetch_page():
    print("Jina Reader経由でLEGOページを取得します")

    response = requests.post(
        JINA_URL,
        data={"url": LEGO_URL},
        headers={
            "x-engine": "browser",
            "x-no-cache": "true",
            "x-timeout": "30",
        },
        timeout=60,
    )

    print("Jina status:", response.status_code)

    response.raise_for_status()

    text = response.text

    print("取得文字数:", len(text))

    return text


# ============================================================
# 商品情報を解析
# ============================================================

def parse_products(text):
    """
    Jinaが返したMarkdownから
    「まもなく廃番」の商品情報を抽出する
    """

    products = {}

    # 商品見出しから次の商品見出しまでを1ブロックとして取得
    pattern = re.compile(
        r"###\s+\[([^\]]+)\]\((https://www\.lego\.com/ja-jp/product/[^\)]+)\)"
        r"(.*?)(?=\n###\s+|\Z)",
        re.DOTALL,
    )

    matches = pattern.findall(text)

    print("商品候補:", len(matches))

    for name, url, block in matches:

        # 念のためURLのクエリパラメータを除去
        url = url.split("?")[0]

        # 「まもなく廃番」がある商品だけ対象
        if "まもなく廃番" not in block:
            continue

        # 価格を取得
        # 例:
        # ¥16,280¥11,396- 30%
        price_match = re.search(
            r"¥\s*([\d,]+)\s*¥\s*([\d,]+)\s*-\s*(\d+)\s*%",
            block,
        )

        if price_match:
            regular_price = int(price_match.group(1).replace(",", ""))
            sale_price = int(price_match.group(2).replace(",", ""))
            discount = int(price_match.group(3))
        else:
            regular_price = None
            sale_price = None
            discount = None

        products[url] = {
            "name": name.strip(),
            "url": url,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "discount": discount,
        }

    print("まもなく廃番商品:", len(products))

    for product in products.values():
        print(
            f"- {product['name']} / "
            f"{product['regular_price']}円 → "
            f"{product['sale_price']}円 / "
            f"{product['discount']}%"
        )

    return products


# ============================================================
# state.json読み込み
# ============================================================

def load_previous_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("state.jsonの読み込みに失敗しました:", e)
        return {}


# ============================================================
# state.json保存
# ============================================================

def save_state(products):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            products,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# ntfy通知
# ============================================================

def send_ntfy_message(title, message):
    if not NTFY_TOPIC:
        print("NTFY_TOPICが設定されていないため、通知をスキップします。")
        return

    url = f"https://ntfy.sh/{NTFY_TOPIC}"

    response = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": "LEGO",
            "Priority": "high",
            "Tags": "lego,moneybag",
        },
        timeout=30,
    )

    print("ntfy status:", response.status_code)

    if response.status_code >= 400:
        print("ntfy通知に失敗:", response.text)
        response.raise_for_status()

    print("ntfy通知を送信しました。")


# ============================================================
# 商品情報を通知用テキストにする
# ============================================================

def format_product(product):
    name = product["name"]
    url = product["url"]

    regular = product["regular_price"]
    sale = product["sale_price"]
    discount = product["discount"]

    if regular is not None and sale is not None:
        price_text = (
            f"通常価格：{regular:,}円\n"
            f"セール価格：{sale:,}円\n"
            f"割引率：{discount}%"
        )
    else:
        price_text = "価格情報を取得できませんでした"

    return (
        f"{name}\n"
        f"{price_text}\n"
        f"{url}"
    )


# ============================================================
# メイン処理
# ============================================================

def main():

    # --------------------------------------------------------
    # LEGOページ取得
    # --------------------------------------------------------

    text = fetch_page()

    # --------------------------------------------------------
    # 商品解析
    # --------------------------------------------------------

    current = parse_products(text)

    if not current:
        print(
            "警告: まもなく廃番の商品を1件も取得できませんでした。"
        )
        print(
            "ページ構造が変更された可能性があるため、"
            "state.jsonは更新しません。"
        )
        return

    # --------------------------------------------------------
    # 前回データ
    # --------------------------------------------------------

    previous = load_previous_state()

    # --------------------------------------------------------
    # 新商品
    # --------------------------------------------------------

    new_items = {}

    for url, product in current.items():

        if url not in previous:
            new_items[url] = product

    # --------------------------------------------------------
    # 価格変更
    # --------------------------------------------------------

    price_changes = {}

    for url, product in current.items():

        if url not in previous:
            continue

        old = previous[url]

        # 古いstate.jsonが
        # 「URL: 商品名」という形式だった場合への対応
        if not isinstance(old, dict):
            continue

        old_sale_price = old.get("sale_price")
        new_sale_price = product.get("sale_price")

        old_discount = old.get("discount")
        new_discount = product.get("discount")

        if (
            old_sale_price != new_sale_price
            or old_discount != new_discount
        ):
            price_changes[url] = {
                "old": old,
                "new": product,
            }

    # --------------------------------------------------------
    # 通知
    # --------------------------------------------------------

    if new_items:

        lines = [
            "【LEGO】まもなく廃番のセール商品が追加！",
            "",
        ]

        for product in new_items.values():
            lines.append(format_product(product))
            lines.append("")
            lines.append("--------------------")
            lines.append("")

        send_ntfy_message(
            "LEGO まもなく廃番セール商品",
            "\n".join(lines),
        )

        print(f"新商品 {len(new_items)}件を通知しました。")

    else:
        print("新商品はありませんでした。")

    # --------------------------------------------------------
    # 価格変更通知
    # --------------------------------------------------------

    if price_changes:

        lines = [
            "【LEGO】セール価格が変更されました！",
            "",
        ]

        for change in price_changes.values():

            old = change["old"]
            new = change["new"]

            lines.append(new["name"])

            if old.get("sale_price") is not None:
                lines.append(
                    f"変更前：{old['sale_price']:,}円 "
                    f"({old.get('discount')}% OFF)"
                )

            if new.get("sale_price") is not None:
                lines.append(
                    f"変更後：{new['sale_price']:,}円 "
                    f"({new.get('discount')}% OFF)"
                )

            lines.append(new["url"])
            lines.append("")
            lines.append("--------------------")
            lines.append("")

        send_ntfy_message(
            "LEGO セール価格変更",
            "\n".join(lines),
        )

        print(
            f"価格変更 {len(price_changes)}件を通知しました。"
        )

    # --------------------------------------------------------
    # state.json更新
    # --------------------------------------------------------

    save_state(current)

    print(
        f"state.jsonを更新しました。"
        f"現在の商品数: {len(current)}"
    )


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()
