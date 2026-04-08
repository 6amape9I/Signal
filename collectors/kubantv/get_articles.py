from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from collectors.common import INTERIM_DIR, RAW_DIR, ensure_directory

DEFAULT_LINKS_PATH = RAW_DIR / "kubantv" / "new_links.txt"
DEFAULT_OUTPUT_PATH = INTERIM_DIR / "kubantv" / "articles.txt"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    )
}


def _extract_article(soup: BeautifulSoup) -> tuple[str, str]:
    title_node = soup.find("h1")
    title = title_node.get_text(" ", strip=True) if title_node else "Без заголовка"

    blocks = soup.find_all("p", class_="ds-markdown-paragraph")
    if not blocks:
        blocks = soup.find_all("div", class_="article__desc")

    parts = [block.get_text(" ", strip=True) for block in blocks if block.get_text(strip=True)]
    text = " ".join(parts).replace("\xa0", " ").strip()
    return title, text


def collect_articles(
    links_path: Path = DEFAULT_LINKS_PATH,
    delay_min_seconds: float = 0.1,
    delay_max_seconds: float = 1.0,
) -> list[tuple[str, str]]:
    if not links_path.exists():
        raise FileNotFoundError(f"Links file not found: {links_path}")

    session = requests.Session()
    articles: list[tuple[str, str]] = []
    links = [
        line.strip()
        for line in links_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    for url in links:
        response = session.get(url, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title, text = _extract_article(soup)
        articles.append((title, text))
        time.sleep(random.uniform(delay_min_seconds, delay_max_seconds))

    return articles


def write_articles(
    articles: list[tuple[str, str]],
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    ensure_directory(output_path.parent)
    lines = [f"{title}: {text}" for title, text in articles]
    output_path.write_text("\n\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Kuban TV article texts.")
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS_PATH)
    parser.add_argument("--delay-min", type=float, default=0.1)
    parser.add_argument("--delay-max", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    articles = collect_articles(
        links_path=args.links,
        delay_min_seconds=args.delay_min,
        delay_max_seconds=args.delay_max,
    )
    output_path = write_articles(articles, args.output)
    print(f"Saved {len(articles)} Kuban TV articles to {output_path}")


if __name__ == "__main__":
    main()
