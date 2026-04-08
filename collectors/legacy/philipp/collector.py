from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from collectors.common import INTERIM_DIR, RAW_DIR, ensure_directory

BASE_DOMAIN = "https://www.vesti.ru"
API_URL = f"{BASE_DOMAIN}/api/politika?page=1"
RAW_DB_PATH = RAW_DIR / "vesti" / "vesti_all_news.db"
INTERIM_TEXT_PATH = INTERIM_DIR / "vesti" / "vesti_all_news.txt"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SignalBot/1.0)",
    "Accept": "application/json",
}


def init_db(db_path: Path = RAW_DB_PATH) -> sqlite3.Connection:
    ensure_directory(db_path.parent)
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            url TEXT UNIQUE
        )
        """
    )
    connection.commit()
    return connection


def get_article_links(max_pages: int = 100, delay_seconds: float = 1.0) -> list[str]:
    session = requests.Session()
    links: list[str] = []
    seen: set[str] = set()
    api_url: str | None = API_URL
    page_counter = 0

    while api_url and page_counter < max_pages:
        response = session.get(api_url, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        page_counter += 1

        for item in data.get("data", []):
            href = item.get("url")
            if not href:
                continue

            full_url = href if href.startswith("http") else f"{BASE_DOMAIN}{href}"
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

        next_path = (data.get("pagination") or {}).get("next")
        api_url = None
        if next_path:
            api_url = next_path if next_path.startswith("http") else f"{BASE_DOMAIN}{next_path}"
            time.sleep(delay_seconds)

    return links


def parse_article(url: str) -> tuple[str | None, str | None]:
    response = requests.get(url, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]}, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = "Без заголовка"
    for tag_name in ("h1", "h2"):
        title_node = soup.find(tag_name)
        if title_node and title_node.get_text(strip=True):
            title = title_node.get_text(" ", strip=True)
            break

    content_blocks = soup.find_all("div", class_="article__text")
    if not content_blocks:
        content_blocks = soup.find_all("p")

    parts = [block.get_text(" ", strip=True) for block in content_blocks if block.get_text(strip=True)]
    content = " ".join(parts).strip() or soup.get_text(" ", strip=True)
    return title, content


def save_to_db(connection: sqlite3.Connection, title: str, content: str, url: str) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO articles (title, content, url)
        VALUES (?, ?, ?)
        """,
        (title, content, url),
    )
    connection.commit()


def write_to_text_file(path: Path, articles: list[dict[str, str]]) -> Path:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for article in articles:
            handle.write(f"Заголовок: {article['title']}\n")
            handle.write(f"URL: {article['url']}\n\n")
            handle.write(article["content"])
            handle.write("\n\n" + ("-" * 80) + "\n\n")
    return path


def run_collection(
    max_pages: int = 100,
    delay_seconds: float = 1.0,
    db_path: Path = RAW_DB_PATH,
    text_output_path: Path = INTERIM_TEXT_PATH,
) -> tuple[Path, Path, int]:
    connection = init_db(db_path)
    links = get_article_links(max_pages=max_pages, delay_seconds=delay_seconds)
    articles_for_export: list[dict[str, str]] = []

    for url in links:
        title, content = parse_article(url)
        if not title or not content:
            continue

        save_to_db(connection, title, content, url)
        articles_for_export.append({"title": title, "content": content, "url": url})
        time.sleep(delay_seconds)

    write_to_text_file(text_output_path, articles_for_export)
    connection.close()
    return db_path, text_output_path, len(articles_for_export)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Vesti/Smotrim legacy articles.")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--db-output", type=Path, default=RAW_DB_PATH)
    parser.add_argument("--text-output", type=Path, default=INTERIM_TEXT_PATH)
    args = parser.parse_args()

    db_path, text_path, total = run_collection(
        max_pages=args.max_pages,
        delay_seconds=args.delay,
        db_path=args.db_output,
        text_output_path=args.text_output,
    )
    print(f"Saved {total} Vesti articles to {text_path} and {db_path}")


if __name__ == "__main__":
    main()
