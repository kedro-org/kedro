import shutil

import pytest

from kedro.framework.project import settings


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
