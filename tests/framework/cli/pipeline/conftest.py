import json
import shutil
from pathlib import Path

import pytest

from kedro.framework.project import settings


def _write_json(filepath: Path, content: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(content, indent=4)
    filepath.write_text(json_str)


def _write_dummy_file(filepath: Path, content: str = ""):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w") as f:
        f.write(content)


@pytest.fixture(autouse=True)
def cleanup_micropackages(fake_repo_path, fake_package_path):
    packages = {p.name for p in fake_package_path.iterdir() if p.is_dir()}

    yield

    created_packages = {
        p.name
        for p in fake_package_path.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    }
    created_packages -= packages

    for micropackage in created_packages:
        shutil.rmtree(str(fake_package_path / micropackage))

        confs = fake_repo_path / settings.CONF_SOURCE
        for each in confs.rglob(f"*{micropackage}*"):
            if each.is_file():
                each.unlink()

        tests = fake_repo_path / "src" / "tests" / micropackage
        if tests.is_dir():
            shutil.rmtree(str(tests))


@pytest.fixture(autouse=True)
def cleanup_pipelines(fake_repo_path, fake_package_path):
    pipes_path = fake_package_path / "pipelines"
    old_pipelines = {p.name for p in pipes_path.iterdir() if p.is_dir()}
    requirements_txt = fake_repo_path / "requirements.txt"
    requirements = requirements_txt.read_text()
    yield

    # remove created pipeline files after the test
    created_pipelines = {
        p.name for p in pipes_path.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    created_pipelines -= old_pipelines

    for pipeline in created_pipelines:
        shutil.rmtree(str(pipes_path / pipeline))

        confs = fake_repo_path / settings.CONF_SOURCE
        for each in confs.rglob(f"*{pipeline}*"):  # clean all pipeline config files
            if each.is_file():
                each.unlink()

        for pattern in ("parameter", "catalog"):
            for dirpath in confs.rglob(pattern):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()

        tests = fake_repo_path / "src" / "tests" / "pipelines" / pipeline
        if tests.is_dir():
            shutil.rmtree(str(tests))

    # reset requirements.txt
    requirements_txt.write_text(requirements)


@pytest.fixture
def cleanup_dist(fake_repo_path):
    yield
    dist_dir = fake_repo_path / "dist"
    if dist_dir.exists():
        shutil.rmtree(str(dist_dir))


@pytest.fixture
def cleanup_pyproject_toml(fake_repo_path):
    pyproject_toml = fake_repo_path / "pyproject.toml"
    existing_toml = pyproject_toml.read_text()

    yield

    pyproject_toml.write_text(existing_toml)


@pytest.fixture()
def fake_local_template_dir(fake_repo_path):
    """Set up a local template directory. This won't be functional we're just testing the actual layout works.

    Note that this is not scoped to module because we don't want to have this folder present in most of the tests,
    so we will tear it down every time.
    """
    template_path = fake_repo_path / Path("templates")
    pipeline_template_path = template_path / Path("pipeline")
    cookiecutter_template_path = (
        pipeline_template_path / "{{ cookiecutter.pipeline_name }}"
    )

    cookiecutter_template_path.mkdir(parents=True)

    # Create the absolute bare minimum files
    cookiecutter_json = {
        "pipeline_name": "default",
    }
    _write_json(pipeline_template_path / "cookiecutter.json", cookiecutter_json)
    _write_dummy_file(
        cookiecutter_template_path / "pipeline_{{ cookiecutter.pipeline_name }}.py",
    )
    _write_dummy_file(cookiecutter_template_path / "__init__.py", "")
    _write_dummy_file(
        cookiecutter_template_path
        / r"config/parameters/{{ cookiecutter.pipeline_name }}.yml",
    )
    _write_dummy_file(
        cookiecutter_template_path / r"tests/test_{{ cookiecutter.pipeline_name }}.py",
    )
    yield template_path.resolve()

    shutil.rmtree(template_path)
