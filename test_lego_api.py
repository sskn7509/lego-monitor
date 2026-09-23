import json
import uuid
import requests


BASE_URL = "https://www.lego.com"

LOGIN_URL = f"{BASE_URL}/api/graphql/Login"
SEARCH_URL = f"{BASE_URL}/api/graphql/SearchQuery"


LOGIN_QUERY = """
mutation Login($forceCtLogin: Boolean) {
  login(forceCtLogin: $forceCtLogin)
}
"""


SEARCH_QUERY = """
query SearchQuery(
  $q: String!,
  $page: Int,
  $perPage: Int,
  $filters: [Filter!],
  $sort: SortInput,
  $isPaginated: Boolean!,
  $visibility: ProductVisibility,
  $scoreFactorAttribute: String,
  $scoreFactorModifier: String,
  $scoreFactorMultiplier: String,
  $scoreFactorBoostMode: String,
  $hideTargetedSections: Boolean
) {
  search(query: $q, visibility: $visibility) {
    ... on ProductSearchResults {
      productResult(
        page: $page,
        perPage: $perPage,
        filters: $filters,
        sort: $sort,
        scoring: {
          scoreFactorAttribute: $scoreFactorAttribute,
          scoreFactorModifier: $scoreFactorModifier,
          scoreFactorMultiplier: $scoreFactorMultiplier,
          scoreFactorBoostMode: $scoreFactorBoostMode
        }
      ) @include(if: $isPaginated) {
        count
        total
        results {
          id
          productCode
          name
          slug

          ... on Product {
            __typename

            ... on ReadOnlyProduct {
              readOnlyVariant {
                id
                sku
                attributes {
                  featuredFlags {
                    key
                    label
                  }
                }
              }
            }

            ... on SingleVariantProduct {
              variant {
                id
                sku
                salePercentage

                attributes {
                  availabilityStatus
                  availabilityText
                  onSale
                  canAddToBag
                  featuredFlags {
                    key
                    label
                  }
                }

                price {
                  formattedAmount
                  centAmount
                  currencyCode
                  formattedValue
                }

                listPrice {
                  formattedAmount
                  centAmount
                }
              }
            }

            ... on MultiVariantProduct {
              variants {
                id
                sku
                salePercentage

                attributes {
                  availabilityStatus
                  availabilityText
                  onSale
                  canAddToBag
                  featuredFlags {
                    key
                    label
                  }
                }

                price {
                  formattedAmount
                  centAmount
                  currencyCode
                  formattedValue
                }

                listPrice {
                  formattedAmount
                  centAmount
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def get_auth_token():
    payload = {
        "operationName": "Login",
        "variables": {
            "forceCtLogin": False
        },
        "query": LOGIN_QUERY
    }

    headers = {
        "Content-Type": "application/json",
        "x-locale": "ja-JP",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.post(
        LOGIN_URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    print("Login status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    token = data["data"]["login"]

    if not token:
        raise RuntimeError("ログイントークンを取得できませんでした。")

    return token


def search_products(token):
    payload = {
        "operationName": "SearchQuery",
        "variables": {
            "q": "",
            "page": 1,
            "perPage": 20,

            "filters": [
                {
                    "key": "variants.attributes.flags.key",
                    "values": ["retiringSoon"]
                }
            ],

            "sort": {
                "key": "FEATURED",
                "direction": "DESC"
            },

            "isPaginated": True,
            "visibility": None,

            "scoreFactorAttribute": None,
            "scoreFactorModifier": None,
            "scoreFactorMultiplier": None,
            "scoreFactorBoostMode": None,

            "hideTargetedSections": True
        },
        "query": SEARCH_QUERY
    }

    headers = {
        "Content-Type": "application/json",
        "x-locale": "ja-JP",
        "x-lego-request-id": str(uuid.uuid4()),
        "authorization": token,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.post(
        SEARCH_URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    print("Search status:", response.status_code)

    response.raise_for_status()

    return response.json()


def main():
    print("LEGO GraphQL API テスト開始")

    token = get_auth_token()

    print("ログイントークン取得：OK")

    result = search_products(token)

    print("商品検索：OK")

    print()
    print("===== APIレスポンスの先頭 =====")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:10000])


if __name__ == "__main__":
    main()
