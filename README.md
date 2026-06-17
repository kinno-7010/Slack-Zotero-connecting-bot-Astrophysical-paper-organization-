# Paper Inbox Bot

Slackの専用チャンネルに論文リンクを投稿すると、論文情報を自動取得して登録するPython Botです。

利用するSlackプランに応じて、次の2方式から選択します。

1. **Slack Listsを利用できる場合**：Slackの「読みたい論文リスト」とZoteroの指定コレクションへ登録
2. **Slack Listsを利用できない場合（Freeプランなど）**：Slackリストを介さず、Zoteroの指定コレクションへ直接登録

また、Slack Listsを利用する方式では、すでにSlackリストに蓄積されている論文をZoteroへ一括同期するスクリプトも利用できます。

---

## 主な機能

- SlackのプライベートチャンネルをSocket Modeで監視
- DOI、arXiv、ADS、出版社ページなどのURLを受け付け
- 入力を `https://doi.org/<DOI>` 形式へ正規化
- Crossref、arXiv API、論文ページのメタデータから書誌情報を取得
- **Slack Lists利用方式のみ**：Slackリストへ以下を登録
  - Citation
  - Title
  - DOI/link
  - Memo
  - Message
- **両方式共通**：Zoteroへ書誌情報を登録
- **Slack Listsを利用できない場合**：Slackリストを介さずZoteroへ直接登録
- Zotero内のDOI重複を確認
- 既存アイテムが指定コレクションにない場合は、コレクションだけ追加
- Slackリストに登録済みでも、Zoteroに未登録ならZoteroへ追加
- 登録結果を元メッセージへの返信として投稿し、チャンネル本体にも表示
- systemdによるバックグラウンド常駐
- 既存Slackリスト全件のZotero一括同期

---
## 目次


---

## ファイル構成

paper_inbox_bot

├── paper_inbox_bot_zotero.py        # Slackリスト + Zoteroへ登録（[Chapter 7](https://github.com/kinno-7010/Slack-Zotero-connecting-bot-Astrophysical-paper-organization-#7-%E6%89%8B%E5%8B%95%E8%B5%B7%E5%8B%95%E3%81%A8%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D)）

├── paper_inbox_bot_zotero_direct.py # Slackリストを介さずZoteroへ直接登録（[Chapter 7](https://github.com/kinno-7010/Slack-Zotero-connecting-bot-Astrophysical-paper-organization-#7-%E6%89%8B%E5%8B%95%E8%B5%B7%E5%8B%95%E3%81%A8%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D)）

├── get_slack_column_ids.py          # SlackリストのColumnのIDを取得（[Chapter 5.4](https://github.com/kinno-7010/Slack-Zotero-connecting-bot-Astrophysical-paper-organization-#54-column-id%E3%82%92%E5%8F%96%E5%BE%97%E3%81%99%E3%82%8B)）

├── inspect_zotero.py                # ZoteroにあるフォルダのIDを取得（[Chapter 6.2](https://github.com/kinno-7010/Slack-Zotero-connecting-bot-Astrophysical-paper-organization-#62-zotero-user-id%E3%81%A8collection-key%E3%82%92%E5%8F%96%E5%BE%97%E3%81%99%E3%82%8B)）

├── sync_slack_list_to_zotero.py     # すでにリストに登録されている論文をZoteroに登録（[Chapter 15](https://github.com/kinno-7010/Slack-Zotero-connecting-bot-Astrophysical-paper-organization-#15-%E6%97%A2%E5%AD%98slack%E3%83%AA%E3%82%B9%E3%83%88%E3%82%92zotero%E3%81%B8%E4%B8%80%E6%8B%AC%E5%90%8C%E6%9C%9F%E3%81%99%E3%82%8B)）

├── requirements.txt                 # Python依存パッケージ

├── .env                             # トークン・ID、パス。Gitへ登録しない

└── README.md


- Slack Listsを利用できる場合：**`paper_inbox_bot_zotero.py`**
- Slack Listsを利用できない場合：**`paper_inbox_bot_zotero_direct.py`**

---

## 処理の流れ

### Slack Listsを利用できる場合

```text
Slackの専用チャンネルへ論文リンクを投稿
        ↓
DOIまたはarXiv IDを抽出
        ↓
DOIがURL中に見えない場合は論文ページを取得
        ↓
ページのmetaタグ・HTML・タイトルを確認
        ↓
CrossrefまたはarXiv APIから書誌情報を取得
        ↓
https://doi.org/<DOI> へ正規化
        ↓
Zotero内をDOIで重複確認
        ↓
Slackリスト内をDOI URLで重複確認
        ↓
必要な登録・コレクション追加を実行
        ↓
Slackへ結果を返信し、チャンネル本体にも表示
```

### Slack Listsを利用できない場合

```text
Slackの専用チャンネルへ論文リンクを投稿
        ↓
DOIまたはarXiv IDを抽出
        ↓
DOIがURL中に見えない場合は論文ページを取得
        ↓
ページのmetaタグ・HTML・タイトルを確認
        ↓
CrossrefまたはarXiv APIから書誌情報を取得
        ↓
https://doi.org/<DOI> へ正規化
        ↓
Zotero内をDOIで重複確認
        ↓
Zoteroへの新規登録または指定コレクション追加
        ↓
Slackへ結果を返信し、チャンネル本体にも表示
```

---

# 1. 必要環境

## ソフトウェア

- Python 3.10以上
- Slackワークスペース
  - Slack Listsを利用する方式：Slack Listsを利用可能なプランが必要
  - Zoteroへ直接登録する方式：Slack Listsは不要で、Freeプランでも利用可能
- Zoteroアカウント
- WSLを使用する場合
  - Ubuntu 22.04 / 24.04など
  - systemd対応WSL

## Pythonパッケージ

```text
slack-bolt
python-dotenv
requests
beautifulsoup4
```

`requirements.txt` の例：

```text
slack-bolt>=1.21
python-dotenv>=1.0
requests>=2.31
beautifulsoup4>=4.12
```

---

# 2. Python環境の準備

作業ディレクトリを作成します。

```bash
mkdir -p ~/Research_code/other_things/paper_inbox_bot
cd ~/Research_code/other_things/paper_inbox_bot
```

仮想環境を作成します。

```bash
python3 -m venv ~/Research_code/wsl-venv
source ~/Research_code/wsl-venv/bin/activate
```

依存パッケージをインストールします。

```bash
pip install -U pip
pip install -r requirements.txt
```

`requirements.txt` がない場合：

```bash
pip install slack-bolt python-dotenv requests beautifulsoup4
```

---
# 3. `.env` の設定

プロジェクトディレクトリに `.env` を作成します。
値は後のセクションで記入していきます。

```bash
nano .env
```

### Slack Listsを利用できる場合

```env
# Slack App
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Slack channel and list
TARGET_CHANNEL_ID=...
SLACK_LIST_ID=...

# Slack List column IDs
SLACK_COL_CITATION=...
SLACK_COL_TITLE=...
SLACK_COL_DOI_LINK=...
SLACK_COL_MEMO=...
SLACK_COL_MESSAGE=...

# Metadata service contact
CONTACT_EMAIL=<your-address@example.com>

# Zotero
ZOTERO_API_KEY=...
ZOTERO_USER_ID=...
ZOTERO_COLLECTION_KEY=...
```

### Slack Listsを利用できない場合

`paper_inbox_bot_zotero_direct.py` では、Slack List関連の変数は不要です。

```env
# Slack App
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
TARGET_CHANNEL_ID=C0123456789

# Metadata service contact
CONTACT_EMAIL=your-address@example.com

# Zotero
ZOTERO_API_KEY=your-zotero-api-key
ZOTERO_USER_ID=12345678
ZOTERO_COLLECTION_KEY=ABCDEFGH
```

---

# 4. Slack側の設定

## 4.1 Slack Appを作成する

Slack App管理画面を開きます。

- <https://api.slack.com/apps>

手順：

1. `Create an App`
2. `From scratch`
3. App名を入力
   - 例：`Paper Inbox Bot`
4. 使用するSlackワークスペースを選択
5. `Create App`

## 4.2 Socket Modeを有効にする

Slack App設定画面で：

1. `Socket Mode`
2. `Enable Socket Mode` をON
3. Token Nameを入力
   - 例：`paper-inbox-socket`
4. Scopeとして `connections:write` を追加
5. App-Level Tokenを生成

生成されるトークンは次の形式です。

```text
xapp-...
```

この値を `.env` の `SLACK_APP_TOKEN` に保存します。

## 4.3 Bot Token Scopesを設定する

`OAuth & Permissions` → `Bot Token Scopes` へ、次を追加します。

| Scope | 用途 |
|---|---|
| `chat:write` | 登録結果をSlackへ投稿 |
| `groups:history` | プライベートチャンネルの投稿を読む |
| `lists:read` | Slackリストの行・列を読む（Slack Lists利用方式のみ） |
| `lists:write` | Slackリストへ行を追加（Slack Lists利用方式のみ） |

チャンネル名からIDをAPI検索したい場合は、必要に応じて次も追加します。

```text
groups:read
```

Scopeを追加したら、必ず次を実行します。

```text
Reinstall to Workspace
```

再インストール後、`Bot User OAuth Token` を取得します。

```text
xoxb-...
```

この値を `.env` の `SLACK_BOT_TOKEN` に保存します。

## 4.4 Event Subscriptionsを設定する

`Event Subscriptions` をONにし、`Subscribe to bot events` へ次を追加します。

```text
message.groups
```

これはプライベートチャンネルのメッセージを受信するためのイベントです。

公開チャンネルを監視する構成へ変更する場合は、イベントとScopeも公開チャンネル用へ変更する必要があります。

## 4.5 Botをチャンネルへ招待する

監視対象のプライベートチャンネルで実行します。

```text
/invite @Paper Inbox Bot
```

Botは参加していないプライベートチャンネルの投稿を読めません。

---

# 5. Slackリストの準備

このセクションは、**Slack Listsを利用できる場合のみ**必要です。

Slack Listsを利用できない場合は、`paper_inbox_bot_zotero_direct.py` を使用し、セクション5を省略してセクション6へ進んでください。その場合、Slack Appの `lists:read` / `lists:write` Scope、List ID、Column IDも不要です。

## 5.1 必要な列

Slackリストには、次の5列を作成してください。

| 列名 | 列の型 | 内容 |
|---|---|---|
| Citation | Text | `Sahade, A., et al. 2026, ApJ, 1003, 154` 形式 |
| Title | Text | 論文タイトル |
| DOI/link | Link | 正規化済みDOI URL |
| Memo | Text | Slack投稿の `Memo:` または `メモ:` 以降 |
| Message | Message | 元のSlack投稿へのリンク |

`Citation` をprimary columnにしても問題ありません。

## 5.2 リストを監視チャンネルへ共有する

Slackリストが別のチャンネルにある場合でも使用できます。ただし、Botからリストが見えるようにする必要があります。

対象リストを開き：

1. `Share / 共有`
2. 監視対象チャンネルを追加
3. 権限を `Can edit / 編集可` に設定

これを行わない場合、APIで次のエラーになることがあります。

```text
list_not_found
```

## 5.3 List IDを取得する

SlackリストのURL例：

```text
https://workspace.slack.com/lists/TEAM_ID/F0123456789?view_id=View0123456789
```

この場合：

```text
SLACK_LIST_ID=F0123456789
```

## 5.4 Column IDを取得する

Slack Lists APIでは列名ではなく、内部の `column_id` を使用します。

`get_slack_column_ids.py` を実行し、IDを取得します。取得したIDは以下の.envに入れます。

必要な設定は次の形式です。

```env
SLACK_COL_CITATION=Col...
SLACK_COL_TITLE=Col...
SLACK_COL_DOI_LINK=Col...
SLACK_COL_MEMO=Col...
SLACK_COL_MESSAGE=Col...
```

列構成を変更した場合は、必ずこれらのIDも取り直してください。

## 5.5 チャンネルIDを取得する

監視対象チャンネル内のメッセージで `リンクをコピー` します。

```text
https://workspace.slack.com/archives/C0123456789/p1234567890000000
```

`archives/` と次の `/` の間がチャンネルIDです。

```text
TARGET_CHANNEL_ID=C0123456789
```

Botの受信ログに表示される `channel` の値を使用しても構いません。

---

# 6. Zotero側の設定

## 6.1 API Keyを作成する

<https://www.zotero.org/> を開き、ログイン→Security→Applications→Create new private keyでAPI Keyを作成。

推奨設定：

```text
Key Description: Paper Inbox Bot
Personal Library: Read/Write
File access: 不要
Group access: 不要
```

API Keyは次へ保存します。

```env
ZOTERO_API_KEY=...
```

*API KeyをREADME、Git、Slack、公開リポジトリへ貼らないでください。*

## 6.2 Zotero User IDとCollection Keyを取得する

- `.env` 内の`TARGET_PATH`を指定し、実行します。

対象コレクションの例：

```text
マイ・ライブラリ
└ 読みたい論文
   └ レビュー論文
```
→　`TARGET_PATH=読みたい論文/レビュー論文`と.envに記入

- `inspect_zotero.py` を実行

出力例
```text
---- Zotero API key ----
username       : ...
userID         : 12345678
library access : True
write access   : True

---- Target collection ----
path           : 読みたい論文/レビュー論文
collection key : ABCD1234

Add these lines to .env:
ZOTERO_USER_ID=12345678
ZOTERO_COLLECTION_KEY=ABCD1234
```

- 出力された `userID` と`Collection Key`を設定します。

```env
ZOTERO_USER_ID=12345678
ZOTERO_COLLECTION_KEY=ABCD1234
```

親コレクションのkeyではなく、実際にアイテムを入れたい最下層のkeyを使用してください。


---



## コメントの書き方

`.env` 内のメモは、行頭に `#` を付けます。

```env
# Zoteroの設定
ZOTERO_USER_ID=12345678
```

次のような説明文をそのまま書くと、`python-dotenv` の解析エラーになります。

```text
これはZoteroの設定です
```

正しくは：

```env
# これはZoteroの設定です
```

## セキュリティ設定

```bash
chmod 600 .env
```

`.gitignore`：

```gitignore
.env
__pycache__/
*.pyc
*.log
*.db
```

---

# 7. 手動起動と動作確認

## 7.1 構文確認

Slack Listsを利用できる場合：

```bash
python3 -m py_compile paper_inbox_bot_zotero.py
```

Slack Listsを利用できない場合：

```bash
python3 -m py_compile paper_inbox_bot_zotero_direct.py
```

何も表示されなければ構文上は正常です。

## 7.2 Botを起動する

Slack Listsを利用できる場合：

```bash
python3 paper_inbox_bot_zotero.py
```

Slack Listsを利用できない場合：

```bash
python3 paper_inbox_bot_zotero_direct.py
```

正常時：

```text
Starting Paper Inbox Bot with Socket Mode
A new session has been established
⚡️ Bolt app is running!
```

## 7.3 Slackへテスト投稿する

```text
https://doi.org/10.xxxx/xxxxx

Memo: この論文を読む目的
```

登録完了時には、利用方式に応じてSlackへ次のような結果が返ります。

Slack Listsを利用できる場合：

```text
✅ 論文登録処理が完了しました。
Citation: Author, A., et al. 2026, ApJ, 1000, 100
Title: Paper title
DOI: https://doi.org/10.xxxx/xxxxx
Slackリスト: 追加しました
Zotero: 新規登録しました
Metadata: crossref-doi
```

Slack Listsを利用できない場合：

```text
✅ Zotero登録処理が完了しました。
Citation: Author, A., et al. 2026, ApJ, 1000, 100
Title: Paper title
DOI: https://doi.org/10.xxxx/xxxxx
Zotero: 新規登録しました
Metadata: crossref-doi
```

返信は元メッセージのスレッドに投稿され、`reply_broadcast=True` によりチャンネル本体にも表示されます。

---

# 8. 対応する入力形式

次のような入力を処理できます。

## DOI URL

```text
https://doi.org/10.3847/1538-4357/ae6e39
```

## DOI文字列

```text
DOI 10.1086/52728
```

## NASA ADS link gateway

```text
https://ui.adsabs.harvard.edu/link_gateway/.../doi:10.3847/1538-4357/aa72e7
```

## 出版社ページ

```text
https://iopscience.iop.org/article/10.1086/374917/pdf
```

## arXiv URL

```text
https://arxiv.org/abs/2507.01580v1
```

## arXiv DOI

```text
https://doi.org/10.48550/arXiv.2605.23484
```

## Memo付き

```text
https://doi.org/10.xxxx/xxxxx

Memo: Type II burstの変調構造に関する参考文献
```

`Memo:` と `メモ:` の両方に対応しています。

---

# 9. DOI正規化とメタデータ取得

## DOI正規化

保存時は原則として次へ統一します。

```text
https://doi.org/<DOI>
```

arXiv URLの場合：

```text
https://arxiv.org/abs/2507.01580v1
```

は、次へ変換されます。

```text
https://doi.org/10.48550/arXiv.2507.01580
```

arXivのversion番号は保存用DOIでは除去されます。

## メタデータ取得順

1. メッセージ中のDOI
2. メッセージ中のarXiv ID
3. URLのリダイレクト先
4. HTML metaタグ
   - `citation_doi`
   - `dc.identifier`
   - `prism.doi`
   - `citation_title`
   - `og:title`
5. HTML本文中のDOI
6. ページタイトルによるCrossref検索

Crossrefのタイトル検索は、誤登録を防ぐため一致度が閾値未満の場合は登録しません。

現在の閾値：

```python
CROSSREF_TITLE_THRESHOLD = 0.82
```

---

## 9.1 新しい雑誌・出版社のリンクに対応させる

このBotのDOI処理は、特定の雑誌名ではなく、次の順番でDOIを探索します。

```text
投稿本文にDOIが含まれる
    ↓
URL内にDOIが含まれる
    ↓
URLを開き、HTMLのmetaタグからDOIを取得
    ↓
HTML本文からDOIを検索
    ↓
ページタイトルをCrossrefで検索
```

そのため、**多くの雑誌・出版社はコードを変更しなくても利用できます**。

### 変更不要なケース

次のいずれかに該当するURLは、通常そのまま処理できます。

1. URL中にDOIが含まれている

```text
https://example.com/article/10.1234/example.5678
https://example.com/doi/full/10.1234/example.5678
```

2. 論文ページのHTMLに一般的なDOI metaタグがある

```html
<meta name="citation_doi" content="10.1234/example.5678">
<meta name="dc.identifier" content="10.1234/example.5678">
<meta name="prism.doi" content="10.1234/example.5678">
```

3. DOIが取得できなくても、ページタイトルとCrossref上のタイトルが十分一致する

この場合、`fetch_page_metadata()` と `crossref_search_by_title()` によってDOIが推定されます。

### まず確認する方法

新しい出版社のURLを追加する前に、現在のコードで解決できるか確認します。

```bash
python3 - <<'PYTEST'
from paper_inbox_bot_zotero import resolve_paper

urls = [
    "https://追加したい論文URL",
]

for url in urls:
    result = resolve_paper(url)
    print("=" * 80)
    print("Input :", url)
    print("Result:", result)
PYTEST
```

次のように `ok: True`、`doi`、`title` が取得できていれば、コード変更は不要です。

```text
{
    'ok': True,
    'doi': '10.1234/example.5678',
    'doi_url': 'https://doi.org/10.1234/example.5678',
    'title': 'Example paper title',
    ...
}
```

---

### ケースA：出版社独自のDOI metaタグを追加する

URL内にDOIが見えず、出版社が独自のmetaタグを使用している場合は、`fetch_page_metadata()` 内のDOI候補へタグ名を追加します。

現在のコード：

```python
raw_doi = page_meta_content(
    soup,
    (
        "citation_doi",
        "dc.identifier",
        "prism.doi",
        "doi",
        "bepress_citation_doi",
    ),
)
```

例えば、対象ページのHTMLが次のようになっていたとします。

```html
<meta name="publisher_doi" content="10.1234/example.5678">
```

この場合は、次のように追加します。

```python
raw_doi = page_meta_content(
    soup,
    (
        "citation_doi",
        "dc.identifier",
        "prism.doi",
        "doi",
        "bepress_citation_doi",
        "publisher_doi",  # 追加
    ),
)
```

タグ名を調べるには、ブラウザで論文ページを開き、ページのソースまたは開発者ツールで次を検索します。

```text
doi
citation_doi
dc.identifier
prism.doi
```

実際のAPIキーや認証情報を、コードやREADMEへ書き込まないでください。

---

### ケースB：出版社独自のタイトルmetaタグを追加する

DOIがページ内にない場合、BotはページタイトルをCrossref検索へ使用します。出版社が独自のタイトルmetaタグを使っている場合は、同じ `fetch_page_metadata()` 内のタイトル候補へ追加します。

現在のコード：

```python
title = page_meta_content(
    soup,
    (
        "citation_title",
        "dc.title",
        "og:title",
        "twitter:title",
    ),
)
```

例えば、HTMLが次の場合：

```html
<meta name="publisher_article_title" content="Example paper title">
```

次のように追加します。

```python
title = page_meta_content(
    soup,
    (
        "citation_title",
        "dc.title",
        "og:title",
        "twitter:title",
        "publisher_article_title",  # 追加
    ),
)
```

Crossref検索で誤った論文が選ばれる場合は、ページタイトルに出版社名などの余分な文字列が残っている可能性があります。

---

### ケースC：ページタイトル末尾の出版社名を除去する

`clean_title()` は、論文タイトル末尾に付いたサイト名を除去します。

現在の例：

```python
suffixes = [
    " | Nature",
    " | SpringerLink",
    " | ScienceDirect",
    " | Oxford Academic",
    " - IOPscience",
    " - NASA ADS",
]
```

例えばページタイトルが次の場合：

```text
Example paper title | Example Publisher
```

次を追加します。

```python
suffixes = [
    " | Nature",
    " | SpringerLink",
    " | ScienceDirect",
    " | Oxford Academic",
    " - IOPscience",
    " - NASA ADS",
    " | Example Publisher",  # 追加
]
```

変更後は、`resolve_paper()` のテストでタイトル一致度を確認してください。

---

### ケースD：URL末尾の余分な文字列をDOIから除去する

一部の出版社URLでは、DOIの後ろに `/pdf`、`/full` などが付く場合があります。`clean_doi()` は一般的な末尾を除去します。

```python
doi = re.sub(
    r"(?i)/(?:pdf|full|abstract|meta|epdf|html?)$",
    "",
    doi,
)
```

例えば、ある出版社が次のURL形式を使うとします。

```text
https://example.com/10.1234/example.5678/download
```

`download` がDOIの一部ではなく、表示形式を示す固定末尾であることを確認したうえで追加します。

```python
doi = re.sub(
    r"(?i)/(?:pdf|full|abstract|meta|epdf|html?|download)$",
    "",
    doi,
)
```

注意事項：

- DOIのsuffixには `/` が含まれることがあります。
- 一般的すぎる語を除去対象にすると、正しいDOIを壊す可能性があります。
- 追加するのは、その出版社でDOIの後ろに必ず付く固定文字列だけにしてください。

---

### ケースE：出版社専用のDOI抽出処理を追加する

metaタグにもHTML本文にもDOIがなく、URLの独自パラメータなどからDOIを組み立てる必要がある場合は、出版社専用関数を追加します。

例：

```python
from urllib.parse import parse_qs, urlparse


def extract_example_publisher_doi(url: str) -> str | None:
    parsed = urlparse(url)

    if parsed.netloc not in {
        "www.example-publisher.com",
        "example-publisher.com",
    }:
        return None

    query = parse_qs(parsed.query)
    raw_doi = query.get("article_doi", [None])[0]

    if not raw_doi:
        return None

    return clean_doi(raw_doi)
```

`fetch_page_metadata()` の冒頭付近で利用します。

```python
final_url = response.url

doi = extract_example_publisher_doi(final_url)

if not doi:
    doi = extract_doi(final_url)
```

出版社専用処理を追加する場合も、最終的には必ず次の形式へ正規化します。

```text
https://doi.org/<DOI>
```

---

### DOIを取得できないURL

次のようなページでは、自動取得できない場合があります。

- JavaScript実行後にのみ書誌情報が表示される
- ログインや大学認証が必要
- BotからのHTTPアクセスを拒否している
- DOIを持たない文献
- ページ内にDOIも正式タイトルもない
- 出版社独自IDしか公開していない

この場合の優先対応は次です。

1. DOIを直接Slackへ投稿する
2. arXiv URLを投稿する
3. 出版社専用の抽出処理を追加する
4. DOIを持たない資料として別処理を実装する

現在のBotはDOIを重複判定の基準にしているため、**DOIを持たない資料は標準処理の対象外**です。

---

## 9.2 新しい雑誌略称を追加する

DOIの取得に成功しても、Citationに表示する雑誌名が正式名称のままになることがあります。

雑誌略称は `JOURNAL_ABBREVIATIONS` に追加します。

```python
JOURNAL_ABBREVIATIONS = {
    "The Astrophysical Journal": "ApJ",
    "Solar Physics": "Sol. Phys.",
    "Example Journal of Space Science": "EJSS",
}
```

左側はCrossrefから返される正式名称、右側はCitationに表示したい略称です。

Crossrefから返される実際の雑誌名は、次のテストで確認できます。

```bash
python3 - <<'PYTEST'
from paper_inbox_bot_zotero import crossref_metadata_by_doi

metadata = crossref_metadata_by_doi("10.1234/example.5678")
print(metadata)
PYTEST
```

略称を追加した後、Citationは次の形式になります。

```text
Author, A., et al. 2026, EJSS, 12, 34
```

---

## 9.3 Zoteroの文献種別を追加する

現在の標準処理は次の文献種別を想定しています。

| 入力 | Zotero item type |
|---|---|
| 通常の査読論文 | `journalArticle` |
| arXiv | `preprint` |
| `preprint` が利用できない環境 | `manuscript` または `journalArticle` へフォールバック |

会議論文、書籍の章、学位論文などへ対応する場合は、Crossrefの `type` をZoteroのitem typeへ変換する対応表を追加できます。

例：

```python
CROSSREF_TO_ZOTERO_ITEM_TYPE = {
    "journal-article": "journalArticle",
    "proceedings-article": "conferencePaper",
    "book-chapter": "bookSection",
    "dissertation": "thesis",
    "posted-content": "preprint",
}
```

`crossref_metadata_from_item()` 内の `item_type` を次のように変更します。

```python
crossref_type = str(item.get("type") or "")

item_type = CROSSREF_TO_ZOTERO_ITEM_TYPE.get(
    crossref_type,
    "journalArticle",
)

return {
    "title": ...,
    "citation": ...,
    "source": "crossref-doi",
    "item_type": item_type,
    ...
}
```

文献種別によってZoteroのフィールド名が異なるため、必要に応じて `build_zotero_item()` に追加します。

例：会議論文の会議録名

```python
set_template_field(
    item,
    "proceedingsTitle",
    str(paper.get("publication_title") or ""),
)
```

例：学位論文の大学名

```python
set_template_field(
    item,
    "university",
    str(paper.get("publisher") or ""),
)
```

`set_template_field()` は、取得したZotero templateにそのフィールドが存在する場合だけ値を設定するため、文献種別ごとのフィールド差を安全に扱えます。

---

## 9.4 変更後の確認手順

コードを変更したら、次の順番で確認します。

### 1. 構文確認

```bash
python3 -m py_compile paper_inbox_bot_zotero.py
```

### 2. URL解決のみ確認

```bash
python3 - <<'PYTEST'
from paper_inbox_bot_zotero import resolve_paper

test_urls = [
    "https://追加した出版社の論文URL",
    "https://doi.org/10.1234/example.5678",
]

for url in test_urls:
    result = resolve_paper(url)
    print("=" * 80)
    print(url)
    print(result)
PYTEST
```

### 3. Botサービスを再起動

```bash
sudo systemctl restart paper-inbox-bot.service
```

### 4. ログ確認

```bash
journalctl -u paper-inbox-bot.service -n 100 --no-pager
```

### 5. Slackで実際に投稿

確認項目：

- DOIが `https://doi.org/<DOI>` 形式へ正規化されたか
- 正しいTitleが取得されたか
- Citationの雑誌略称が正しいか
- Slackリストで重複登録されていないか
- Zoteroの正しいitem typeとコレクションへ登録されたか

# 10. Citation形式

Citationは次の形式で生成します。

```text
FirstAuthor, Initial., et al. Year, Journal, Volume, Page
```

例：

```text
Jarolim, R., et al. 2026, ApJ, 1004, 168
```

雑誌略称は `JOURNAL_ABBREVIATIONS` で定義されています。

別分野の雑誌を追加する場合：

```python
JOURNAL_ABBREVIATIONS = {
    "The Astrophysical Journal": "ApJ",
    "Solar Physics": "Sol. Phys.",
    "Your Journal Full Name": "Your Abbreviation",
}
```

---

# 11. 重複時の動作

## Slackリスト

この処理は、Slack Listsを利用する方式だけで実行されます。

`DOI/link` 列の正規化済みURLで重複を確認します。

- 未登録：新しい行を作成
- 登録済み：新しい行を作らない

Slack Listsを利用できない方式では、この確認を省略し、Zotero側のDOI重複確認だけを実行します。

## Zotero

DOI欄とURL欄の両方を確認します。

| Zoteroの状態 | 動作 |
|---|---|
| DOIが存在しない | 新規アイテムを作成 |
| DOIは存在するが指定コレクションにない | 既存アイテムへコレクションを追加 |
| DOIが存在し指定コレクションにもある | 変更しない |

Slackリストに登録済みでも、Zoteroに未登録ならZoteroへ追加されます。

---

# 12. Zoteroへ保存する情報

取得可能な範囲で、次を保存します。

- Title
- 全著者
- Abstract
- Publication title
- Journal abbreviation
- Volume
- Issue
- Pages / article number
- Date
- DOI
- DOI URL
- ISSN
- Language
- 指定コレクション
- 元のSlackメッセージURL

通常の論文は `journalArticle` として登録します。

arXivは `preprint` を優先し、Zotero側で利用できない場合は `manuscript` または `journalArticle` へフォールバックします。

現在の実装はPDFファイルを自動添付しません。

---

# 13. systemdで常駐させる

Cursorやターミナルを開き続けずに実行するには、systemdサービスとして登録します。

## 13.1 Pythonパスを確認

```bash
python3 -c "import sys; print(sys.executable)"
```

例：

```text
/home/<USER>/Research_code/wsl-venv/bin/python3
```

## 13.2 systemdが有効か確認

```bash
ps -p 1 -o comm=
```

正常：

```text
systemd
```

WSLでsystemdが無効の場合、`/etc/wsl.conf`：

```ini
[boot]
systemd=true
```

Windows PowerShellで：

```powershell
wsl --shutdown
```

## 13.3 サービスファイルを作る

```bash
sudo nano /etc/systemd/system/paper-inbox-bot.service
```

例：

```ini
[Unit]
Description=Slack and Zotero Paper Inbox Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<USER>
WorkingDirectory=/home/<USER>/Research_code/other_things/paper_inbox_bot

ExecStart=/home/<USER>/Research_code/wsl-venv/bin/python3 /home/<USER>/Research_code/other_things/paper_inbox_bot/paper_inbox_bot_zotero.py

Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

`ExecStart` は利用方式に応じて指定してください。

- Slack Listsを利用できる場合：`paper_inbox_bot_zotero.py`
- Slack Listsを利用できない場合：`paper_inbox_bot_zotero_direct.py`

## 13.4 有効化と起動

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now paper-inbox-bot.service
```

確認：

```bash
systemctl status paper-inbox-bot.service --no-pager
```

実行ファイル確認：

```bash
PID=$(systemctl show paper-inbox-bot.service -p MainPID --value)
ps -p "$PID" -o pid,args=
```

出力に次が含まれていれば正常です。

```text
paper_inbox_bot_zotero.py
```

## 13.5 ログ確認

```bash
journalctl -u paper-inbox-bot.service -n 100 --no-pager
```

リアルタイム表示：

```bash
journalctl -u paper-inbox-bot.service -f
```

コード変更後：

```bash
sudo systemctl restart paper-inbox-bot.service
```


## 13.6 Pythonコード・`.env`・依存関係を変更したとき

systemdで起動中のBotは、Pythonコードや `.env` を実行中に自動で読み直しません。変更内容を反映するには、原則としてサービスを再起動します。

### Pythonコードを変更した場合

最初に構文を確認します。実際に使用しているファイル名を指定してください。

Slack Listsを利用できる場合：

```bash
python3 -m py_compile paper_inbox_bot_zotero.py
```

Slack Listsを利用できない場合：

```bash
python3 -m py_compile paper_inbox_bot_zotero_direct.py
```

構文エラーがなければ、サービスを再起動します。

```bash
sudo systemctl restart paper-inbox-bot.service
```

### `.env` を変更した場合

`.env` はBotプロセスの起動時に読み込まれるため、変更後はサービスを再起動します。

```bash
sudo systemctl restart paper-inbox-bot.service
```

`.env` の変更だけであれば、`systemctl daemon-reload` は不要です。

### `requirements.txt` を変更した場合

使用中の仮想環境を有効にし、依存パッケージを更新してからサービスを再起動します。

```bash
source /home/<USER>/Research_code/wsl-venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart paper-inbox-bot.service
```

仮想環境の場所が異なる場合は、実際のパスへ変更してください。

### systemdサービスファイルを変更した場合

次のファイルを変更した場合は、systemdに設定を再読込させてからサービスを再起動します。

```text
/etc/systemd/system/paper-inbox-bot.service
```

実行コマンド：

```bash
sudo systemctl daemon-reload
sudo systemctl restart paper-inbox-bot.service
```

特に、次の項目を変更した場合は `daemon-reload` が必要です。

```ini
ExecStart=...
WorkingDirectory=...
Environment=...
User=...
```

### 変更内容ごとの操作

| 変更したもの | 必要な操作 |
|---|---|
| `paper_inbox_bot_zotero.py` | 構文確認後、`systemctl restart` |
| `paper_inbox_bot_zotero_direct.py` | 構文確認後、`systemctl restart` |
| `.env` | `systemctl restart` |
| `requirements.txt` | `pip install -r requirements.txt` 後、`systemctl restart` |
| `paper-inbox-bot.service` | `daemon-reload` 後、`systemctl restart` |
| `inspect_zotero.py` | Botサービスへの反映操作は不要。次回の手動実行時から反映 |
| `README.md` | Botの実行には影響しない |

`Restart=always` は、Botのプロセスが終了した場合に再起動する設定です。Pythonコードや `.env` の変更を自動検知して再起動する設定ではありません。

### 現在どのPythonファイルが実行されているか確認する

systemdの設定を確認します。

```bash
systemctl show paper-inbox-bot.service -p ExecStart
```

実際に動いているプロセスも確認できます。

```bash
PID=$(systemctl show paper-inbox-bot.service -p MainPID --value)
ps -p "$PID" -o pid,args=
```

Slack Listsを利用する方式では、出力に次が含まれていることを確認します。

```text
paper_inbox_bot_zotero.py
```

Slack Listsを利用しない方式では、次が含まれていることを確認します。

```text
paper_inbox_bot_zotero_direct.py
```

### 再起動後の確認

```bash
systemctl status paper-inbox-bot.service --no-pager
journalctl -u paper-inbox-bot.service -n 100 --no-pager
```

`Active: active (running)` と、Socket Mode接続成功のログが表示されれば正常です。

---

# 14. Windows起動時にWSLも起動する

systemdサービスがenabledでも、Windows起動後にWSL自体が起動していないとBotは動きません。

Windowsタスクスケジューラで、ログオン時にWSLを起動します。

## プログラム

```text
C:\Windows\System32\wsl.exe
```

## 引数

```text
-d Ubuntu-24.04 -u root -- /bin/bash -lc "systemctl start paper-inbox-bot.service; exec sleep infinity"
```

`Ubuntu-24.04` は次で確認した実際のディストリビューション名へ変更します。

```powershell
wsl -l -q
```

PCがスリープ、シャットダウン、ネットワーク切断中はBotも動作しません。完全な24時間稼働が必要な場合は、VPS、Linuxサーバー、Raspberry Piなどへ配置してください。


## 14.1 Pythonコードや`.env`を変更した場合のWindowsタスク

Windowsタスクスケジューラが次のsystemdサービスを起動する設定であれば、Pythonコードや `.env` を変更しても、通常はWindows側のタスク設定を変更する必要はありません。

```text
paper-inbox-bot.service
```

変更後はWSL側でサービスを再起動します。

```bash
sudo systemctl restart paper-inbox-bot.service
```

systemdサービスファイル自体を変更した場合は、次を実行します。

```bash
sudo systemctl daemon-reload
sudo systemctl restart paper-inbox-bot.service
```

Windowsタスクスケジューラ側の変更が必要になるのは、主に次の場合です。

- systemdのサービス名を変更した
- WSLディストリビューション名を変更した
- タスクの引数内に記載したサービス名やディストリビューション名を変更した
- WSLを起動するコマンドそのものを変更した

---

# 15. 既存SlackリストをZoteroへ一括同期する

このセクションは、**Slack Listsを利用できる場合のみ**対象です。Slack Listsを利用できない方式では、同期元のリストがないため、このスクリプトは使用しません。

`sync_slack_list_to_zotero.py` は、既存Slackリストを読み、Zotero側だけを同期します。

Slackリストの内容は変更しません。

## 動作

- ZoteroにないDOI：新規登録
- Zoteroにはあるが指定コレクションにない：コレクション追加
- すでに指定コレクションにある：変更なし
- Slackリスト内の重複DOI：2件目以降をスキップ
- DOI/linkが空欄：スキップ

## Dry Run

最初は変更なしで確認します。

```bash
python3 sync_slack_list_to_zotero.py --dry-run
```

ログ保存：

```bash
python3 sync_slack_list_to_zotero.py --dry-run \
  | tee sync_slack_list_dry_run.log
```

## 実行

```bash
python3 sync_slack_list_to_zotero.py
```

ログ保存：

```bash
python3 sync_slack_list_to_zotero.py \
  | tee sync_slack_list_to_zotero.log
```

一括同期スクリプトは `paper_inbox_bot_zotero.py` の関数をimportするため、同じディレクトリへ置いてください。

---

# 16. 他のユーザーが変更すべき設定

このBotを別の人・別のSlack・別のZoteroで使用する場合、最低限次を変更します。

| 項目 | 変更場所 |
|---|---|
| Slack Bot Token | `.env` の `SLACK_BOT_TOKEN` |
| Slack App Token | `.env` の `SLACK_APP_TOKEN` |
| 監視チャンネル | `.env` の `TARGET_CHANNEL_ID` |
| Slack List | `.env` の `SLACK_LIST_ID`（Slack Lists利用方式のみ） |
| Slack列構成 | 5つの `SLACK_COL_*`（Slack Lists利用方式のみ） |
| Crossref連絡先 | `.env` の `CONTACT_EMAIL` |
| Zotero API Key | `.env` の `ZOTERO_API_KEY` |
| Zotero User ID | `.env` の `ZOTERO_USER_ID` |
| Zotero保存先 | `.env` の `ZOTERO_COLLECTION_KEY` |
| Linuxユーザー名 | systemd unitの `User` とパス |
| Python仮想環境 | systemd unitの `ExecStart` |
| WSLディストリビューション | Windowsタスクスケジューラの引数 |

Slackリストの列を作り直した場合は、列名が同じでもColumn IDは変わるため、再取得が必要です。

---

# 17. トラブルシューティング

## Botが反応しない

確認項目：

1. Botが対象プライベートチャンネルに参加しているか
2. `message.groups` を購読しているか
3. `groups:history` があるか
4. Scope変更後にAppを再インストールしたか
5. `TARGET_CHANNEL_ID` が正しいか
6. systemdサービスが起動中か

```bash
systemctl status paper-inbox-bot.service --no-pager
journalctl -u paper-inbox-bot.service -n 100 --no-pager
```

## `list_not_found`

このエラーはSlack Listsを利用する方式でのみ発生します。

- List IDが正しいか
- リストを対象チャンネルへ共有したか
- チャンネルへ編集権限を付けたか
- `lists:read` / `lists:write` があるか
- Scope変更後に再インストールしたか

## `python-dotenv could not parse statement`

`.env` に通常の文章、Markdownコードフェンス、全角記号などが入っています。

正しい形式：

```env
# コメント
KEY=value
```

不正な例：

````text
```env
KEY=value
```
````

READMEのコードブロック記号を `.env` へコピーしないでください。

## タイトルが未取得

原因候補：

- DOIがCrossrefへ登録されていない
- 出版社ページがBotアクセスを拒否している
- ページに書誌metaタグがない
- arXiv APIが一時的に応答しない

DOIを直接投稿すると最も安定します。

## Zoteroに反映されない

- API Keyがwrite権限を持つか
- `ZOTERO_USER_ID` が数値IDか
- `ZOTERO_COLLECTION_KEY` が最下層コレクションか
- Zoteroデスクトップで同期が有効か
- systemdログにZotero APIエラーがないか

## サービスが古いPythonファイルを実行する

確認：

```bash
systemctl show paper-inbox-bot.service -p ExecStart
```

`ExecStart` が次を指している必要があります。

```text
paper_inbox_bot_zotero.py
```

修正後：

```bash
sudo systemctl daemon-reload
sudo systemctl restart paper-inbox-bot.service
```

---

# 18. 現在の制限

- 1つのSlack投稿につき1論文を想定
- PDFファイルはZoteroへ自動添付しない
- DOIがない文献は自動登録できない場合がある
- Crossrefタイトル検索は誤登録防止のため低一致度候補を拒否する
- Zotero重複判定は主にDOIとDOI URLで行う
- WSLを使用する場合、PCが停止・スリープ中は動作しない

---

# 19. セキュリティ上の注意

- `.env` をGitへcommitしない
- Slack TokenやZotero API Keyをチャット・Issue・ログへ貼らない
- 誤って公開したTokenはただちに再発行する
- `.env` の権限を制限する

```bash
chmod 600 .env
```

- systemdログへTokenを出力しない
- 共有PCでは、プロジェクトディレクトリと `.env` のアクセス権を確認する

---

# 20. 参考リンク

- Slack Apps: <https://api.slack.com/apps>
- Slack Socket Mode: <https://docs.slack.dev/apis/events-api/using-socket-mode>
- Slack Lists API（Slack Lists利用方式のみ）: <https://docs.slack.dev/reference/methods/slackLists.items.create>
- Bolt for Python: <https://docs.slack.dev/tools/bolt-python/getting-started>
- Zotero Web API Basics: <https://www.zotero.org/support/dev/web_api/v3/basics>
- Zotero Web API Write Requests: <https://www.zotero.org/support/dev/web_api/v3/write_requests>
- Zotero API Keys: <https://www.zotero.org/settings/keys>
- WSL systemd: <https://learn.microsoft.com/windows/wsl/systemd>

---

## License

このリポジトリを公開する場合は、用途に応じてLICENSEファイルを追加してください。

