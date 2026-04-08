from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Kuban TV collector pipeline.")
    parser.add_argument("--start-page", type=int, default=2)
    parser.add_argument("--stop-page", type=int, default=42)
    parser.add_argument("--step", type=int, default=2)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument(
        "--skip-articles",
        action="store_true",
        help="Only collect links and skip article text download.",
    )
    args = parser.parse_args()

    from collectors.kubantv.get_articles import collect_articles, write_articles
    from collectors.kubantv.get_links import fetch_links, write_links

    links = fetch_links(
        start_page=args.start_page,
        stop_page=args.stop_page,
        step=args.step,
        delay_seconds=args.delay,
    )
    links_path = write_links(links)
    print(f"Kuban TV links written to {links_path}")

    if args.skip_articles:
        return

    articles = collect_articles(links_path=links_path)
    articles_path = write_articles(articles)
    print(f"Kuban TV articles written to {articles_path}")


if __name__ == "__main__":
    main()
