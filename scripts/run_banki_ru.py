from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Banki.ru collector pipeline.")
    parser.add_argument("--max-page", type=int, default=7734)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--max-articles", type=int, default=None)
    parser.add_argument(
        "--skip-articles",
        action="store_true",
        help="Only collect links and skip article text download.",
    )
    args = parser.parse_args()

    from collectors.banki_ru.mainparse import collect_news_links, write_news_links
    from collectors.banki_ru.newsparser import parse_news, write_articles

    links = collect_news_links(max_page=args.max_page, delay_seconds=args.delay)
    links_path = write_news_links(links)
    print(f"Banki.ru links written to {links_path}")

    if args.skip_articles:
        return

    articles = parse_news(
        links_path=links_path,
        max_articles=args.max_articles,
        delay_seconds=args.delay,
    )
    articles_path = write_articles(articles)
    print(f"Banki.ru articles written to {articles_path}")


if __name__ == "__main__":
    main()
