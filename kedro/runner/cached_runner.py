import hashlib
import json
from pathlib import Path
from typing import Any

from pluggy import PluginManager

from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.runner import SequentialRunner
from kedro.runner.task import Task


class CachedRunner(SequentialRunner):
    def __init__(
        self,
        run_only_missing=False,
        metadata_dir=".kedro_node_cache",
        is_async: bool = False,
    ):
        self.run_only_missing = run_only_missing
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self._is_async = is_async
        self._hook_manager = None
        self._session_id = None
        self._run_only_missing = True
        super().__init__()

    def _hash_dataset(self, data: Any) -> str:
        """Hash data for change detection."""
        try:
            data_str = json.dumps(data, sort_keys=True, default=str)
        except Exception:
            data_str = str(data)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def _load_and_fingerprint_inputs(
        self, node: Node, catalog: DataCatalog
    ) -> dict[str, str]:
        input_fingerprints = {}
        for name in node.inputs:
            try:
                data = catalog.load(name)
                input_fingerprints[name] = self._hash_dataset(data)
            except Exception:
                input_fingerprints[name] = "unavailable"
        return input_fingerprints

    def _output_exists(self, name: str, catalog: DataCatalog) -> bool:
        dataset = catalog._datasets.get(name)
        if not dataset:
            return False
        if hasattr(dataset, "exists") and callable(dataset.exists):
            try:
                return dataset.exists()
            except Exception:
                return False
        try:
            dataset.load()
            return True
        except Exception:
            return False

    def _get_cache_file(self, node: Node) -> Path:
        safe_name = node.name.replace(" ", "_").replace("/", "_")
        return self.metadata_dir / f"{safe_name}.json"

    def _should_run_node(self, node: Node, catalog: DataCatalog) -> bool:
        if not self._run_only_missing:
            return True

        # 1. Check output exists
        all_outputs_exist = all(
            self._output_exists(name, catalog) for name in node.outputs
        )
        if not all_outputs_exist:
            return True

        # 2. Check if inputs have changed
        input_fingerprints = self._load_and_fingerprint_inputs(node, catalog)
        cache_file = self._get_cache_file(node)
        if not cache_file.exists():
            return True  # First-time run or no metadata

        try:
            with open(cache_file) as f:
                previous_fingerprints = json.load(f)
            if input_fingerprints != previous_fingerprints:
                return True  # Input has changed
            return False  # Inputs and outputs are good; skip
        except Exception:
            return True

    def _save_fingerprints(self, node: Node, fingerprints: dict[str, str]):
        cache_file = self._get_cache_file(node)
        with open(cache_file, "w") as f:
            json.dump(fingerprints, f, indent=2)

    def _run_node(self, node: Node, catalog: DataCatalog):
        node_task = Task(
            node=node,
            catalog=catalog,
            is_async=self._is_async,
            hook_manager=self._hook_manager,
            session_id=self._session_id,
        )
        node_task.execute()
        return node

    def run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager | None = None,
        session_id: str | None = None,
    ):
        self._hook_manager = hook_manager
        self._session_id = session_id

        for node in pipeline.nodes:
            should_run = self._should_run_node(node, catalog)

            if should_run:
                self._logger.info(f"[RUNNING] {node.name}")
                input_fingerprints = self._load_and_fingerprint_inputs(node, catalog)
                self._save_fingerprints(node, input_fingerprints)
            else:
                self._logger.info(f"[SKIPPED] {node.name} (no input or output changes)")
