"""Slack Paper Inbox Bot with Zotero integration.

このファイルは公開・共有用のテンプレートです。
個人用のトークン、ID、メールアドレス、フォルダーの絶対パスはコード内に
直接記述せず、このファイルと同じフォルダーに置く `.env` で設定してください。

必要な `.env` の例（`...` を各利用者の値へ置き換える）::

    # Slack App
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_APP_TOKEN=xapp-...
    TARGET_CHANNEL_ID=...

    # Slack List
    SLACK_LIST_ID=...
    SLACK_COL_CITATION=...
    SLACK_COL_TITLE=...
    SLACK_COL_DOI_LINK=...
    SLACK_COL_MEMO=...
    SLACK_COL_MESSAGE=...

    # API問い合わせ時の連絡先（推奨）
    CONTACT_EMAIL=...

    # Zotero
    ZOTERO_API_KEY=...
    ZOTERO_USER_ID=...
    ZOTERO_COLLECTION_KEY=...

変更箇所:
    原則として、このPythonファイルではなく `.env` だけを変更します。
    Citation形式やジャーナル略称を変更したい場合のみ、
    `JOURNAL_ABBREVIATIONS` または `build_crossref_citation()` を編集してください。

実行例::

    python3 paper_inbox_bot_zotero_public.py

秘密情報を含む `.env` はGitへコミットしないでください。
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
from pathlib import Path
import sys
import uuid
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


# `.env` はカレントディレクトリではなく、このファイルと同じ場所から読み込みます。
# これにより、systemdなど別の場所から起動しても設定を読み込めます。
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger("paper-inbox-bot")


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
#
# 【利用者が変更する場所】
# このセクションへトークンやIDを直接書かず、同じフォルダーの `.env` に
# 設定してください。`.env` の例はファイル先頭の説明を参照してください。
#


def required_env(name: str) -> str:
    """必須の環境変数を取得し、未設定や `...` のままなら明確に停止する。"""
    value = os.getenv(name, "").strip()
    if not value or value == "...":
        raise RuntimeError(
            f"Required environment variable {name} is not configured. "
            "Replace `...` in .env with your own value."
        )
    return value


# Slack AppのOAuthトークン。
# Slack App管理画面の OAuth & Permissions / App-Level Tokens から取得します。
SLACK_BOT_TOKEN = required_env("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = required_env("SLACK_APP_TOKEN")

# 書き込み対象のSlack List IDと各列ID。
# List URLや slackLists.items.info の schema から確認します。
SLACK_LIST_ID = required_env("SLACK_LIST_ID")
COL_CITATION = required_env("SLACK_COL_CITATION")
COL_TITLE = required_env("SLACK_COL_TITLE")
COL_DOI_LINK = required_env("SLACK_COL_DOI_LINK")
COL_MEMO = required_env("SLACK_COL_MEMO")
COL_MESSAGE = required_env("SLACK_COL_MESSAGE")

# 監視するSlackチャンネルID。
# 誤って他のチャンネルを処理しないよう、公開版では必須設定にしています。
TARGET_CHANNEL_ID = required_env("TARGET_CHANNEL_ID")

# Crossref・arXiv等へのAPI問い合わせに使用する連絡先。
# `.env` の CONTACT_EMAIL=... を自分のメールアドレスへ置き換えることを推奨します。
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()
if CONTACT_EMAIL == "...":
    CONTACT_EMAIL = ""

# Zotero Web API設定。
# ZOTERO_USER_IDは数値ID、ZOTERO_COLLECTION_KEYは保存先コレクションのキーです。
ZOTERO_API_KEY = required_env("ZOTERO_API_KEY")
ZOTERO_USER_ID = required_env("ZOTERO_USER_ID")
ZOTERO_COLLECTION_KEY = required_env("ZOTERO_COLLECTION_KEY")
ZOTERO_API_BASE = "https://api.zotero.org"

USER_AGENT = "PaperInboxBot/1.0"
if CONTACT_EMAIL:
    USER_AGENT += f" (mailto:{CONTACT_EMAIL})"

HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

REQUEST_TIMEOUT = 20
CROSSREF_TITLE_THRESHOLD = 0.82

app = App(token=SLACK_BOT_TOKEN)


# -----------------------------------------------------------------------------
# Patterns and normalizers
# -----------------------------------------------------------------------------

DOI_RE = re.compile(r"(?i)\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)")
ARXIV_RE = re.compile(
    r"(?i)(?:arxiv:|arxiv\.org/(?:abs|pdf)/)"
    r"([a-z0-9.\-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?"
)
SLACK_OR_PLAIN_URL_RE = re.compile(
    r"<(https?://[^>|]+)(?:\|[^>]+)?>|(?<!<)(https?://[^\s<>]+)"
)
MEMO_RE = re.compile(r"(?ims)^\s*(?:memo|メモ)\s*[:：]\s*(.*)$")


JOURNAL_ABBREVIATIONS = {
    "The Astrophysical Journal": "ApJ",
    "Astrophysical Journal": "ApJ",
    "The Astrophysical Journal Letters": "ApJL",
    "Astrophysical Journal Letters": "ApJL",
    "The Astrophysical Journal Supplement Series": "ApJS",
    "Astrophysical Journal Supplement Series": "ApJS",
    "The Astronomical Journal": "AJ",
    "Astronomical Journal": "AJ",
    "Astronomy & Astrophysics": "A&A",
    "Astronomy and Astrophysics": "A&A",
    "Monthly Notices of the Royal Astronomical Society": "MNRAS",
    "Solar Physics": "Sol. Phys.",
    "Space Weather": "Space Weather",
    "Journal of Geophysical Research: Space Physics": "JGR Space Physics",
    "Journal of Geophysical Research: Space Physics (1978–2012)": "JGR Space Physics",
    "Geophysical Research Letters": "GRL",
    "Publications of the Astronomical Society of Japan": "PASJ",
    "Publications of the Astronomical Society of the Pacific": "PASP",
    "Nature Astronomy": "Nat. Astron.",
    "Nature": "Nature",
    "Science": "Science",
}


def clean_doi(raw_doi: str) -> str:
    doi = unquote(raw_doi.strip())
    doi = re.sub(r"(?i)^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"(?i)^doi\s*:\s*", "", doi)
    doi = doi.split("?")[0].split("#")[0]
    doi = re.sub(r"(?i)/(?:pdf|full|abstract|meta|epdf|html?)$", "", doi)
    return doi.strip("<>.,;:、。)）]】}'\"")


def doi_url(doi: str) -> str:
    return f"https://doi.org/{doi}"


def extract_doi(text: str) -> str | None:
    match = DOI_RE.search(unquote(text))
    return clean_doi(match.group(1)) if match else None


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in SLACK_OR_PLAIN_URL_RE.finditer(text):
        url = match.group(1) or match.group(2)
        url = url.strip("<>.,;:、。)）]】}'\"")
        if url not in urls:
            urls.append(url)
    return urls


def extract_arxiv_id(text: str) -> str | None:
    match = ARXIV_RE.search(unquote(text))
    return match.group(1) if match else None


def arxiv_id_from_doi(doi: str) -> str | None:
    prefix = "10.48550/arxiv."
    if doi.lower().startswith(prefix):
        return doi[len(prefix) :]
    return None


def arxiv_doi(arxiv_id: str) -> str:
    # arXiv:2202.01037 -> 10.48550/arXiv.2202.01037
    # arXiv:astro-ph/0601001 -> 10.48550/arXiv.astro-ph/0601001
    canonical = re.sub(r"v\d+$", "", arxiv_id, flags=re.I)
    return f"10.48550/arXiv.{canonical}"


def clean_title(title: str) -> str:
    title = BeautifulSoup(html.unescape(title), "html.parser").get_text(" ")
    title = re.sub(r"\s+", " ", title).strip()

    # 出版社名などの一般的なページタイトル末尾を除く。
    suffixes = [
        " | Nature",
        " | SpringerLink",
        " | ScienceDirect",
        " | Oxford Academic",
        " - IOPscience",
        " - NASA ADS",
    ]
    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title


def normalize_title_for_compare(title: str) -> str:
    title = clean_title(title).lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(
        None,
        normalize_title_for_compare(a),
        normalize_title_for_compare(b),
    ).ratio()


def extract_memo(text: str) -> str:
    match = MEMO_RE.search(text)
    return match.group(1).strip() if match else ""


# -----------------------------------------------------------------------------
# Metadata sources
# -----------------------------------------------------------------------------


def request_json(url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        headers=HTTP_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def crossref_date_parts(item: dict[str, Any]) -> list[int]:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = item.get(key, {}).get("date-parts")
        if parts and parts[0]:
            return [int(value) for value in parts[0] if value is not None]
    return []


def format_date_parts(parts: list[int]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return str(parts[0])
    if len(parts) == 2:
        return f"{parts[0]:04d}-{parts[1]:02d}"
    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"


def crossref_year(item: dict[str, Any]) -> str:
    parts = crossref_date_parts(item)
    return str(parts[0]) if parts else ""


def author_name_and_initials(author: dict[str, Any]) -> str:
    family = str(author.get("family") or author.get("name") or "").strip()
    given = str(author.get("given") or "").strip()
    if not family:
        return ""
    if not given:
        return family

    initials: list[str] = []
    for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", given):
        initials.append(token[0].upper() + ".")
    return f"{family}, {' '.join(initials)}" if initials else family


def crossref_creators(item: dict[str, Any]) -> list[dict[str, str]]:
    creators: list[dict[str, str]] = []
    for author in item.get("author") or []:
        family = str(author.get("family") or "").strip()
        given = str(author.get("given") or "").strip()
        name = str(author.get("name") or "").strip()
        if family or given:
            creators.append(
                {
                    "creatorType": "author",
                    "firstName": given,
                    "lastName": family,
                }
            )
        elif name:
            creators.append({"creatorType": "author", "name": name})
    return creators


def abbreviate_journal(journal: str) -> str:
    journal = clean_title(journal) if journal else ""
    return JOURNAL_ABBREVIATIONS.get(journal, journal)


def build_crossref_citation(item: dict[str, Any]) -> str:
    authors = item.get("author") or []
    first_author = author_name_and_initials(authors[0]) if authors else ""
    year = crossref_year(item)

    containers = item.get("container-title") or []
    short_containers = item.get("short-container-title") or []
    journal_source = str(short_containers[0]) if short_containers else (
        str(containers[0]) if containers else ""
    )
    journal = abbreviate_journal(journal_source)
    volume = str(item.get("volume") or "").strip()
    page = str(item.get("page") or item.get("article-number") or "").strip()

    if first_author:
        author_part = f"{first_author}, et al." if len(authors) > 1 else first_author
    else:
        author_part = ""

    head = " ".join(part for part in (author_part, year) if part)
    tail = ", ".join(part for part in (journal, volume, page) if part)
    return f"{head}, {tail}" if head and tail else head or tail


def clean_abstract(value: str) -> str:
    if not value:
        return ""
    return clean_title(value)


def crossref_metadata_from_item(item: dict[str, Any]) -> dict[str, Any]:
    titles = item.get("title") or []
    containers = item.get("container-title") or []
    short_containers = item.get("short-container-title") or []
    issn_values = [str(value).strip() for value in (item.get("ISSN") or []) if value]

    return {
        "title": clean_title(str(titles[0])) if titles else "",
        "citation": build_crossref_citation(item),
        "source": "crossref-doi",
        "item_type": "journalArticle",
        "creators": crossref_creators(item),
        "abstract": clean_abstract(str(item.get("abstract") or "")),
        "publication_title": clean_title(str(containers[0])) if containers else "",
        "journal_abbreviation": abbreviate_journal(
            str(short_containers[0]) if short_containers else (
                str(containers[0]) if containers else ""
            )
        ),
        "volume": str(item.get("volume") or "").strip(),
        "issue": str(item.get("issue") or "").strip(),
        "pages": str(item.get("page") or item.get("article-number") or "").strip(),
        "date": format_date_parts(crossref_date_parts(item)),
        "issn": ", ".join(issn_values),
        "language": str(item.get("language") or "").strip(),
        "arxiv_id": "",
    }


def crossref_metadata_by_doi(doi: str) -> dict[str, Any] | None:
    try:
        data = request_json(
            f"https://api.crossref.org/works/{quote(doi, safe='')}",
        )
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return None
        LOGGER.warning("Crossref DOI lookup failed for %s: %s", doi, exc)
        return None
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Crossref DOI lookup failed for %s: %s", doi, exc)
        return None

    item = data.get("message") or {}
    return crossref_metadata_from_item(item)


def crossref_search_by_title(title: str) -> dict[str, Any] | None:
    try:
        data = request_json(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": title,
                "rows": 5,
                "select": (
                    "DOI,title,container-title,short-container-title,"
                    "issued,published,published-print,published-online,"
                    "created,author,volume,issue,page,article-number,score,"
                    "abstract,ISSN,language"
                ),
            },
        )
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Crossref title search failed: %s", exc)
        return None

    candidates: list[dict[str, Any]] = []
    for item in data.get("message", {}).get("items", []):
        metadata = crossref_metadata_from_item(item)
        candidate_title = str(metadata.get("title") or "")
        candidate_doi = clean_doi(str(item.get("DOI") or ""))
        if not candidate_title or not candidate_doi:
            continue
        candidates.append(
            {
                "doi": candidate_doi,
                **metadata,
                "source": "crossref-title-search",
                "similarity": title_similarity(title, candidate_title),
            }
        )

    return max(candidates, key=lambda x: x["similarity"], default=None)


def split_person_name(full_name: str) -> tuple[str, str]:
    full_name = re.sub(r"\s+", " ", full_name).strip()
    if not full_name:
        return "", ""
    if "," in full_name:
        family, given = [part.strip() for part in full_name.split(",", 1)]
        return given, family
    parts = full_name.split()
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def arxiv_metadata(arxiv_id: str) -> dict[str, Any] | None:
    canonical = re.sub(r"v\d+$", "", arxiv_id, flags=re.I)
    try:
        response = requests.get(
            "https://export.arxiv.org/api/query",
            params={"id_list": canonical},
            headers=HTTP_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as exc:
        LOGGER.warning("arXiv lookup failed for %s: %s", canonical, exc)
        return None

    atom = "{http://www.w3.org/2005/Atom}"
    entry = root.find(f"{atom}entry")
    if entry is None:
        return None

    title_node = entry.find(f"{atom}title")
    summary_node = entry.find(f"{atom}summary")
    published_node = entry.find(f"{atom}published")
    author_nodes = entry.findall(f"{atom}author")

    title = clean_title(title_node.text or "") if title_node is not None else ""
    abstract = clean_title(summary_node.text or "") if summary_node is not None else ""
    published = (published_node.text or "").strip() if published_node is not None else ""
    date = published[:10] if published else ""
    year = date[:4] if date else ""

    creators: list[dict[str, str]] = []
    author_names: list[str] = []
    for author_node in author_nodes:
        name_node = author_node.find(f"{atom}name")
        if name_node is None or not name_node.text:
            continue
        full_name = re.sub(r"\s+", " ", name_node.text).strip()
        author_names.append(full_name)
        given, family = split_person_name(full_name)
        creators.append(
            {
                "creatorType": "author",
                "firstName": given,
                "lastName": family,
            }
        )

    first_author = ""
    if author_names:
        given, family = split_person_name(author_names[0])
        initials = " ".join(
            f"{token[0].upper()}." for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", given)
        )
        first_author = f"{family}, {initials}".strip() if family else author_names[0]

    if first_author:
        author_part = f"{first_author}, et al." if len(author_names) > 1 else first_author
    else:
        author_part = ""
    head = " ".join(part for part in (author_part, year) if part)
    citation = f"{head}, arXiv:{canonical}" if head else f"arXiv:{canonical}"

    return {
        "title": title,
        "citation": citation,
        "source": "arxiv-api",
        "item_type": "preprint",
        "creators": creators,
        "abstract": abstract,
        "publication_title": "",
        "journal_abbreviation": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "date": date,
        "issn": "",
        "language": "",
        "arxiv_id": canonical,
    }


def page_meta_content(soup: BeautifulSoup, names: tuple[str, ...]) -> str | None:
    for name in names:
        for attr in ("name", "property"):
            tag = soup.find("meta", attrs={attr: re.compile(rf"^{re.escape(name)}$", re.I)})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()
    return None


def fetch_page_metadata(url: str) -> dict[str, str | None]:
    try:
        response = requests.get(
            url,
            headers=HTTP_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("Page fetch failed for %s: %s", url, exc)
        return {"doi": None, "title": None, "final_url": None}

    final_url = response.url
    doi = extract_doi(final_url)
    if not doi:
        doi = extract_doi(response.headers.get("Content-Disposition", ""))

    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" in content_type:
        return {"doi": doi, "title": None, "final_url": final_url}

    soup = BeautifulSoup(response.text, "html.parser")

    if not doi:
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
        doi = extract_doi(raw_doi or "") or (clean_doi(raw_doi) if raw_doi else None)

    if not doi:
        doi = extract_doi(response.text)

    title = page_meta_content(
        soup,
        (
            "citation_title",
            "dc.title",
            "og:title",
            "twitter:title",
        ),
    )
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    return {
        "doi": doi,
        "title": clean_title(title) if title else None,
        "final_url": final_url,
    }


def empty_metadata() -> dict[str, Any]:
    return {
        "title": "",
        "citation": "",
        "source": "not-found",
        "item_type": "journalArticle",
        "creators": [],
        "abstract": "",
        "publication_title": "",
        "journal_abbreviation": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "date": "",
        "issn": "",
        "language": "",
        "arxiv_id": "",
    }


def enrich_doi(doi: str, *, arxiv_id: str | None = None) -> dict[str, Any]:
    inferred_arxiv_id = arxiv_id or arxiv_id_from_doi(doi)
    if inferred_arxiv_id:
        metadata = arxiv_metadata(inferred_arxiv_id)
        if metadata and metadata.get("title"):
            return metadata

    metadata = crossref_metadata_by_doi(doi)
    if metadata and metadata.get("title"):
        return metadata

    return empty_metadata()


def resolve_paper(text: str) -> dict[str, Any]:
    # 1. DOIがメッセージ中に明示されている。
    doi = extract_doi(text)
    if doi:
        metadata = enrich_doi(doi)
        return {
            "ok": True,
            "doi": doi,
            "doi_url": doi_url(doi),
            **metadata,
            "resolution": "doi-in-message",
        }

    # 2. arXiv URL / arXiv ID。
    arxiv_id = extract_arxiv_id(text)
    if arxiv_id:
        doi = arxiv_doi(arxiv_id)
        metadata = enrich_doi(doi, arxiv_id=arxiv_id)
        return {
            "ok": True,
            "doi": doi,
            "doi_url": doi_url(doi),
            **metadata,
            "resolution": "arxiv-id",
        }

    # 3. URL先のメタデータを調べる。
    urls = extract_urls(text)
    if not urls:
        return {
            "ok": False,
            "reason": "DOI、arXiv ID、URLのいずれも見つかりませんでした。",
        }

    low_confidence: dict[str, Any] | None = None

    for url in urls:
        page = fetch_page_metadata(url)
        page_doi = page.get("doi")
        page_title = page.get("title") or ""

        if page_doi:
            doi = clean_doi(str(page_doi))
            metadata = enrich_doi(doi)
            if not metadata.get("title") and page_title:
                metadata["title"] = page_title
                metadata["source"] = "publisher-page"
            return {
                "ok": True,
                "doi": doi,
                "doi_url": doi_url(doi),
                **metadata,
                "resolution": "doi-from-page",
            }

        if page_title:
            candidate = crossref_search_by_title(page_title)
            if candidate and candidate["similarity"] >= CROSSREF_TITLE_THRESHOLD:
                return {
                    "ok": True,
                    "doi": candidate["doi"],
                    "doi_url": doi_url(candidate["doi"]),
                    **{k: v for k, v in candidate.items() if k not in {"doi", "similarity"}},
                    "resolution": "crossref-title-search",
                    "similarity": candidate["similarity"],
                }
            if candidate:
                low_confidence = {
                    "ok": False,
                    "reason": (
                        "Crossrefに候補はありましたが、タイトル一致度が低いため登録しません。"
                    ),
                    "candidate_doi_url": doi_url(candidate["doi"]),
                    "candidate_title": candidate["title"],
                    "similarity": candidate["similarity"],
                }

    return low_confidence or {
        "ok": False,
        "reason": "ページからDOIを特定できませんでした。DOIまたはarXiv URLを投稿してください。",
    }


# -----------------------------------------------------------------------------
# Slack Lists
# -----------------------------------------------------------------------------


def slack_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }


def slack_api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"https://slack.com/api/{method}",
        headers=slack_headers(),
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API {method} failed: {data.get('error')}")
    return data


def rich_text_value(text: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [{"type": "text", "text": text or ""}],
                }
            ],
        }
    ]


def normalize_url_for_compare(url: str) -> str:
    return unquote(url).strip().rstrip("/").lower()


def list_contains_doi_url(target_url: str) -> bool:
    cursor = ""
    target = normalize_url_for_compare(target_url)

    while True:
        payload: dict[str, Any] = {
            "list_id": SLACK_LIST_ID,
            "limit": 100,
            "archived": False,
        }
        if cursor:
            payload["cursor"] = cursor

        data = slack_api("slackLists.items.list", payload)
        for item in data.get("items", []):
            for field in item.get("fields", []):
                if field.get("column_id") != COL_DOI_LINK:
                    continue
                for link in field.get("link") or []:
                    existing = link.get("originalUrl") or link.get("original_url") or ""
                    if normalize_url_for_compare(existing) == target:
                        return True

        cursor = data.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            return False


def add_to_slack_list(
    *,
    citation: str,
    title: str,
    doi_link: str,
    memo: str,
    message_permalink: str,
) -> dict[str, Any]:
    fields: list[dict[str, Any]] = [
        {
            "column_id": COL_CITATION,
            "rich_text": rich_text_value(citation or title),
        },
        {
            "column_id": COL_TITLE,
            "rich_text": rich_text_value(title),
        },
        {
            "column_id": COL_DOI_LINK,
            "link": [
                {
                    "original_url": doi_link,
                    "display_as_url": False,
                    "display_name": doi_link,
                }
            ],
        },
    ]

    if memo:
        fields.append(
            {
                "column_id": COL_MEMO,
                "rich_text": rich_text_value(memo),
            }
        )

    if message_permalink:
        fields.append(
            {
                "column_id": COL_MESSAGE,
                "message": [message_permalink],
            }
        )

    return slack_api(
        "slackLists.items.create",
        {
            "list_id": SLACK_LIST_ID,
            "initial_fields": fields,
        },
    )


# -----------------------------------------------------------------------------
# Zotero
# -----------------------------------------------------------------------------


_ZOTERO_TEMPLATE_CACHE: dict[str, dict[str, Any]] = {}


def zotero_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Zotero-API-Key": ZOTERO_API_KEY,
        "Zotero-API-Version": "3",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def zotero_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    extra_headers: dict[str, str] | None = None,
) -> requests.Response:
    response = requests.request(
        method,
        f"{ZOTERO_API_BASE}{path}",
        params=params,
        json=json_body,
        headers=zotero_headers(extra_headers),
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code >= 400:
        body = response.text[:2000]
        raise RuntimeError(
            f"Zotero API {method} {path} failed: HTTP {response.status_code}: {body}"
        )
    return response


def get_zotero_template(item_type: str) -> tuple[str, dict[str, Any]]:
    candidate_types = [item_type]
    if item_type == "preprint":
        candidate_types.extend(["manuscript", "journalArticle"])

    for candidate in candidate_types:
        if candidate in _ZOTERO_TEMPLATE_CACHE:
            return candidate, dict(_ZOTERO_TEMPLATE_CACHE[candidate])
        try:
            response = zotero_request(
                "GET",
                "/items/new",
                params={"itemType": candidate},
            )
            template = response.json()
            if isinstance(template, dict) and template.get("itemType"):
                _ZOTERO_TEMPLATE_CACHE[candidate] = template
                return candidate, dict(template)
        except (RuntimeError, ValueError) as exc:
            LOGGER.warning("Could not get Zotero template for %s: %s", candidate, exc)

    raise RuntimeError(f"No usable Zotero item template for {item_type}")


def set_template_field(template: dict[str, Any], field: str, value: Any) -> None:
    if field in template and value not in (None, "", []):
        template[field] = value


def build_zotero_item(paper: dict[str, Any], message_permalink: str) -> dict[str, Any]:
    requested_type = str(paper.get("item_type") or "journalArticle")
    actual_type, item = get_zotero_template(requested_type)
    item["itemType"] = actual_type

    set_template_field(item, "title", str(paper.get("title") or ""))
    set_template_field(item, "creators", paper.get("creators") or [])
    set_template_field(item, "abstractNote", str(paper.get("abstract") or ""))
    set_template_field(item, "date", str(paper.get("date") or ""))
    set_template_field(item, "DOI", str(paper.get("doi") or ""))
    set_template_field(item, "url", str(paper.get("doi_url") or ""))
    set_template_field(item, "language", str(paper.get("language") or ""))

    set_template_field(item, "publicationTitle", str(paper.get("publication_title") or ""))
    set_template_field(
        item,
        "journalAbbreviation",
        str(paper.get("journal_abbreviation") or ""),
    )
    set_template_field(item, "volume", str(paper.get("volume") or ""))
    set_template_field(item, "issue", str(paper.get("issue") or ""))
    set_template_field(item, "pages", str(paper.get("pages") or ""))
    set_template_field(item, "ISSN", str(paper.get("issn") or ""))

    arxiv_id = str(paper.get("arxiv_id") or "")
    set_template_field(item, "repository", "arXiv" if arxiv_id else "")
    set_template_field(item, "archiveID", arxiv_id)
    set_template_field(item, "manuscriptType", "Preprint" if arxiv_id else "")
    set_template_field(item, "type", "Preprint" if arxiv_id else "")

    # 作成時点で最下層の「未印刷」コレクションへ入れる。
    item["collections"] = [ZOTERO_COLLECTION_KEY]

    # 元投稿を追跡できるようにする。既存のExtra値があれば保持する。
    if "extra" in item and message_permalink:
        existing_extra = str(item.get("extra") or "").strip()
        slack_line = f"Slack message: {message_permalink}"
        item["extra"] = f"{existing_extra}\n{slack_line}".strip()

    return item


def normalize_doi_for_compare(value: str) -> str:
    value = str(value or "").strip()
    extracted = extract_doi(value)
    normalized = extracted or clean_doi(value)
    return normalized.lower()


def zotero_items_page(start: int) -> tuple[list[dict[str, Any]], int]:
    response = zotero_request(
        "GET",
        f"/users/{ZOTERO_USER_ID}/items/top",
        params={
            "format": "json",
            "limit": 100,
            "start": start,
            "sort": "dateModified",
            "direction": "desc",
        },
    )
    items = response.json()
    if not isinstance(items, list):
        raise RuntimeError("Unexpected Zotero items response")
    try:
        total = int(response.headers.get("Total-Results", len(items)))
    except ValueError:
        total = len(items)
    return items, total


def find_zotero_item_by_doi(doi: str) -> dict[str, Any] | None:
    target = normalize_doi_for_compare(doi)
    start = 0

    while True:
        items, total = zotero_items_page(start)
        for item in items:
            data = item.get("data") or {}
            existing_doi = normalize_doi_for_compare(str(data.get("DOI") or ""))
            if existing_doi and existing_doi == target:
                return item

            # 古い登録で DOI 欄が空でも、DOI URL が保存されていれば重複扱いにする。
            existing_url = normalize_doi_for_compare(str(data.get("url") or ""))
            if existing_url and existing_url == target:
                return item

        start += len(items)
        if not items or start >= total:
            return None


def get_zotero_item(item_key: str) -> dict[str, Any]:
    response = zotero_request(
        "GET",
        f"/users/{ZOTERO_USER_ID}/items/{item_key}",
    )
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected Zotero item response")
    return data


def add_existing_zotero_item_to_collection(item: dict[str, Any]) -> dict[str, str]:
    item_key = str(item.get("key") or item.get("data", {}).get("key") or "")
    if not item_key:
        raise RuntimeError("Existing Zotero item has no key")

    for attempt in range(2):
        current = item if attempt == 0 else get_zotero_item(item_key)
        data = current.get("data") or {}
        collections = list(data.get("collections") or [])
        if ZOTERO_COLLECTION_KEY in collections:
            return {
                "status": "already-in-collection",
                "item_key": item_key,
                "item_type": str(data.get("itemType") or ""),
            }

        collections.append(ZOTERO_COLLECTION_KEY)
        version = current.get("version") or data.get("version")
        try:
            zotero_request(
                "PATCH",
                f"/users/{ZOTERO_USER_ID}/items/{item_key}",
                json_body={"collections": collections},
                extra_headers={"If-Unmodified-Since-Version": str(version)},
            )
            return {
                "status": "collection-added",
                "item_key": item_key,
                "item_type": str(data.get("itemType") or ""),
            }
        except RuntimeError as exc:
            if "HTTP 412" in str(exc) and attempt == 0:
                continue
            raise

    raise RuntimeError("Failed to update Zotero item after retry")


def create_zotero_item(paper: dict[str, Any], message_permalink: str) -> dict[str, str]:
    item = build_zotero_item(paper, message_permalink)
    response = zotero_request(
        "POST",
        f"/users/{ZOTERO_USER_ID}/items",
        json_body=[item],
        extra_headers={"Zotero-Write-Token": uuid.uuid4().hex},
    )
    result = response.json()
    successful = result.get("successful") or result.get("success") or {}
    failed = result.get("failed") or {}

    saved = successful.get("0")
    if not saved:
        failure = failed.get("0") or failed or result
        raise RuntimeError(f"Zotero item creation failed: {failure}")

    if isinstance(saved, dict):
        item_key = str(saved.get("key") or saved.get("data", {}).get("key") or "")
    else:
        item_key = str(saved)

    return {
        "status": "created",
        "item_key": item_key,
        "item_type": str(item.get("itemType") or ""),
    }


def ensure_zotero_item(paper: dict[str, Any], message_permalink: str) -> dict[str, str]:
    existing = find_zotero_item_by_doi(str(paper["doi"]))
    if existing:
        return add_existing_zotero_item_to_collection(existing)
    return create_zotero_item(paper, message_permalink)


def describe_zotero_status(result: dict[str, str]) -> str:
    status = result.get("status")
    item_key = result.get("item_key") or ""
    if status == "created":
        return f"新規登録しました (`{item_key}`)"
    if status == "collection-added":
        return f"既存アイテムを「未印刷」に追加しました (`{item_key}`)"
    if status == "already-in-collection":
        return f"既に「未印刷」に登録されています (`{item_key}`)"
    return f"処理済み (`{item_key}`)"


# -----------------------------------------------------------------------------
# Event handler
# -----------------------------------------------------------------------------


def get_message_permalink(client: Any, channel: str, message_ts: str) -> str:
    response = client.chat_getPermalink(channel=channel, message_ts=message_ts)
    return str(response.get("permalink") or "")


@app.event("message")
def handle_message_events(body: dict[str, Any], event: dict[str, Any], client: Any, say: Any) -> None:
    # Bot投稿、編集通知、削除通知などは無視する。
    if event.get("bot_id") or event.get("subtype") is not None:
        return

    channel = str(event.get("channel") or "")
    message_ts = str(event.get("ts") or "")
    text = str(event.get("text") or "")

    if TARGET_CHANNEL_ID and channel != TARGET_CHANNEL_ID:
        return

    if not text.strip():
        return

    LOGGER.info("Received Slack message: channel=%s ts=%s text=%r", channel, message_ts, text)

    try:
        paper = resolve_paper(text)

        if not paper.get("ok"):
            details = ""
            if paper.get("candidate_doi_url"):
                details = (
                    f"\n候補: {paper['candidate_doi_url']}"
                    f"\nTitle: {paper.get('candidate_title', '')}"
                    f"\n一致度: {paper.get('similarity', 0):.2f}"
                )
            say(
                text=f"⚠️ 論文を自動登録できませんでした。\n{paper['reason']}{details}",
                thread_ts=message_ts,
            )
            return

        if not paper.get("title"):
            say(
                text=(
                    "⚠️ DOIは取得できましたが、タイトルを取得できなかったため登録を停止しました。\n"
                    f"DOI: {paper['doi_url']}"
                ),
                thread_ts=message_ts,
            )
            return

        permalink = get_message_permalink(client, channel, message_ts)
        memo = extract_memo(text)

        zotero_result: dict[str, str] | None = None
        zotero_error = ""
        try:
            zotero_result = ensure_zotero_item(paper, permalink)
        except Exception as exc:  # noqa: BLE001
            zotero_error = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("Zotero registration failed")

        slack_status = "already-exists"
        slack_item_id = ""
        slack_error = ""
        try:
            if not list_contains_doi_url(str(paper["doi_url"])):
                created = add_to_slack_list(
                    citation=str(paper.get("citation") or ""),
                    title=str(paper["title"]),
                    doi_link=str(paper["doi_url"]),
                    memo=memo,
                    message_permalink=permalink,
                )
                slack_status = "created"
                slack_item_id = str(created.get("item", {}).get("id", ""))
        except Exception as exc:  # noqa: BLE001
            slack_error = f"{type(exc).__name__}: {exc}"
            LOGGER.exception("Slack List registration failed")

        if zotero_error and slack_error:
            say(
                text=(
                    "❌ SlackリストとZoteroの両方で登録に失敗しました。\n"
                    f"*Slack:* `{slack_error}`\n"
                    f"*Zotero:* `{zotero_error}`"
                ),
                thread_ts=message_ts,
            )
            return

        if slack_status == "created":
            slack_description = f"追加しました (`{slack_item_id}`)"
        elif slack_error:
            slack_description = f"失敗しました (`{slack_error}`)"
        else:
            slack_description = "既に登録されています"

        if zotero_result:
            zotero_description = describe_zotero_status(zotero_result)
        else:
            zotero_description = f"失敗しました (`{zotero_error}`)"

        icon = "✅" if not slack_error and not zotero_error else "⚠️"
        say(
            text=(
                f"{icon} 論文登録処理が完了しました。\n"
                f"*Citation:* {paper.get('citation') or '未取得'}\n"
                f"*Title:* {paper['title']}\n"
                f"*DOI:* {paper['doi_url']}\n"
                f"*Slackリスト:* {slack_description}\n"
                f"*Zotero:* {zotero_description}\n"
                f"*Metadata:* `{paper.get('source', 'unknown')}`"
            ),
            thread_ts=message_ts,
            reply_broadcast=True,
        )

    except Exception as exc:  # noqa: BLE001 - Slackへエラーを返してログを残すため
        LOGGER.exception("Paper registration failed")
        say(
            text=f"❌ 登録処理中にエラーが発生しました。\n`{type(exc).__name__}: {exc}`",
            thread_ts=message_ts,
        )


if __name__ == "__main__":
    # 必須設定は import 時に required_env() が検証します。
    LOGGER.info("Starting Paper Inbox Bot with Socket Mode")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
