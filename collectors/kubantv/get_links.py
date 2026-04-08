from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from collectors.common import RAW_DIR, ensure_directory

BASE_URL = "https://kubantv.ru"
SECTION_URL = f"{BASE_URL}/kultura"
DEFAULT_OUTPUT_PATH = RAW_DIR / "kubantv" / "new_links.txt"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SignalBot/1.0)"}


def fetch_links(
    start_page: int = 2,
    stop_page: int = 42,
    step: int = 2,
    delay_seconds: float = 1.0,
) -> list[str]:
    session = requests.Session()
    links: set[str] = set()

    for page in range(start_page, stop_page, step):
        response = session.get(
            f"{SECTION_URL}?page={page}",
            headers=DEFAULT_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "/kultura/" not in href:
                continue

            absolute_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            links.add(absolute_url)

        time.sleep(delay_seconds)

    return sorted(links)


def write_links(links: list[str], output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    ensure_directory(output_path.parent)
    output_path.write_text("\n".join(links) + ("\n" if links else ""), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Kuban TV article links.")
    parser.add_argument("--start-page", type=int, default=2)
    parser.add_argument("--stop-page", type=int, default=42)
    parser.add_argument("--step", type=int, default=2)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the collected links file.",
    )
    args = parser.parse_args()

    links = fetch_links(
        start_page=args.start_page,
        stop_page=args.stop_page,
        step=args.step,
        delay_seconds=args.delay,
    )
    output_path = write_links(links, args.output)
    print(f"Saved {len(links)} Kuban TV links to {output_path}")


if __name__ == "__main__":
    main()
