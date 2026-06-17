import os
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_LIST_ID = os.environ["SLACK_LIST_ID"]

headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json; charset=utf-8",
}


def slack_api(method: str, payload: dict) -> dict:
    response = requests.post(
        f"https://slack.com/api/{method}",
        headers=headers,
        json=payload,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Slack API error: {data.get('error')}"
        )

    return data


# リストから1行取得する
items_data = slack_api(
    "slackLists.items.list",
    {
        "list_id": SLACK_LIST_ID,
        "limit": 1,
        "archived": False,
    },
)

items = items_data.get("items", [])

if not items:
    raise SystemExit(
        "リストに行がありません。テスト行を1行追加してください。"
    )

item_id = items[0]["id"]

# 行の詳細とリストスキーマを取得する
info_data = slack_api(
    "slackLists.items.info",
    {
        "list_id": SLACK_LIST_ID,
        "id": item_id,
    },
)

schema = (
    info_data
    .get("list", {})
    .get("list_metadata", {})
    .get("schema", [])
)

print("---- Slack List Column IDs ----")

for column in schema:
    print(
        f"{column.get('name')}: "
        f"{column.get('id')} "
        f"(type={column.get('type')}, key={column.get('key')})"
    )
