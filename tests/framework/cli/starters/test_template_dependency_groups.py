"""Development dependency groups for current and older starter layouts."""

import sys

import pytest
import tomli_w

from kedro.templates.project.hooks import utils

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@pytest.mark.parametrize("layout", ["legacy", "groups", "both"])
@pytest.mark.parametrize(
    "tools",
    [
        [],
        ["Linting"],
        ["Testing"],
        ["Documentation"],
        ["Logging"],
        ["Linting", "Testing"],
    ],
)
@pytest.mark.parametrize("example_pipeline", ["True", "False"])
def test_dev_dependencies_are_never_published_as_extras(
    tmp_path, monkeypatch, layout, tools, example_pipeline
):
    monkeypatch.setattr(utils, "current_dir", tmp_path)
    data = {
        "project": {"name": "demo", "optional-dependencies": {"other": ["requests"]}}
    }
    if layout in {"legacy", "both"}:
        data["project"]["optional-dependencies"]["dev"] = ["pytest", "ruff"]
    if layout in {"groups", "both"}:
        data["dependency-groups"] = {"dev": ["ruff"]}
    project = tmp_path / "pyproject.toml"
    project.write_text(tomli_w.dumps(data))
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("")

    utils.setup_template_tools(
        str(tools), requirements, project, "demo", example_pipeline
    )

    result = tomllib.loads(project.read_text())
    extras = result["project"]["optional-dependencies"]
    assert extras == {"other": ["requests"]}
    if "Linting" in tools or "Testing" in tools:
        expected = (
            ["ruff", "pytest"]
            if layout == "both"
            else (["pytest", "ruff"] if layout == "legacy" else ["ruff"])
        )
        assert result["dependency-groups"]["dev"] == expected
    else:
        assert "dependency-groups" not in result


def test_migration_removes_an_empty_extra_table_and_preserves_other_groups(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(utils, "current_dir", tmp_path)
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\nname="demo"\n[project.optional-dependencies]\ndev=["pytest"]\n'
        '[dependency-groups]\ndev=["pytest"]\nbenchmark=["pytest-benchmark"]\n'
    )
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("")
    utils.setup_template_tools("['Testing']", requirements, project, "demo", "True")
    result = tomllib.loads(project.read_text())
    assert "optional-dependencies" not in result["project"]
    assert result["dependency-groups"] == {
        "dev": ["pytest"],
        "benchmark": ["pytest-benchmark"],
    }
