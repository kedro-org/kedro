import shutil
from pathlib import Path

from kedro.framework.session import KedroServiceSession

from ._utils import build_benchmark_project, teardown_benchmark_project


class ServiceSessionTimeSuite:
    """Benchmark suite for KedroServiceSession startup and run times."""

    def setup(self):
        """Set up a minimal Kedro project structure for benchmarking."""
        self.project_path = Path("benchmarks/service_session_project")

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
        """Benchmark creating a service session and running only one specific pipeline."""
        with KedroServiceSession.create(project_path=self.project_path) as session:
            session.run(pipeline_names=["pipeline_1"])

    def time_session_run_all_pipelines(self):
        """Benchmark creating a service session and running all pipelines."""
        with KedroServiceSession.create(project_path=self.project_path) as session:
            session.run()  # Runs the __default__ pipeline which will run all of them

    def time_session_run_multiple_times(self):
        """Benchmark reusing a single service session across multiple pipeline runs."""
        with KedroServiceSession.create(project_path=self.project_path) as session:
            for _ in range(5):
                session.run(pipeline_names=["pipeline_1"])

    def time_session_startup_only(self):
        """Benchmark just the service session creation/startup time without running."""
        session = KedroServiceSession.create(project_path=self.project_path)
        session.close()

    def time_session_startup_and_context_load(self):
        """Benchmark service session creation and context loading."""
        session = KedroServiceSession.create(project_path=self.project_path)
        session.load_context()
        session.close()
