# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

import logging
import os
import shutil
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from kedro.framework.cli.cli import KedroCLI
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

logger = logging.getLogger(__name__)


class SessionTimeSuite:
    """Benchmark suite for KedroSession startup and run times."""

    def setup(self): #noqa: PLR0912, PLR0915
        """Set up a minimal Kedro project structure for benchmarking."""

        self.project_path = Path("benchmarks/session_project")

        # Clean up any existing project directory to avoid conflicts
        if self.project_path.exists():
            shutil.rmtree(self.project_path)

        self.project_path.mkdir(parents=True, exist_ok=True)
        self.original_cwd = Path.cwd()

        # Change to parent directory to ensure project is created in the right location
        os.chdir(self.project_path.parent)
        cli = KedroCLI(self.project_path.parent)
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
            os.chdir(self.original_cwd)  # Return to original directory

        created_project = None
        for potential_dir in self.project_path.parent.iterdir():
            if potential_dir.is_dir() and (potential_dir / "pyproject.toml").exists():
                try:
                    with (potential_dir / "pyproject.toml").open("rb") as f:
                        pyproject_data = tomllib.load(f)
                    if "tool" in pyproject_data and "kedro" in pyproject_data["tool"]:
                        created_project = potential_dir
                        break
                except Exception as e:
                    logger.debug(f"Failed to process {potential_dir}: {e}")
                    continue

        if created_project and created_project != self.project_path:
            for item in created_project.iterdir():
                shutil.move(str(item), str(self.project_path / item.name))
            created_project.rmdir()

        for potential_dir in self.project_path.parent.iterdir():
            if potential_dir.is_dir() and potential_dir.name.startswith("test-"):
                try:
                    if (potential_dir / "pyproject.toml").exists():
                        with (potential_dir / "pyproject.toml").open("rb") as f:
                            pyproject_data = tomllib.load(f)
                        if "tool" in pyproject_data and "kedro" in pyproject_data["tool"]:
                            shutil.rmtree(potential_dir, ignore_errors=True)
                except Exception as e:
                    logger.debug(f"Failed to clean up {potential_dir}: {e}")

        # Bootstrap the project for kedro pipeline create
        bootstrap_project(self.project_path)

        with (self.project_path / "pyproject.toml").open("rb") as f:
            pyproject_data = tomllib.load(f)
        self.package_name = pyproject_data["tool"]["kedro"]["package_name"]
        self.package_dir = self.project_path / "src" / self.package_name

        pipeline_names = ["pipeline_1", "pipeline_2", "pipeline_3", "pipeline_4", "pipeline_5"]
        pipelines_dir = self.package_dir / "pipelines"
        for pipeline_name in pipeline_names:
            pipeline_dir = pipelines_dir / pipeline_name
            if pipeline_dir.exists():
                continue

            cli = KedroCLI(self.project_path)
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
                pass
            except Exception as e:
                logger.debug(f"Failed to create pipeline '{pipeline_name}': {e}")

        dummy_task_code = '''
def dummy_task():
    """A simple dummy task that creates and returns a dictionary."""
    result = {}
    for i in range(100):
        result[f"key_{i}"] = i * 2
    return result
'''

        for i, pipeline_name in enumerate(["pipeline_1", "pipeline_2", "pipeline_3", "pipeline_4", "pipeline_5"], 1):
            pipeline_file = self.package_dir / "pipelines" / pipeline_name / "pipeline.py"
            output_name = f"output_{i}"
            node_name = f"node_{i}"
            pipeline_content = f'''"""
This is a boilerplate pipeline '{pipeline_name}'
generated using Kedro
"""

from kedro.pipeline import Node, Pipeline

{dummy_task_code}

def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline([
        Node(dummy_task, None, "{output_name}", name="{node_name}")
    ])
'''
            pipeline_file.write_text(pipeline_content)

        # Update catalog.yml to add output datasets
        catalog_file = self.project_path / "conf" / "base" / "catalog.yml"
        if catalog_file.exists():
            catalog_content = catalog_file.read_text()
        else:
            catalog_content = ""

        catalog_content += """
output_1:
    type: kedro.io.MemoryDataset

output_2:
    type: kedro.io.MemoryDataset

output_3:
    type: kedro.io.MemoryDataset

output_4:
    type: kedro.io.MemoryDataset

output_5:
    type: kedro.io.MemoryDataset
"""
        catalog_file.write_text(catalog_content)

    def teardown(self):
        """Clean up after benchmarking."""
        import os

        os.chdir(self.original_cwd)

        if hasattr(self, "project_path") and self.project_path.exists():
            shutil.rmtree(self.project_path, ignore_errors=True)

    def time_session_run_single_pipeline(self):
        """Benchmark creating a session and running only one specific pipeline."""
        with KedroSession.create(
            project_path=self.project_path, save_on_close=False
        ) as session:
            session.run(pipeline_name="pipeline_1")

    def time_session_run_all_pipelines(self):
        """Benchmark creating a session and running all pipelines."""
        with KedroSession.create(
            project_path=self.project_path, save_on_close=False
        ) as session:
            session.run()  # Runs the __default__ pipeline which will run all of them

    def time_session_startup_only(self):
        """Benchmark just the session creation/startup time without running."""
        session = KedroSession.create(
            project_path=self.project_path, save_on_close=False
        )
        session.close()

    def time_session_startup_and_context_load(self):
        """Benchmark session creation and context loading."""
        session = KedroSession.create(
            project_path=self.project_path, save_on_close=False
        )
        session.load_context()
        session.close()
