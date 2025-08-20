"""Behave environment setup commands."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

from features.steps.sh_run import run

_PATHS_TO_REMOVE: set[Path] = set()

FRESH_VENV_TAG = "fresh_venv"
MINOR_PYTHON_38_VERSION = 8


def call(cmd, env):
    res = run(cmd, env=env)
    if res.returncode:
        print(res.stdout)
        print(res.stderr)
        assert False


def before_all(context):
    """Environment preparation before other cli tests are run.
    Installs (core) kedro by running pip in the top level directory.
    """
    context = _setup_minimal_env(context)
    context = _install_project_requirements(context)


def after_all(context):
    for path in _PATHS_TO_REMOVE:
        # ignore errors when attempting to remove already removed directories
        shutil.rmtree(path, ignore_errors=True)


def before_scenario(context, scenario):
    if FRESH_VENV_TAG in scenario.tags:
        context = _setup_minimal_env(context)

    context.temp_dir = _create_tmp_dir()


def _setup_context_with_venv(context, venv_dir):
    context.venv_dir = venv_dir
    # note the locations of some useful stuff
    # this is because exe resolution in subprocess doesn't respect a passed env
    if os.name == "posix":
        bin_dir = context.venv_dir / "bin"
    else:
        bin_dir = context.venv_dir / "Scripts"
    context.bin_dir = bin_dir
    context.pip = str(bin_dir / "pip")
    context.python = str(bin_dir / "python")
    context.kedro = str(bin_dir / "kedro")

    # clone the environment, remove any condas and venvs and insert our venv
    context.env = os.environ.copy()
    path = context.env["PATH"].split(os.pathsep)
    path = [p for p in path if not (Path(p).parent / "pyvenv.cfg").is_file()]
    path = [p for p in path if not (Path(p).parent / "conda-meta").is_dir()]
    path = [str(bin_dir), *path]
    context.env["PATH"] = os.pathsep.join(path)

    # Create an empty pip.conf file and point pip to it
    pip_conf_path = context.venv_dir / "pip.conf"
    pip_conf_path.touch()
    context.env["PIP_CONFIG_FILE"] = str(pip_conf_path)

    return context


def _create_new_venv() -> Path:
    """Create a new venv.

    Returns:
        path to created venv
    """
    # Create venv
    venv_dir = _create_tmp_dir()
    venv.main([str(venv_dir)])
    return venv_dir


def _create_tmp_dir() -> Path:
    """Create a temp directory and add it to _PATHS_TO_REMOVE"""
    tmp_dir = Path(tempfile.mkdtemp()).resolve()
    _PATHS_TO_REMOVE.add(tmp_dir)
    return tmp_dir


def _setup_minimal_env(context):
    if os.environ.get("BEHAVE_LOCAL_ENV"):
        # equivalent run "which kedro"
        output = subprocess.check_output(["which", "kedro"])  # noqa: S603, S607
        output = output.strip().decode("utf8")
        kedro_install_venv_dir = Path(output).parent.parent
        context.kedro_install_venv_dir = kedro_install_venv_dir
        context = _setup_context_with_venv(context, kedro_install_venv_dir)
        return context
    else:
        kedro_install_venv_dir = _create_new_venv()
        context.kedro_install_venv_dir = kedro_install_venv_dir
        context = _setup_context_with_venv(context, kedro_install_venv_dir)

        call(
            [
                context.python,
                "-m",
                "pip",
                "install",
                "-U",
                "pip>=21.2",
            ],
            env=context.env,
        )
        call([context.python, "-m", "pip", "install", "-e", "."], env=context.env)
        return context


def _install_project_requirements(context):
    install_reqs = (
        Path("kedro/templates/project/{{ cookiecutter.repo_name }}/requirements.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    install_reqs = [req for req in install_reqs if "{" not in req and "#" not in req]
    install_reqs.append("kedro-datasets[pandas-csvdataset]")
    call([context.pip, "install", *install_reqs], env=context.env)
    return context
