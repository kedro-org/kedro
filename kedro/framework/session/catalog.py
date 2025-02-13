from typing import Any

from kedro.framework.project import pipelines
from kedro.io import KedroDataCatalog


class CatalogCommandsMixin:
    context = None
    _logger = None

    def rank_catalog_factories(self) -> list[str]:
        """List all dataset factories in the catalog, ranked by priority
        by which they are matched.
        """

        return self.context.catalog.config_resolver.list_patterns()

    def resolve_patterns(self, include_default: bool = False) -> dict[str, Any]:
        """Resolve catalog factories against pipeline datasets."""
        catalog = self.context.catalog

        # TODO: remove after moving to new catalog
        if not isinstance(catalog, KedroDataCatalog):
            self._logger.warning(
                "This method is available for `KedroDataCatalog` only."
            )
            return {}

        # TODO: revise setting default pattern logic based on https://github.com/kedro-org/kedro/issues/4475
        runtime_pattern = {"{default}": {"type": "MemoryDataset"}}
        if include_default:
            catalog.config_resolver.add_runtime_patterns(runtime_pattern)

        explicit_datasets = catalog.config_resolver.config
        pipeline_datasets = set()

        for pipe in pipelines.keys():
            pl_obj = pipelines.get(pipe)
            if pl_obj:
                pipeline_datasets.update(pl_obj.datasets())

        for ds_name in pipeline_datasets:
            # TODO: when breaking change replace with is_parameter from kedro/io/core.py
            if (
                ds_name in catalog.config_resolver.config
                or ds_name.startswith("params:")
                or ds_name == "parameters"
            ):
                continue

            ds_config = catalog.config_resolver.resolve_pattern(ds_name)
            if ds_config:
                explicit_datasets[ds_name] = ds_config

        if include_default:
            catalog.config_resolver.remove_runtime_patterns(runtime_pattern)

        return explicit_datasets
