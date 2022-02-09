import shutil

import pytest

from kedro.framework.project import settings


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture(autouse=True)
def cleanup_pipelines(fake_repo_path, fake_package_path):
    pipes_path = fake_package_path / "pipelines"
    old_pipelines = {p.name for p in pipes_path.iterdir() if p.is_dir()}
    requirements_txt = fake_repo_path / "src" / "requirements.txt"
    requirements = requirements_txt.read_text()
    yield

    # remove created pipeline files after the test
    created_pipelines = {
        p.name for p in pipes_path.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    created_pipelines -= old_pipelines

    for pipeline in created_pipelines:
        shutil.rmtree(str(pipes_path / pipeline))

        confs = fake_repo_path / settings.CONF_ROOT
        for each in confs.rglob(f"*{pipeline}*"):  # clean all pipeline config files
            if each.is_file():
                each.unlink()

        dirs_to_delete = (
            dirpath
            for pattern in ("parameters", "catalog")
            for dirpath in confs.rglob(pattern)
            if dirpath.is_dir() and not any(dirpath.iterdir())
        )
        for dirpath in dirs_to_delete:
            dirpath.rmdir()

        tests = fake_repo_path / "src" / "tests" / "pipelines" / pipeline
        if tests.is_dir():
            shutil.rmtree(str(tests))

    # remove requirements.in and reset requirements.txt
    requirements_in = fake_repo_path / "src" / "requirements.in"
    if requirements_in.exists():
        requirements_in.unlink()
    requirements_txt.write_text(requirements)


@pytest.fixture
def cleanup_dist(fake_repo_path):
    yield
    dist_dir = fake_repo_path / "src" / "dist"
    if dist_dir.exists():
        shutil.rmtree(str(dist_dir))


@pytest.fixture
def cleanup_pyproject_toml(fake_repo_path):
    pyproject_toml = fake_repo_path / "pyproject.toml"
    existing_toml = pyproject_toml.read_text()

    yield

    pyproject_toml.write_text(existing_toml)
