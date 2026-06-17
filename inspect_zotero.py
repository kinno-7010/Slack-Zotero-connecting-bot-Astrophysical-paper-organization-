import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.zotero.org"

api_key = os.environ.get("ZOTERO_API_KEY", "").strip()
target_path = os.environ.get("ZOTERO_TARGET_PATH", "").strip()

missing = []

if not api_key:
    missing.append("ZOTERO_API_KEY")

if not target_path:
    missing.append("ZOTERO_TARGET_PATH")

if missing:
    raise SystemExit(
        "[ERROR] Missing required environment variables in .env: "
        + ", ".join(missing)
    )

headers = {
    "Zotero-API-Key": api_key,
    "Zotero-API-Version": "3",
}


def get_response(url: str, params: dict | None = None) -> requests.Response:
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise SystemExit(
            f"[ERROR] Zotero API connection failed: {exc}"
        ) from exc

    if not response.ok:
        print(f"[ERROR] HTTP {response.status_code}")
        print(response.text[:2000])
        raise SystemExit(1)

    return response


# --------------------------------
# 1. API keyとUser IDを確認
# --------------------------------
key_response = get_response(f"{API_BASE}/keys/current")
key_info = key_response.json()

user_id = key_info.get("userID")
username = key_info.get("username", "")
user_access = key_info.get("access", {}).get("user", {})

library_access = bool(user_access.get("library"))
write_access = bool(user_access.get("write"))

print("---- Zotero API key ----")
print(f"target path    : {target_path}")
print(f"username       : {username}")
print(f"userID         : {user_id}")
print(f"library access : {library_access}")
print(f"write access   : {write_access}")

if not user_id:
    raise SystemExit("[ERROR] Zotero userID could not be obtained.")

if not library_access:
    raise SystemExit(
        "[ERROR] The API key does not have Personal Library access."
    )

if not write_access:
    raise SystemExit(
        "[ERROR] The API key does not have write access."
    )


# --------------------------------
# 2. 全collectionを取得
# --------------------------------
collections_raw = []
start = 0
limit = 100

while True:
    response = get_response(
        f"{API_BASE}/users/{user_id}/collections",
        params={
            "limit": limit,
            "start": start,
            "format": "json",
        },
    )

    batch = response.json()

    if not isinstance(batch, list):
        raise SystemExit(
            "[ERROR] Unexpected collections response."
        )

    collections_raw.extend(batch)

    try:
        total = int(
            response.headers.get(
                "Total-Results",
                len(collections_raw),
            )
        )
    except ValueError:
        total = len(collections_raw)

    if not batch or len(collections_raw) >= total:
        break

    start += len(batch)


# --------------------------------
# 3. collection treeを組み立てる
# --------------------------------
collections = {}

for collection in collections_raw:
    data = collection.get("data", {})

    collection_key = collection.get("key") or data.get("key")
    name = str(data.get("name", "")).strip()
    parent = data.get("parentCollection")

    if parent is False:
        parent = None

    if collection_key:
        collections[collection_key] = {
            "name": name,
            "parent": parent,
        }


def get_full_path(collection_key: str) -> str:
    names = []
    current_key = collection_key
    visited = set()

    while current_key:
        if current_key in visited:
            names.append("[CYCLE]")
            break

        visited.add(current_key)

        current = collections.get(current_key)
        if not current:
            names.append(f"[UNKNOWN:{current_key}]")
            break

        names.append(current["name"])
        current_key = current["parent"]

    return "/".join(reversed(names))


paths = {
    collection_key: get_full_path(collection_key)
    for collection_key in collections
}

print("\n---- Zotero collections ----")

for collection_key, path in sorted(
    paths.items(),
    key=lambda pair: pair[1],
):
    print(f"{path} -> {collection_key}")


# --------------------------------
# 4. 対象collectionを検索
# --------------------------------
matches = [
    (collection_key, path)
    for collection_key, path in paths.items()
    if path == target_path
]

print("\n---- Target collection ----")

if len(matches) == 1:
    collection_key, path = matches[0]

    print(f"path           : {path}")
    print(f"collection key : {collection_key}")

    print("\nAdd these lines to .env:")
    print(f"ZOTERO_USER_ID={user_id}")
    print(f"ZOTERO_COLLECTION_KEY={collection_key}")

elif len(matches) == 0:
    print(f"[ERROR] Collection not found: {target_path}")
    print(
        "Check the collection names printed above, "
        "including spaces and character variants."
    )
    sys.exit(1)

else:
    print(f"[ERROR] Multiple collections matched: {target_path}")

    for collection_key, path in matches:
        print(f"{path} -> {collection_key}")

    sys.exit(1)
