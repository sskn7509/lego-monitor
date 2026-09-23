import requests

TARGET_URL = (
    "https://www.lego.com/ja-jp/categories/sales-and-deals"
    "?filters.i0.key=variants.attributes.flags.key"
    "&filters.i0.values.i0=retiringSoon"
)

JINA_URL = "https://r.jina.ai/"


def main():
    print("Jina Reader経由でLEGOページを取得します")

    response = requests.post(
        JINA_URL,
        data={
            "url": TARGET_URL
        },
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

    print()
    print("取得文字数:", len(text))

    print()
    print("===== LEGOページ取得結果（先頭15000文字） =====")
    print(text[:15000])


if __name__ == "__main__":
    main()
