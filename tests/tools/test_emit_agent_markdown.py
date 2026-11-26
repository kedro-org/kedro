"""Tests for tools/emit_agent_markdown.py."""

from pathlib import Path

from tools import emit_agent_markdown


def make_html(
    title="Test page",
    description="Test description",
    body="<p>Useful content.</p>",
    canonical="https://docs.kedro.org/en/stable/build/test/",
):
    return f"""<!doctype html>
<html>
  <head>
    <meta name="description" content="{description}">
    <link rel="canonical" href="{canonical}">
  </head>
  <body>
    <nav>Navigation must not leak</nav>
    <article class="md-content__inner md-typeset"><h1>{title}</h1>{body}</article>
  </body>
</html>
"""


def test_html_to_markdown_strips_headerlink_symbols(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(
        make_html(
            title='Title <a class="headerlink" href="#title" title="Permanent link">¶</a>',
            body='<h2 id="section">Section <a class="headerlink" href="#section" title="Permanent link">¶</a></h2>',
        ),
        encoding="utf-8",
    )
    markdown = emit_agent_markdown.html_to_markdown(html_path)
    assert "¶" not in markdown
    assert "# Title" in markdown
    assert "# Section" in markdown


def test_html_to_markdown_converts_highlighted_code_to_python_fence(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(
        make_html(
            body='<div class="language-python highlight"><pre><span></span><code>x = 1</code></pre></div>',
        ),
        encoding="utf-8",
    )
    markdown = emit_agent_markdown.html_to_markdown(html_path)
    assert "```python\nx = 1\n```" in markdown


def test_html_to_markdown_removes_mkdocstrings_source(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(
        make_html(
            body='<details class="mkdocstrings-source"><summary>Source code</summary><pre>code</pre></details><p>After</p>',
        ),
        encoding="utf-8",
    )
    markdown = emit_agent_markdown.html_to_markdown(html_path)
    assert "Source code" not in markdown
    assert "```" not in markdown
    assert "After" in markdown


def test_html_to_markdown_labels_tabbed_content(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(
        make_html(
            body="""
<div class="tabbed-set">
  <input type="radio" name="__tabbed_1" id="__tabbed_1_1" checked>
  <input type="radio" name="__tabbed_1" id="__tabbed_1_2">
  <div class="tabbed-labels">
    <label for="__tabbed_1_1">uv</label>
    <label for="__tabbed_1_2">conda</label>
  </div>
  <div class="tabbed-content">
    <div class="tabbed-block"><p>A</p></div>
    <div class="tabbed-block"><p>B</p></div>
  </div>
</div>
""",
        ),
        encoding="utf-8",
    )
    markdown = emit_agent_markdown.html_to_markdown(html_path)
    assert "**uv**" in markdown
    assert "**conda**" in markdown
    assert "A" in markdown
    assert "B" in markdown
    assert "uvconda" not in markdown


def test_html_to_markdown_converts_admonition_to_blockquote(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text(
        make_html(
            body='<div class="admonition note"><p class="admonition-title">Note</p><p>Text</p></div>',
        ),
        encoding="utf-8",
    )
    markdown = emit_agent_markdown.html_to_markdown(html_path)
    lines = markdown.splitlines()
    assert any(line.startswith("> **Note**") for line in lines)
    assert any(line.startswith("> Text") for line in lines)


def test_html_to_markdown_rewrites_links_and_frontmatter_with_published_base_url(
    tmp_path,
):
    html_path = tmp_path / "index.html"
    html_path.write_text(
        make_html(
            body='<p><a href="../other/">Other</a></p>',
            canonical="https://docs.kedro.org/en/stable/build/test/",
        ),
        encoding="utf-8",
    )
    markdown = emit_agent_markdown.html_to_markdown(
        html_path,
        url_placeholder="https://docs.kedro.org/en/stable/",
        published_base_url="https://docs.kedro.org/en/latest/",
    )
    assert 'source_url: "https://docs.kedro.org/en/latest/build/test/"' in markdown
    assert "[Other](https://docs.kedro.org/en/latest/build/other/)" in markdown


def test_markdown_paths_for_deep_api_page_returns_two_shapes(tmp_path):
    html_path = tmp_path / "site" / "api" / "io" / "kedro.io.DataCatalog" / "index.html"
    assert emit_agent_markdown.markdown_paths(html_path, tmp_path / "site") == (
        tmp_path / "site" / "api" / "io" / "kedro.io.DataCatalog" / "index.md",
        tmp_path / "site" / "api" / "io" / "kedro.io.DataCatalog.md",
    )


def test_markdown_paths_for_root_index_returns_single_path(tmp_path):
    html_path = tmp_path / "site" / "index.html"
    assert emit_agent_markdown.markdown_paths(html_path, tmp_path / "site") == (
        tmp_path / "site" / "index.md",
    )


def test_documentation_pages_skips_redirect_and_excluded_pages(tmp_path):
    (tmp_path / "site").mkdir()
    redirect = tmp_path / "site" / "redirect.html"
    redirect.write_text(
        '<html><head><link rel="canonical" href="https://example.com/"></head><body></body></html>',
        encoding="utf-8",
    )
    normal = tmp_path / "site" / "page" / "index.html"
    normal.parent.mkdir(parents=True)
    normal.write_text(
        make_html(canonical="https://docs.kedro.org/en/stable/page/"),
        encoding="utf-8",
    )
    excluded = tmp_path / "site" / "skip.html"
    excluded.write_text(
        make_html(canonical="https://docs.kedro.org/en/stable/skip/"),
        encoding="utf-8",
    )
    config = emit_agent_markdown.Config(
        site_dir=tmp_path / "site",
        excluded_pages=frozenset({Path("skip.html")}),
    )
    pages = emit_agent_markdown.documentation_pages(config)
    assert redirect not in pages
    assert excluded not in pages
    assert normal in pages


def test_emit_bundle_and_check_pass_for_valid_site(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    root = site_dir / "index.html"
    root.write_text(make_html(title="Home"), encoding="utf-8")
    api_page = site_dir / "api" / "io" / "index.html"
    api_page.parent.mkdir(parents=True)
    api_page.write_text(
        make_html(title="API", canonical="https://docs.kedro.org/en/stable/api/io/"),
        encoding="utf-8",
    )
    guide_page = site_dir / "guide" / "index.html"
    guide_page.parent.mkdir(parents=True)
    guide_page.write_text(
        make_html(title="Guide", canonical="https://docs.kedro.org/en/stable/guide/"),
        encoding="utf-8",
    )
    config = emit_agent_markdown.Config(
        site_dir=site_dir,
        bundle_filename=Path("llms-full.txt"),
        bundle_excluded_prefixes=(Path("api"),),
        url_placeholder="https://docs.kedro.org/en/stable/",
        published_base_url="https://docs.kedro.org/en/stable/",
    )
    pages = emit_agent_markdown.documentation_pages(config)
    written = emit_agent_markdown.emit_markdown(config, pages)
    assert (site_dir / "index.md") in written
    assert (site_dir / "guide" / "index.md") in written
    assert (site_dir / "api" / "io" / "index.md") in written
    bundle_path = emit_agent_markdown.emit_bundle(config, pages)
    assert bundle_path == site_dir / "llms-full.txt"
    bundle = bundle_path.read_text(encoding="utf-8")
    assert "Source: https://docs.kedro.org/en/stable/guide/" in bundle
    assert "Source: https://docs.kedro.org/en/stable/api/io/" not in bundle
    assert emit_agent_markdown.check_markdown(config, pages) == []


def test_check_markdown_detects_raw_html_outside_code(tmp_path):
    site_dir = tmp_path / "site"
    page = site_dir / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(make_html(), encoding="utf-8")
    config = emit_agent_markdown.Config(site_dir=site_dir)
    emit_agent_markdown.emit_markdown(config, [page])
    md_path = site_dir / "index.md"
    md_path.write_text(
        md_path.read_text(encoding="utf-8") + "\n<span>x</span>\n", encoding="utf-8"
    )
    failures = emit_agent_markdown.check_markdown(config, [page])
    assert any("raw HTML outside code" in f for f in failures)


def test_content_without_code_strips_fenced_blocks_inside_blockquotes():
    markdown = """> ```python
> <div>inside code</div>
> ```
<span>outside</span>
"""
    prose = emit_agent_markdown._content_without_code(markdown)
    assert "<div>inside code</div>" not in prose
    assert "<span>outside</span>" in prose


def test_resolve_published_base_url_prefers_explicit():
    assert (
        emit_agent_markdown.resolve_published_base_url("https://ex.com/en/abc/", None)
        == "https://ex.com/en/abc/"
    )


def test_resolve_published_base_url_uses_canonical_url(monkeypatch):
    monkeypatch.setenv("READTHEDOCS_CANONICAL_URL", "https://docs.kedro.org/en/latest")
    monkeypatch.delenv("READTHEDOCS_VERSION", raising=False)
    assert (
        emit_agent_markdown.resolve_published_base_url(None, None)
        == "https://docs.kedro.org/en/latest/"
    )


def test_resolve_published_base_url_falls_back_to_version(monkeypatch):
    monkeypatch.delenv("READTHEDOCS_CANONICAL_URL", raising=False)
    monkeypatch.setenv("READTHEDOCS_VERSION", "1.0.0")
    assert (
        emit_agent_markdown.resolve_published_base_url(
            None, "https://docs.kedro.org/en/stable/"
        )
        == "https://docs.kedro.org/en/1.0.0/"
    )


def test_resolve_published_base_url_returns_none_when_nothing_set(monkeypatch):
    monkeypatch.delenv("READTHEDOCS_CANONICAL_URL", raising=False)
    monkeypatch.delenv("READTHEDOCS_VERSION", raising=False)
    assert emit_agent_markdown.resolve_published_base_url(None, None) is None
