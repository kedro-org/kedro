"""Emit clean Markdown copies of every page in the built Zensical site.

AI agents read Markdown more reliably and with fewer tokens than HTML. The
source Markdown in ``docs/`` cannot be published as-is, because Zensical
resolves mkdocstrings directives, mkdocs-click output, snippets and autorefs
while it builds the HTML. This post-build step extracts each rendered article
from ``site/`` and writes it back out as Markdown, at both URL shapes that
agents commonly try: ``<path>/index.md`` and ``<path>.md``.

It also writes an ``llms-full.txt`` bundle with the narrative documentation in
one file, and validates everything it generated.

Adapted from Vizro's ``tools/emit_agent_markdown.py``
(https://github.com/mckinsey/vizro, Apache 2.0).

Usage, from the repository root after ``zensical build``::

    python tools/emit_agent_markdown.py --site-dir=site \
        --exclude=index.html \
        --canary=api/io/kedro.io.DataCatalog/index.html \
        --bundle=llms-full.txt \
        --bundle-exclude-prefix=api \
        --url-placeholder=https://docs.kedro.org/en/stable/

    python tools/emit_agent_markdown.py --site-dir=site --check [same options]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from markdownify import ATX, MarkdownConverter

ARTICLE_SELECTOR = "article.md-content__inner"
REMOVE_SELECTORS = (
    ".headerlink",
    "a[id^=__codelineno]",
    ".md-clipboard",
    ".md-source-file",
    ".md-content__button",
    ".md-feedback",
    # mkdocstrings "Source code in ..." blocks render as a line-number table that
    # Markdown flattens into one huge table row. Agents can read the source on GitHub.
    "details.mkdocstrings-source",
)
RAW_HTML_RE = re.compile(
    r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>",
    flags=re.IGNORECASE,
)
FENCE_START_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
BLOCKQUOTE_PREFIX_RE = re.compile(r"^(?: {0,3}> ?)+")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n\n", flags=re.DOTALL)
RTD_BASE_URL_RE = re.compile(r"https://[^/\s]+(?:/projects/[^/\s]+)?/en/[^/\s]+/")
MAX_FENCE_INDENT = 3


@dataclass(frozen=True)
class Config:
    """Settings for generation and validation."""

    site_dir: Path
    excluded_pages: frozenset[Path] = frozenset()
    canary_page: Path | None = None
    canary_min_chars: int = 10_000
    agent_docs: str | None = None
    bundle_filename: Path | None = None
    bundle_excluded_prefixes: tuple[Path, ...] = ()
    url_placeholder: str | None = None
    published_base_url: str | None = None


class AgentMarkdownConverter(MarkdownConverter):
    """Markdown converter that keeps the language of fenced code blocks."""

    def convert_pre(self, el: Tag, text: str, parent_tags: set[str]) -> str:
        """Convert highlighted ``pre`` elements to fences with an explicit language."""
        code = el.find("code", recursive=False)
        candidates = (el.parent, el, code)
        classes = [
            class_name
            for candidate in candidates
            if isinstance(candidate, Tag)
            for class_name in candidate.get("class", [])
        ]
        if "mermaid" in classes:
            return f"\n```mermaid\n{el.get_text().strip()}\n```\n"
        language_class = next(
            (c for c in classes if c.startswith("language-")), None
        )
        if language_class:
            language = language_class.removeprefix("language-")
            return f"\n```{language}\n{el.get_text().strip()}\n```\n"
        return super().convert_pre(el, text, parent_tags)


def _metadata(soup: BeautifulSoup, html_path: Path) -> tuple[str, str, str]:
    heading = soup.select_one(f"{ARTICLE_SELECTOR} h1")
    description = soup.select_one('meta[name="description"]')
    canonical = soup.select_one('link[rel="canonical"]')
    if not heading or not canonical or not canonical.get("href"):
        raise ValueError(f"{html_path}: expected an article heading and canonical URL")
    for permalink in heading.select(".headerlink"):
        permalink.decompose()  # Otherwise the title ends with the "¶" permalink symbol.
    return (
        heading.get_text(" ", strip=True),
        str(description.get("content", "")) if description else "",
        str(canonical["href"]),
    )


def _rewrite_url(
    value: str, url_placeholder: str | None, published_base_url: str | None
) -> str:
    if url_placeholder and published_base_url and value.startswith(url_placeholder):
        return published_base_url + value.removeprefix(url_placeholder)
    return value


def resolve_published_base_url(
    explicit_url: str | None, url_placeholder: str | None
) -> str | None:
    """Return the base URL of the docs being built, preferring the most precise source.

    On Read the Docs, ``READTHEDOCS_CANONICAL_URL`` points at the version being
    built (``stable``, ``latest``, a release, or a pull request preview).
    """
    published_base_url = explicit_url or os.environ.get("READTHEDOCS_CANONICAL_URL")
    if not published_base_url:
        version = os.environ.get("READTHEDOCS_VERSION")
        if version and url_placeholder:
            stem = url_placeholder.rstrip("/").rsplit("/", 1)[0]
            published_base_url = f"{stem}/{version}/"
    return published_base_url.rstrip("/") + "/" if published_base_url else None


def _canonicalize_links(
    article: Tag,
    source_url: str,
    url_placeholder: str | None = None,
    published_base_url: str | None = None,
) -> None:
    for element in article.select("[title]"):
        # Autorefs stores an HTML tooltip in ``title``. Markdownify would turn it
        # into a Markdown link title and leak raw HTML into the output.
        title = str(element["title"])
        if "<" in title or ">" in title:
            del element["title"]
    for element, attribute in (
        *((element, "href") for element in article.select("[href]")),
        *((element, "src") for element in article.select("[src]")),
    ):
        value = element.get(attribute)
        if value and not str(value).startswith(("data:", "mailto:", "tel:")):
            resolved = urljoin(source_url, str(value))
            element[attribute] = _rewrite_url(
                resolved, url_placeholder, published_base_url
            )


def _label_tabs(article: Tag) -> None:
    """Put each content tab's label above its block.

    Material renders all tab labels in one row, apart from their content, so the
    Markdown would read "uvOther native toolsconda" followed by unlabelled blocks.
    """
    for tabbed_set in article.select(".tabbed-set"):
        labels_row = tabbed_set.select_one(".tabbed-labels")
        content = tabbed_set.select_one(".tabbed-content")
        if not isinstance(labels_row, Tag) or not isinstance(content, Tag):
            continue
        labels = [label.get_text(" ", strip=True) for label in labels_row.select("label")]
        blocks = content.find_all(class_="tabbed-block", recursive=False)
        for label, block in zip(labels, blocks):
            heading = BeautifulSoup("<p><strong></strong></p>", "html.parser").p
            heading.strong.string = label
            block.insert(0, heading)
        labels_row.decompose()


def _quote_admonitions(article: Tag) -> None:
    """Render admonitions as blockquotes with a bold title, such as "> **Note**"."""
    for admonition in article.select("div.admonition, details"):
        title = admonition.find(class_="admonition-title", recursive=False)
        if title is None:
            title = admonition.find("summary", recursive=False)
        if isinstance(title, Tag):
            title.name = "p"
            text = title.get_text(" ", strip=True)
            title.clear()
            strong = BeautifulSoup("<strong></strong>", "html.parser").strong
            strong.string = text
            title.append(strong)
        admonition.name = "blockquote"


def _convert_tag(
    tag: Tag,
    source_url: str,
    url_placeholder: str | None = None,
    published_base_url: str | None = None,
) -> str:
    for selector in REMOVE_SELECTORS:
        for element in tag.select(selector):
            element.decompose()
    _label_tabs(tag)
    _quote_admonitions(tag)
    _canonicalize_links(tag, source_url, url_placeholder, published_base_url)
    converter = AgentMarkdownConverter(heading_style=ATX, bullets="-")
    return converter.convert_soup(tag).strip()


def _frontmatter(
    title: str, description: str, source_url: str, agent_docs: str | None
) -> str:
    frontmatter = (
        "---\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        f"source_url: {json.dumps(source_url)}\n"
    )
    if agent_docs:
        frontmatter += f"agent_docs: {json.dumps(agent_docs)}\n"
    return f"{frontmatter}---"


def html_to_markdown(
    html_path: Path,
    agent_docs: str | None = None,
    url_placeholder: str | None = None,
    published_base_url: str | None = None,
) -> str:
    """Convert one built HTML page to agent-facing Markdown."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    title, description, source_url = _metadata(soup, html_path)
    source_url = _rewrite_url(source_url, url_placeholder, published_base_url)
    if agent_docs and url_placeholder and published_base_url:
        agent_docs = agent_docs.replace(url_placeholder, published_base_url)
    article = soup.select_one(ARTICLE_SELECTOR)
    if not isinstance(article, Tag):
        raise ValueError(f"{html_path}: expected exactly one documentation article")

    body = _convert_tag(article, source_url, url_placeholder, published_base_url)
    frontmatter = _frontmatter(title, description, source_url, agent_docs)
    return f"{frontmatter}\n\n{body}\n"


def markdown_paths(html_path: Path, site_dir: Path) -> tuple[Path, ...]:
    """Return the Markdown paths to write for a built HTML page.

    ``site/a/b/index.html`` produces ``site/a/b/index.md`` and ``site/a/b.md``.
    """
    directory_shape = html_path.with_suffix(".md")
    if html_path.name != "index.html" or html_path.parent == site_dir:
        return (directory_shape,)
    # Not ``Path.with_suffix``: API page directories such as ``kedro.io.DataCatalog``
    # contain dots, and with_suffix would produce ``kedro.io.md`` for all of them.
    page_dir = html_path.parent
    return (directory_shape, page_dir.parent / f"{page_dir.name}.md")


def documentation_pages(config: Config) -> list[Path]:
    """Find built documentation pages.

    A documentation page has a canonical link and an article. Redirect stubs for
    moved pages have a canonical link but no article, so they are skipped.
    """
    pages = []
    for html_path in sorted(config.site_dir.rglob("*.html")):
        if html_path.relative_to(config.site_dir) in config.excluded_pages:
            continue
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        if soup.select_one('link[rel="canonical"]') and soup.select_one(
            ARTICLE_SELECTOR
        ):
            pages.append(html_path)
    return pages


def emit_markdown(config: Config, pages: list[Path]) -> list[Path]:
    """Write Markdown copies of ``pages`` and return the paths written."""
    written = []
    for html_path in pages:
        markdown = html_to_markdown(
            html_path,
            agent_docs=config.agent_docs,
            url_placeholder=config.url_placeholder,
            published_base_url=config.published_base_url,
        )
        for output_path in markdown_paths(html_path, config.site_dir):
            if output_path in written:
                raise ValueError(f"{html_path}: {output_path} was already written")
            output_path.write_text(markdown, encoding="utf-8")
            written.append(output_path)
    return written


def _page_source_url(html_path: Path) -> str:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    canonical = soup.select_one('link[rel="canonical"]')
    if not canonical or not canonical.get("href"):
        raise ValueError(f"{html_path}: expected a canonical URL")
    return str(canonical["href"])


def _is_excluded_from_bundle(relative_path: Path, prefixes: tuple[Path, ...]) -> bool:
    return any(relative_path.is_relative_to(prefix) for prefix in prefixes)


def emit_bundle(config: Config, pages: list[Path]) -> Path | None:
    """Concatenate the generated Markdown of selected pages into one bundle file."""
    if not config.bundle_filename:
        return None

    bundled_pages = []
    for html_path in pages:
        relative_path = html_path.relative_to(config.site_dir)
        if _is_excluded_from_bundle(relative_path, config.bundle_excluded_prefixes):
            continue
        markdown_path = markdown_paths(html_path, config.site_dir)[0]
        markdown = FRONTMATTER_RE.sub(
            "", markdown_path.read_text(encoding="utf-8"), count=1
        ).strip()
        heading, separator, remainder = markdown.partition("\n")
        source_url = _rewrite_url(
            _page_source_url(html_path),
            config.url_placeholder,
            config.published_base_url,
        )
        bundled_pages.append(
            f"{heading}\n\nSource: {source_url}{separator}{remainder}".strip()
        )

    if not bundled_pages:
        raise ValueError("No documentation pages remain after applying bundle exclusions")

    output_path = config.site_dir / config.bundle_filename
    header = (
        "# Kedro documentation\n\n"
        "> All narrative Kedro documentation in one file, without the API reference. "
        "See llms.txt for the curated index, including API reference links."
    )
    output_path.write_text(
        f"{header}\n\n---\n\n" + "\n\n---\n\n".join(bundled_pages) + "\n",
        encoding="utf-8",
    )
    return output_path


def _content_without_code(markdown: str) -> str:
    """Return ``markdown`` with fenced code blocks and inline code removed.

    Fences inside blockquotes (admonitions) count too, so ``> `` markers are
    stripped before looking for fences.
    """
    prose_lines = []
    fence_character = ""
    fence_length = 0
    for quoted_line in markdown.splitlines():
        line = BLOCKQUOTE_PREFIX_RE.sub("", quoted_line)
        if fence_character:
            closing_fence = line.lstrip(" ")
            indentation = len(line) - len(closing_fence)
            closing_candidate = closing_fence.strip()
            if (
                indentation <= MAX_FENCE_INDENT
                and len(closing_candidate) >= fence_length
                and set(closing_candidate) == {fence_character}
            ):
                fence_character = ""
                fence_length = 0
            continue

        match = FENCE_START_RE.match(line)
        if match:
            fence_character = match.group(1)[0]
            fence_length = len(match.group(1))
            continue
        prose_lines.append(line)
    return INLINE_CODE_RE.sub("", "\n".join(prose_lines))


def _check_page_copies(config: Config, documentation: list[Path]) -> list[str]:
    failures = []
    for html_path in documentation:
        for markdown_path in markdown_paths(html_path, config.site_dir):
            if not markdown_path.is_file():
                failures.append(f"missing Markdown copy: {markdown_path}")
                continue
            markdown = markdown_path.read_text(encoding="utf-8")
            prose = _content_without_code(markdown)
            if RAW_HTML_RE.search(prose):
                failures.append(f"raw HTML outside code: {markdown_path}")
            if "__codelineno" in markdown:
                failures.append(f"code-line anchor leaked into: {markdown_path}")
            if "Skip to content" in prose:
                failures.append(f"navigation text leaked into: {markdown_path}")
    return failures


def _check_canary(config: Config) -> list[str]:
    if not config.canary_page:
        return []
    canary_markdown = config.site_dir / config.canary_page.with_suffix(".md")
    if (
        not canary_markdown.is_file()
        or len(canary_markdown.read_text(encoding="utf-8")) < config.canary_min_chars
    ):
        return [f"canary page is missing or unexpectedly short: {canary_markdown}"]
    return []


def _check_bundle(config: Config, documentation: list[Path]) -> list[str]:
    if not config.bundle_filename:
        return []
    bundle_path = config.site_dir / config.bundle_filename
    if not bundle_path.is_file():
        return [f"missing documentation bundle: {bundle_path}"]

    failures = []
    bundle = bundle_path.read_text(encoding="utf-8")
    normalized_bundle = RTD_BASE_URL_RE.sub("{docs-base}/", bundle)
    source_markers = {
        line for line in normalized_bundle.splitlines() if line.startswith("Source: ")
    }
    if RAW_HTML_RE.search(_content_without_code(bundle)):
        failures.append(f"raw HTML outside code: {bundle_path}")
    for html_path in documentation:
        relative_path = html_path.relative_to(config.site_dir)
        source_url = _page_source_url(html_path)
        marker = RTD_BASE_URL_RE.sub("{docs-base}/", f"Source: {source_url}")
        is_excluded = _is_excluded_from_bundle(
            relative_path, config.bundle_excluded_prefixes
        )
        if is_excluded and marker in source_markers:
            failures.append(f"excluded page leaked into bundle: {source_url}")
        elif not is_excluded and marker not in source_markers:
            failures.append(f"page missing from bundle: {source_url}")
    return failures


def check_markdown(config: Config, pages: list[Path]) -> list[str]:
    """Return validation failures for all generated agent-facing files."""
    return [
        *_check_page_copies(config, pages),
        *_check_canary(config),
        *_check_bundle(config, pages),
    ]


def main() -> int:
    """Parse arguments, emit Markdown unless checking, and validate the result."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--site-dir",
        default="site",
        type=Path,
        help="Built documentation directory (default: site).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        type=Path,
        help="HTML path relative to site-dir to skip; repeat for multiple paths.",
    )
    parser.add_argument(
        "--canary",
        type=Path,
        help="HTML path relative to site-dir whose Markdown must exceed --canary-min-chars.",
    )
    parser.add_argument(
        "--canary-min-chars",
        default=10_000,
        type=int,
        help="Minimum size of the canary page's Markdown (default: 10000).",
    )
    parser.add_argument(
        "--agent-docs",
        help="Optional guidance for agents, added to each file's frontmatter.",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help="Write the bundle to this path relative to site-dir.",
    )
    parser.add_argument(
        "--bundle-exclude-prefix",
        action="append",
        default=[],
        type=Path,
        help="Leave pages under this site-relative prefix out of the bundle; repeatable.",
    )
    parser.add_argument(
        "--url-placeholder",
        help="Canonical docs base URL to replace with the base URL of the version being built.",
    )
    parser.add_argument(
        "--published-base-url",
        help=(
            "Base URL of the version being built (default: READTHEDOCS_CANONICAL_URL, "
            "or the URL placeholder with READTHEDOCS_VERSION substituted)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate existing Markdown without regenerating it.",
    )
    args = parser.parse_args()

    if not args.site_dir.is_dir():
        print(f"ERROR: {args.site_dir} not found. Run after `zensical build`.")
        return 1
    published_base_url = resolve_published_base_url(
        args.published_base_url, args.url_placeholder
    )
    if published_base_url and not args.url_placeholder:
        parser.error("--url-placeholder is required when a published base URL is set")

    config = Config(
        site_dir=args.site_dir,
        excluded_pages=frozenset(args.exclude),
        canary_page=args.canary,
        canary_min_chars=args.canary_min_chars,
        agent_docs=args.agent_docs,
        bundle_filename=args.bundle,
        bundle_excluded_prefixes=tuple(args.bundle_exclude_prefix),
        url_placeholder=args.url_placeholder,
        published_base_url=published_base_url,
    )
    pages = documentation_pages(config)
    if not args.check:
        written = emit_markdown(config, pages)
        print(f"Generated {len(written)} Markdown files from {len(pages)} HTML pages.")
        bundle_path = emit_bundle(config, pages)
        if bundle_path:
            print(f"Generated documentation bundle: {bundle_path}.")

    failures = check_markdown(config, pages)
    if failures:
        print("ERROR: agent-facing Markdown validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Agent-facing Markdown validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
