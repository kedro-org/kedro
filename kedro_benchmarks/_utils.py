"""Shared utilities to scaffold a minimal Kedro project for the session benchmarks.

Both ``benchmark_session.py`` and ``benchmark_service_session.py`` need an
identical throwaway project (5 pipelines, dummy nodes, MemoryDataset outputs).
Keep that logic here so a fix only has to be made once.
"""

import logging
import os
import shutil
from pathlib import Path

from kedro.framework.cli.cli import KedroCLI
from kedro.framework.startup import bootstrap_project
from kedro.utils import is_kedro_project

logger = logging.getLogger(__name__)

PIPELINE_NAMES = ["pipeline_1", "pipeline_2", "pipeline_3", "pipeline_4", "pipeline_5"]


def build_benchmark_project(project_path: Path, original_cwd: Path) -> tuple[str, Path]:  # noqa: PLR0912
    """Set up a minimal Kedro project structure for benchmarking.

    Args:
        project_path: Directory the benchmark project will be created in. It is
            (re)created fresh by the caller before this is called.
        original_cwd: Directory to return to after the CLI ``new`` command,
            which changes the working directory.

    Returns:
        A ``(package_name, package_dir)`` tuple for the created project.
    """
    # Change to parent directory to ensure project is created in the right location
    os.chdir(project_path.parent)
    cli = KedroCLI(project_path.parent)
    try:
        cli.main(
            [
                "new",
                "--name",
                "test_project",
                "--tools",
                "none",
                "--example",
                "no",
            ],
            standalone_mode=False,
        )
    except SystemExit:
        pass  # KedroCLI exits after running the command
    finally:
        os.chdir(original_cwd)  # Return to original directory

    created_project = None
    for potential_dir in project_path.parent.iterdir():
        if potential_dir.is_dir() and is_kedro_project(potential_dir):
            created_project = potential_dir
            break

    if created_project and created_project != project_path:
        for item in created_project.iterdir():
            shutil.move(str(item), str(project_path / item.name))
        created_project.rmdir()

    for potential_dir in project_path.parent.iterdir():
        if (
            potential_dir.is_dir()
            and potential_dir.name.startswith("test-")
            and is_kedro_project(potential_dir)
        ):
            shutil.rmtree(potential_dir, ignore_errors=True)

    # Bootstrap the project for kedro pipeline create
    metadata = bootstrap_project(project_path)
    package_name = metadata.package_name
    package_dir = project_path / "src" / package_name

    pipelines_dir = package_dir / "pipelines"
    for pipeline_name in PIPELINE_NAMES:
        pipeline_dir = pipelines_dir / pipeline_name
        if pipeline_dir.exists():
            continue

        cli = KedroCLI(project_path)
        try:
            cli.main(
                [
                    "pipeline",
                    "create",
                    pipeline_name,
                    "--skip-config",
                ],
                standalone_mode=False,
            )
        except SystemExit:
            pass  # KedroCLI exits after running the command
        except Exception as e:
            logger.debug(f"Failed to create pipeline '{pipeline_name}': {e}")

    import textwrap

    dummy_task_code = textwrap.dedent(
        '''
        def dummy_task():
            """A simple dummy task that creates and returns a dictionary."""
            result = {}
            for i in range(100):
                result[f"key_{i}"] = i * 2
            return result
        '''
    ).strip("\n")

    for i, pipeline_name in enumerate(PIPELINE_NAMES, 1):
        pipeline_file = package_dir / "pipelines" / pipeline_name / "pipeline.py"
        output_name = f"output_{i}"
        node_name = f"node_{i}"
        pipeline_content = (
            '"""\n'
            f"This is a boilerplate pipeline '{pipeline_name}'\n"
            "generated using Kedro\n"
            '"""\n\n'
            "from kedro.pipeline import Node, Pipeline\n\n"
            f"{dummy_task_code}\n\n"
            "def create_pipeline(**kwargs) -> Pipeline:\n"
            f"    return Pipeline([Node(dummy_task, None, \"{output_name}\", name=\"{node_name}\")])\n"
        )
        pipeline_file.write_text(pipeline_content)

    # Update catalog.yml to add output datasets
    catalog_file = project_path / "conf" / "base" / "catalog.yml"
    if catalog_file.exists():
        catalog_content = catalog_file.read_text()
    else:
        catalog_content = ""

    catalog_content += (
        "\n"
        "output_1:\n"
        "    type: kedro.io.MemoryDataset\n\n"
        "output_2:\n"
        "    type: kedro.io.MemoryDataset\n\n"
        "output_3:\n"
        "    type: kedro.io.MemoryDataset\n\n"
        "output_4:\n"
        "    type: kedro.io.MemoryDataset\n\n"
        "output_5:\n"
        "    type: kedro.io.MemoryDataset\n"
    )
    catalog_file.write_text(catalog_content)

    return package_name, package_dir


def teardown_benchmark_project(original_cwd: Path, project_path: Path) -> None:
    """Clean up the benchmark project directory."""
    os.chdir(original_cwd)

    if project_path.exists():
        shutil.rmtree(project_path, ignore_errors=True)
