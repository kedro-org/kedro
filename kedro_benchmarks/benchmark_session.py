import shutil
from pathlib import Path

from kedro.framework.session import KedroSession

from ._utils import build_benchmark_project, teardown_benchmark_project


class SessionTimeSuite:
    """Benchmark suite for KedroSession startup and run times."""

    def setup(self):
        """Set up a minimal Kedro project structure for benchmarking."""
        self.project_path = Path("benchmarks/session_project")

        # Clean up any existing project directory to avoid conflicts
        if self.project_path.exists():
            shutil.rmtree(self.project_path)

        self.project_path.mkdir(parents=True, exist_ok=True)
        self.original_cwd = Path.cwd()

        self.package_name, self.package_dir = build_benchmark_project(
            self.project_path, self.original_cwd
        )

    def teardown(self):
        """Clean up after benchmarking."""
        teardown_benchmark_project(self.original_cwd, self.project_path)

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
