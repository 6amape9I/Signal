from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import requests

from collectors.common import RAW_DIR, ensure_directory

DEFAULT_OUTPUT_PATH = RAW_DIR / "banki_ru" / "newslinks.txt"
DEFAULT_HEADERS = {
    "Accept": "text/html",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
    ),
}
LINK_PATTERN = re.compile(r'href="/news/lenta/\?id=\d+')


def collect_news_links(max_page: int = 7734, delay_seconds: float = 0.0) -> list[str]:
    session = requests.Session()
    links: list[str] = []

    for page in range(1, max_page + 1):
        response = session.get(
            f"https://www.banki.ru/news/lenta/?page={page}",
            headers=DEFAULT_HEADERS,
            timeout=20,
        )
        response.raise_for_status()

        matches = LINK_PATTERN.findall(response.text)
        links.extend(f"https://www.banki.ru/{match[7:]}" for match in matches)

        if delay_seconds:
            time.sleep(delay_seconds)

    return list(dict.fromkeys(links))


def write_news_links(links: list[str], output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    ensure_directory(output_path.parent)
    output_path.write_text("\n".join(links) + ("\n" if links else ""), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Banki.ru news links.")
    parser.add_argument("--max-page", type=int, default=7734)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    links = collect_news_links(max_page=args.max_page, delay_seconds=args.delay)
    output_path = write_news_links(links, output_path=args.output)
    print(f"Saved {len(links)} Banki.ru links to {output_path}")


if __name__ == "__main__":
    main()
