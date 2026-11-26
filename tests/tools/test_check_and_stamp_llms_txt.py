"""Tests for tools/check_llms_txt.py and tools/stamp_llms_txt.py."""

from tools import check_llms_txt, stamp_llms_txt


def test_stamp_leaves_file_unchanged_without_env_vars(tmp_path, monkeypatch):
    llms_txt = tmp_path / "llms.txt"
    llms_txt.write_text("https://docs.kedro.org/en/stable/hello", encoding="utf-8")
    monkeypatch.delenv("READTHEDOCS_VERSION", raising=False)
    monkeypatch.delenv("READTHEDOCS_CANONICAL_URL", raising=False)
    assert (
        stamp_llms_txt.stamp_llms_txt("https://docs.kedro.org/en/stable/", tmp_path)
        == 0
    )
    assert (
        llms_txt.read_text(encoding="utf-8") == "https://docs.kedro.org/en/stable/hello"
    )


def test_stamp_replaces_placeholder_with_canonical_url(tmp_path, monkeypatch):
    llms_txt = tmp_path / "llms.txt"
    llms_full_txt = tmp_path / "llms-full.txt"
    llms_txt.write_text("https://docs.kedro.org/en/stable/a", encoding="utf-8")
    llms_full_txt.write_text(
        "Source: https://docs.kedro.org/en/stable/b", encoding="utf-8"
    )
    monkeypatch.setenv("READTHEDOCS_CANONICAL_URL", "https://docs.kedro.org/en/latest")
    monkeypatch.delenv("READTHEDOCS_VERSION", raising=False)
    assert (
        stamp_llms_txt.stamp_llms_txt(
            "https://docs.kedro.org/en/stable/",
            tmp_path,
            filenames=("llms.txt", "llms-full.txt"),
        )
        == 0
    )
    assert llms_txt.read_text(encoding="utf-8") == "https://docs.kedro.org/en/latest/a"
    assert (
        llms_full_txt.read_text(encoding="utf-8")
        == "Source: https://docs.kedro.org/en/latest/b"
    )


def test_stamp_uses_readthedocs_version_fallback(tmp_path, monkeypatch):
    llms_txt = tmp_path / "llms.txt"
    llms_txt.write_text("https://docs.kedro.org/en/stable/x", encoding="utf-8")
    monkeypatch.delenv("READTHEDOCS_CANONICAL_URL", raising=False)
    monkeypatch.setenv("READTHEDOCS_VERSION", "1.0.0")
    assert (
        stamp_llms_txt.stamp_llms_txt("https://docs.kedro.org/en/stable/", tmp_path)
        == 0
    )
    assert llms_txt.read_text(encoding="utf-8") == "https://docs.kedro.org/en/1.0.0/x"


def test_stamp_leaves_unchanged_when_canonical_equals_placeholder(
    tmp_path, monkeypatch
):
    llms_txt = tmp_path / "llms.txt"
    llms_txt.write_text("hello", encoding="utf-8")
    monkeypatch.setenv("READTHEDOCS_CANONICAL_URL", "https://docs.kedro.org/en/stable/")
    monkeypatch.delenv("READTHEDOCS_VERSION", raising=False)
    assert (
        stamp_llms_txt.stamp_llms_txt("https://docs.kedro.org/en/stable/", tmp_path)
        == 0
    )
    assert llms_txt.read_text(encoding="utf-8") == "hello"


def test_stamp_returns_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("READTHEDOCS_CANONICAL_URL", "https://docs.kedro.org/en/latest/")
    monkeypatch.delenv("READTHEDOCS_VERSION", raising=False)
    assert (
        stamp_llms_txt.stamp_llms_txt("https://docs.kedro.org/en/stable/", tmp_path)
        == 1
    )


def test_compute_versioned_url_replaces_version_slug():
    result = stamp_llms_txt.compute_versioned_url(
        "https://docs.kedro.org/en/stable/", "1.0.0"
    )
    assert result == "https://docs.kedro.org/en/1.0.0/"


def test_check_llms_txt_passes_when_all_links_resolve_and_nav_covered(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "site" / "build").mkdir(parents=True)
    (tmp_path / "site" / "deploy.md").write_text("deploy", encoding="utf-8")
    (tmp_path / "site" / "build" / "nodes.md").write_text("nodes", encoding="utf-8")
    (tmp_path / "docs" / "llms.txt").write_text(
        "[Nodes](https://docs.kedro.org/en/stable/build/nodes.md)\n"
        "[Deploy](https://docs.kedro.org/en/stable/deploy.md)\n",
        encoding="utf-8",
    )
    (tmp_path / "zensical.toml").write_text(
        '[project]\nnav = [{"Welcome" = "index.md"}, {"Kedro" = [{"Nodes" = "build/nodes.md"}, {"Deploy" = [{"Overview" = "deploy/index.md"}]}, {"Viz" = "https://example.com/"}]}]\n',
        encoding="utf-8",
    )
    assert check_llms_txt.check_llms_txt() == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_check_llms_txt_fails_for_broken_docs_link(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "site" / "build").mkdir(parents=True)
    (tmp_path / "site" / "build" / "nodes.md").write_text("nodes", encoding="utf-8")
    (tmp_path / "docs" / "llms.txt").write_text(
        "[Nodes](https://docs.kedro.org/en/stable/build/nodes.md)\n"
        "[Missing](https://docs.kedro.org/en/stable/missing.md)\n",
        encoding="utf-8",
    )
    (tmp_path / "zensical.toml").write_text(
        '[project]\nnav = [{"Welcome" = "index.md"}, {"Kedro" = [{"Nodes" = "build/nodes.md"}, {"Deploy" = [{"Overview" = "deploy/index.md"}]}, {"Viz" = "https://example.com/"}]}]\n',
        encoding="utf-8",
    )
    assert check_llms_txt.check_llms_txt() != 0
    captured = capsys.readouterr()
    assert "has no generated file" in captured.out


def test_check_llms_txt_fails_for_unlisted_nav_page(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "site" / "build").mkdir(parents=True)
    (tmp_path / "site" / "deploy.md").write_text("deploy", encoding="utf-8")
    (tmp_path / "site" / "build" / "nodes.md").write_text("nodes", encoding="utf-8")
    (tmp_path / "docs" / "llms.txt").write_text(
        "[Deploy](https://docs.kedro.org/en/stable/deploy.md)\n",
        encoding="utf-8",
    )
    (tmp_path / "zensical.toml").write_text(
        '[project]\nnav = [{"Welcome" = "index.md"}, {"Kedro" = [{"Nodes" = "build/nodes.md"}, {"Deploy" = [{"Overview" = "deploy/index.md"}]}, {"Viz" = "https://example.com/"}]}]\n',
        encoding="utf-8",
    )
    assert check_llms_txt.check_llms_txt() != 0
    captured = capsys.readouterr()
    assert "is in the nav but not in" in captured.out


def test_check_llms_txt_ignores_not_listed_and_external_nav(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "site").mkdir()
    (tmp_path / "docs" / "llms.txt").write_text(
        "[External](https://example.com/)\n", encoding="utf-8"
    )
    (tmp_path / "zensical.toml").write_text(
        '[project]\nnav = [{"Welcome" = "index.md"}, {"Viz" = "https://example.com/"}]\n',
        encoding="utf-8",
    )
    assert check_llms_txt.check_llms_txt() == 0


def test_page_url_maps_deploy_index_to_deploy_md():
    assert (
        check_llms_txt.page_url("deploy/index.md")
        == "https://docs.kedro.org/en/stable/deploy.md"
    )


def test_page_url_maps_build_nodes_to_build_nodes_md():
    assert (
        check_llms_txt.page_url("build/nodes.md")
        == "https://docs.kedro.org/en/stable/build/nodes.md"
    )


def test_url_to_site_path_returns_none_for_external_url():
    assert check_llms_txt.url_to_site_path("https://example.com/") is None
