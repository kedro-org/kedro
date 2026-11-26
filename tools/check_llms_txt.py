"""Check that ``docs/llms.txt`` matches the built docs and the site navigation.

``docs/llms.txt`` is maintained by hand, so this check catches it going stale.
It fails when:

- a docs link in ``llms.txt`` does not resolve to a generated file in ``site/``
  (a page was renamed, moved, or deleted), or
- a page in the ``zensical.toml`` nav has no entry in ``llms.txt`` (a page was
  added without listing it), unless it is in ``NOT_LISTED``.

Docs links in ``llms.txt`` use the Markdown copy of each page, for example
``https://docs.kedro.org/en/stable/build/nodes.md``, which
``tools/emit_agent_markdown.py`` writes to ``site/build/nodes.md``.

Usage, from the repository root after ``zensical build`` and
``tools/emit_agent_markdown.py``::

    python tools/check_llms_txt.py
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

DOCS_BASE_URL = "https://docs.kedro.org/en/stable/"
LLMS_TXT = Path("docs/llms.txt")
SITE_DIR = Path("site")
ZENSICAL_TOML = Path("zensical.toml")

# Nav pages deliberately left out of llms.txt.
NOT_LISTED = {
    "index.md",  # Docs home page: navigation cards only.
    "getting-started/cheatsheet.md",  # Image only; agents use the Kedro for LLMs page.
    "develop/debugging.md",  # Only links to other pages.
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def nav_pages(nav: list[Any]) -> Iterator[str]:
    """Yield the source path of every local page in a Zensical nav."""
    for item in nav:
        for value in item.values():
            if isinstance(value, list):
                yield from nav_pages(value)
            elif not value.startswith(("http://", "https://")):
                yield value


def page_url(source_path: str) -> str:
    """Return the ``llms.txt`` URL for a docs source path.

    ``build/nodes.md`` maps to ``<base>build/nodes.md`` and ``deploy/index.md``
    to ``<base>deploy.md``, matching the files ``emit_agent_markdown.py`` writes.
    """
    path = source_path.removesuffix(".md")
    if path.endswith("/index"):
        path = path.removesuffix("/index")
    return f"{DOCS_BASE_URL}{path}.md"


def url_to_site_path(url: str) -> Path | None:
    """Map a docs URL to its file in ``site/``, or ``None`` for other URLs."""
    if not url.startswith(DOCS_BASE_URL):
        return None
    return SITE_DIR / url.removeprefix(DOCS_BASE_URL)


def check_llms_txt() -> int:
    """Print every problem found and return how many there are."""
    for required in (LLMS_TXT, ZENSICAL_TOML, SITE_DIR):
        if not required.exists():
            print(
                f"ERROR: {required} not found. Run from the repository root after "
                "the docs build and tools/emit_agent_markdown.py."
            )
            return 1

    urls = LINK_RE.findall(LLMS_TXT.read_text(encoding="utf-8"))
    broken = []
    for url in urls:
        site_path = url_to_site_path(url)
        if site_path is not None and not site_path.is_file():
            broken.append((url, site_path))

    nav = tomllib.loads(ZENSICAL_TOML.read_text(encoding="utf-8"))["project"]["nav"]
    listed = set(urls)
    unlisted = [
        source
        for source in nav_pages(nav)
        if source not in NOT_LISTED and page_url(source) not in listed
    ]

    for url, site_path in broken:
        print(f"ERROR: {url} in {LLMS_TXT} has no generated file at {site_path}.")
    for source in unlisted:
        print(
            f"ERROR: docs/{source} is in the nav but not in {LLMS_TXT}. "
            f"Add an entry for {page_url(source)}, or add it to NOT_LISTED in tools/check_llms_txt.py."
        )
    if broken or unlisted:
        return len(broken) + len(unlisted)

    docs_urls = sum(1 for url in urls if url.startswith(DOCS_BASE_URL))
    print(
        f"OK: all {docs_urls} docs URLs in {LLMS_TXT} resolve, "
        "and every nav page is listed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(1 if check_llms_txt() else 0)
