from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from collectors.common import INTERIM_DIR, RAW_DIR, ensure_directory

DEFAULT_LINKS_PATH = RAW_DIR / "banki_ru" / "newslinks.txt"
DEFAULT_OUTPUT_PATH = INTERIM_DIR / "banki_ru" / "statyi.txt"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SignalBot/1.0)"}


def _extract_article(soup: BeautifulSoup) -> tuple[str, str]:
    title_node = soup.find("h1")
    title = title_node.get_text(" ", strip=True) if title_node else "Без заголовка"

    wrapper = soup.find(
        "div",
        class_=lambda value: value and "Markdownstyled__Wrapper" in value,
    )
    paragraphs: list[str] = []

    if wrapper:
        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in wrapper.find_all("p")
            if paragraph.get_text(strip=True)
        ]

    if not paragraphs:
        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in soup.find_all("p")
            if paragraph.get_text(strip=True)
        ]

    text = " ".join(paragraphs).replace("\xa0", " ").strip()
    return title, text


def parse_news(
    links_path: Path = DEFAULT_LINKS_PATH,
    max_articles: int | None = None,
    delay_seconds: float = 0.0,
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

    if max_articles is not None:
        links = links[:max_articles]

    for link in links:
        response = session.get(link, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        articles.append(_extract_article(soup))

        if delay_seconds:
            time.sleep(delay_seconds)

    return articles


def write_articles(
    articles: list[tuple[str, str]],
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    ensure_directory(output_path.parent)
    output = "".join(f"{title}\n{text}\n\n" for title, text in articles)
    output_path.write_text(output, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Banki.ru article texts.")
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS_PATH)
    parser.add_argument("--max-articles", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    articles = parse_news(
        links_path=args.links,
        max_articles=args.max_articles,
        delay_seconds=args.delay,
    )
    output_path = write_articles(articles, output_path=args.output)
    print(f"Saved {len(articles)} Banki.ru articles to {output_path}")


if __name__ == "__main__":
    main()
