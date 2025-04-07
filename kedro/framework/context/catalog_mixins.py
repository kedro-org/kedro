import logging
from collections.abc import Iterable
from typing import Any

from kedro.framework.project import pipelines as _pipelines
from kedro.io import KedroDataCatalog
from kedro.io.core import is_parameter
from kedro.pipeline import Pipeline


class CatalogCommandsMixin:
    @property
    def _logger(self) -> logging.Logger: ...  # type: ignore[empty-body]

    def list_datasets(
        self: KedroDataCatalog, pipelines: list[str] | list[Pipeline] | None = None
    ) -> dict:
        """Show datasets per type."""

        target_pipelines = pipelines or _pipelines.keys()

        result = {}
        if not isinstance(target_pipelines, Iterable):
            target_pipelines = [target_pipelines]

        for i, pipe in enumerate(target_pipelines):
            pipeline_ds = set()
            pl_obj = _pipelines.get(pipe) if isinstance(pipe, str) else pipe
            if pl_obj:
                pipeline_ds = pl_obj.datasets()

            catalog_ds = set(self.keys())

            patterns_ds = set()
            default_ds = set()
            for ds_name in pipeline_ds - catalog_ds:
                if self.config_resolver.match_pattern(ds_name):
                    patterns_ds.add(ds_name)
                else:
                    default_ds.add(ds_name)

            used_ds_by_type = _group_ds_by_type(
                pipeline_ds - patterns_ds - default_ds, self
            )
            patterns_ds_by_type = _group_ds_by_type(patterns_ds, self)
            default_ds_by_type = _group_ds_by_type(default_ds, self)

            data = (
                ("datasets", used_ds_by_type),
                ("factories", patterns_ds_by_type),
                ("defaults", default_ds_by_type),
            )
            pipe_name = pipe if isinstance(pipe, str) else f"pipeline_{i}"
            result[pipe_name] = {key: value for key, value in data}

        return result

    def list_patterns(self: KedroDataCatalog) -> list[str]:
        """List all dataset factories in the catalog, ranked by priority
        by which they are matched.
        """
        return self.config_resolver.list_patterns()

    def resolve_patterns(
        self: KedroDataCatalog,
        pipelines: list[Pipeline] | None = None,
        include_default: bool = False,
    ) -> dict[str, Any]:
        """Resolve catalog factories against pipeline datasets."""
        # TODO: revise setting default pattern logic based on https://github.com/kedro-org/kedro/issues/4475
        runtime_pattern = {"{default}": {"type": "MemoryDataset"}}
        if include_default:
            self.config_resolver.add_runtime_patterns(runtime_pattern)

        target_pipelines = pipelines or _pipelines.keys()

        pipeline_datasets = set()
        for pipe in target_pipelines:
            pl_obj = _pipelines.get(pipe) if isinstance(pipe, str) else pipe
            if pl_obj:
                pipeline_datasets.update(pl_obj.datasets())

        # We need to include datasets defined in the catalog.yaml and datasets added manually to the catalog
        explicit_datasets = {}
        for ds_name, ds in self.items():
            if is_parameter(ds_name):
                continue

            unresolved_config, _ = self.config_resolver.unresolve_credentials(
                ds_name, ds.to_config()
            )
            explicit_datasets[ds_name] = unresolved_config

        for ds_name in pipeline_datasets:
            if ds_name in explicit_datasets or is_parameter(ds_name):
                continue

            ds_config = self.config_resolver.resolve_pattern(ds_name)
            if ds_config:
                explicit_datasets[ds_name] = ds_config

        if include_default:
            self.config_resolver.remove_runtime_patterns(runtime_pattern)

        return explicit_datasets


def _group_ds_by_type(
    datasets: set[str], catalog: KedroDataCatalog
) -> dict[str, list[str]]:
    mapping = {}
    for ds_name in datasets:
        if is_parameter(ds_name):
            continue

        str_type = catalog.get_type(ds_name)
        if str_type not in mapping:
            mapping[str_type] = []

        mapping[str_type].append(ds_name)

    return mapping
