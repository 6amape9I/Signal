

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


def init_db(db_path: str = "vesti_all_news.db") -> sqlite3.Connection:

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    conn.commit()
    return conn


def get_article_links() -> List[str]:

    base_domain = "https://www.vesti.ru"
    api_url: Optional[str] = f"{base_domain}/api/politika?page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GPT-5-Nano)",
        "Accept": "application/json",
    }
    links: List[str] = []
    seen: set[str] = set()

    counter = 0

    while api_url:
        print(counter)
        counter += 1

        if counter > 100:
            return links

        try:
            resp = requests.get(api_url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Ошибка при обращении к API {api_url}: {e}")
            break


        # Extract article URLs from the current page
        for item in data.get("data", []):

            href = item.get("url")
            if not href:
                continue
            # Normalize to absolute URL
            full_url = href
            if href.startswith("/"):
                full_url = base_domain + href
            # Deduplicate
            if full_url not in seen:
                seen.add(full_url)
                links.append(full_url)

        # Determine the next page
        next_path = None
        pagination = data.get("pagination") or {}
        if isinstance(pagination, dict):
            next_path = pagination.get("next")

        if next_path:
            # Build the next API URL; next_path is relative (e.g. "/api/politika?page=2")
            if next_path.startswith("/"):
                api_url = base_domain + next_path
            else:
                api_url = next_path
            # Respectful delay between API calls
            time.sleep(1)
        else:
            api_url = None

    return links


def parse_article(url: str) -> Tuple[Optional[str], Optional[str]]:

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GPT-5-Nano)",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"Ошибка при загрузке статьи {url}: {e}")
        return None, None

    # Extract title
    title: Optional[str] = None
    for tag_name in ["h1", "h2"]:
        el = soup.find(tag_name)
        if el and el.get_text(strip=True):
            title = el.get_text(strip=True)
            break
    if not title:
        title = "Без заголовка"

    # Extract content blocks
    content_blocks = soup.find_all("div", class_="article__text")
    if not content_blocks:
        content_blocks = soup.find_all("p")
    text_chunks = [p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True)]
    full_text = " ".join(text_chunks)
    if not full_text:
        full_text = soup.get_text(separator=" ", strip=True)

    return title, full_text


def save_to_db(conn: sqlite3.Connection, title: str, content: str, url: str) -> None:
    """Insert a parsed article into the database if it's not already present."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO articles (title, content, url)
            VALUES (?, ?, ?)
            """,
            (title, content, url),
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при сохранении статьи {url}: {e}")


def write_to_text_file(filepath: str, articles: List[dict]) -> None:

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for a in articles:
            f.write(f"Заголовок: {a.get('title', 'Без заголовка')}\n")
            f.write(f"URL: {a.get('url', '')}\n\n")
            content = a.get("content", "")
            if content:
                f.write(content + "\n")
            f.write("\n" + ("-" * 80) + "\n\n")


def main() -> None:
    """Entry point for the script."""
    db_path = "vesti_all_news.db"
    conn = init_db(db_path)

    print("Собираю ссылки на все новости раздела 'Политика'...")
    links = get_article_links()
    print(f"Найдено ссылок: {len(links)}")

    articles_for_txt: List[dict] = []

    for i, url in enumerate(links):
        print(f"[{i + 1}/{len(links)}] Обработка: {url}")
        title, content = parse_article(url)
        if title and content:
            save_to_db(conn, title, content, url)
            articles_for_txt.append({"title": title, "content": content, "url": url})
        else:
            print(f"Пропускаю статью: {url}")
        # Pause briefly between article requests to be polite
        time.sleep(1)

    # Display sorted titles from the database
    print("\n--- Отсортированные заголовки из базы данных ---")
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, url FROM articles ORDER BY title ASC")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Заголовок: {row[0]}")
        print(f"Текст (первые 100 символов): {row[1][:100]}...\n")

    txt_path = "vesti_all_news.txt"
    write_to_text_file(txt_path, articles_for_txt)
    print(f"\nТекстовый файл создан: {txt_path}")
    conn.close()


if __name__ == "__main__":
    main()