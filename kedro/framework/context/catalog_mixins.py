import logging
from collections.abc import Iterable
from typing import Any

from kedro.framework.project import pipelines as _pipelines
from kedro.io import DataCatalog
from kedro.io.core import is_parameter
from kedro.pipeline import Pipeline


class CatalogCommandsMixin:
    """
    A mixin class that provides additional commands for interacting with the `DataCatalog`.

    This class adds methods to list datasets, dataset patterns and resolve dataset patterns.
    It is designed to extend the functionality of the `DataCatalog` for better
    integration with Kedro pipelines.

    Methods:
        - list_datasets: Show datasets per type for specified pipelines.
        - list_patterns: List all dataset factories in the catalog.
        - resolve_patterns: Resolve dataset factories against pipeline datasets.

    Usage:
    You can integrate this mixin with the `DataCatalog` in two ways:

    1. Using `compose_classes`:
        >>> from kedro.io import DataCatalog
        >>> from kedro.framework.context.catalog_mixins import CatalogCommandsMixin
        >>> from kedro.framework.context import compose_classes
        >>> # DataCatalog instance without CatalogCommandsMixin
        >>> assert not hasattr(DataCatalog(), "list_datasets")
        >>>
        >>> # Compose a new class combining DataCatalog and CatalogCommandsMixin
        >>> catalog_class = compose_classes(DataCatalog, CatalogCommandsMixin)
        >>>
        >>> # Create a catalog instance from configuration
        >>> catalog = catalog_class.from_config(
        ...     {
        ...         "cars": {
        ...             "type": "pandas.CSVDataset",
        ...             "filepath": "cars.csv",
        ...             "save_args": {"index": False},
        ...         }
        ...     }
        ... )
        >>>
        >>> # Assert that the catalog has the `list_datasets` method
        >>> assert hasattr(
        ...     catalog, "list_datasets"
        ... ), "list_datasets method is not available"
        >>> print("list_datasets method is available!")
        # list_datasets method is available!

    2. Creating a new class with inheritance:
        >>> from kedro.io import DataCatalog
        >>> from kedro.framework.context.catalog_mixins import CatalogCommandsMixin
        >>>
        >>> class DataCatalogWithMixins(DataCatalog, CatalogCommandsMixin):
        ...     pass
        >>>
        >>> catalog = DataCatalogWithMixins(datasets={"example": MemoryDataset()})
        >>> assert hasattr(
        ...     catalog, "list_datasets"
        ... ), "list_datasets method is not available"
        >>> print("list_datasets method is available!")
        # list_datasets method is available!
    """

    @property
    def _logger(self) -> logging.Logger: ...  # type: ignore[empty-body]

    def list_datasets(
        self: DataCatalog, pipelines: list[str] | list[Pipeline] | None = None
    ) -> dict:
        """
        Show datasets grouped by type for the specified pipelines.

        This method lists datasets used in the specified pipelines, categorizing them
        into three groups:
        - `datasets`: Datasets explicitly defined in the catalog.
        - `factories`: Datasets resolved from patterns.
        - `defaults`: Datasets that do not match any pattern or explicit definition.

        Args:
            pipelines (list[str] | list[Pipeline] | None): A list of pipeline names or
                `Pipeline` objects to analyze. If `None`, all pipelines are analyzed.

        Returns:
            dict: A dictionary where keys are pipeline names and values are dictionaries
            containing datasets grouped by type.
        """
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

    def list_patterns(self: DataCatalog) -> list[str]:
        """
        List all dataset factories in the catalog, ranked by priority.

        This method retrieves all dataset factories (patterns) defined in the catalog,
        ordered by the priority in which they are matched.

        Returns:
            list[str]: A list of dataset factory patterns.
        """
        return self.config_resolver.list_patterns()

    def resolve_patterns(
        self: DataCatalog,
        pipelines: list[Pipeline] | None = None,
    ) -> dict[str, Any]:
        """
        Resolve dataset factories against pipeline datasets.

        This method resolves dataset patterns for datasets used in the specified pipelines.
        It includes datasets explicitly defined in the catalog as well as those resolved
        from patterns.

        Args:
            pipelines (list[Pipeline] | None): A list of `Pipeline` objects to analyze.
                If `None`, all pipelines are analyzed.

        Returns:
            dict[str, Any]: A dictionary mapping dataset names to their unresolved configurations.
        """
        target_pipelines = pipelines or _pipelines.keys()

        pipeline_datasets: set[str] = set()
        for pipe in target_pipelines:
            pl_obj = _pipelines.get(pipe) if isinstance(pipe, str) else pipe
            if pl_obj:
                pipeline_datasets.update(pl_obj.datasets())

        # We need to include datasets defined in the catalog.yaml and datasets added manually to the catalog
        explicit_datasets = {}
        for ds_name, ds in self.items():
            if is_parameter(ds_name):
                continue

            unresolved_config, _ = self.config_resolver._unresolve_credentials(
                ds_name, ds.to_config()
            )
            explicit_datasets[ds_name] = unresolved_config

        for ds_name in pipeline_datasets:
            if ds_name in explicit_datasets or is_parameter(ds_name):
                continue

            ds_config = self.config_resolver.resolve_pattern(ds_name)
            if ds_config:
                unresolved_config, _ = self.config_resolver._unresolve_credentials(
                    ds_name, ds_config
                )
                explicit_datasets[ds_name] = unresolved_config

        return explicit_datasets


def _group_ds_by_type(datasets: set[str], catalog: DataCatalog) -> dict[str, list[str]]:
    """
    Group datasets by their type.

    This utility function groups datasets into a dictionary where the keys are
    dataset types (as strings) and the values are lists of dataset names.

    Args:
        datasets (set[str]): A set of dataset names to group.
        catalog (DataCatalog): The `DataCatalog` instance to retrieve dataset types.

    Returns:
        dict[str, list[str]]: A dictionary mapping dataset types to lists of dataset names.

    Example:
        >>> from kedro.io.data_catalog import DataCatalog
        >>> from kedro.io.memory_dataset import MemoryDataset
        >>> from kedro.framework.context.catalog_mixins import _group_ds_by_type
        >>> catalog = DataCatalog(datasets={"example": MemoryDataset()})
        >>> datasets = {"example"}
        >>> _group_ds_by_type(datasets, catalog)
        # {'kedro.io.memory_dataset.MemoryDataset': ['example']}
    """
    mapping: dict[str, list[str]] = {}
    for ds_name in datasets:
        if is_parameter(ds_name):
            continue

        str_type = catalog.get_type(ds_name)
        if str_type not in mapping:
            mapping[str_type] = []

        mapping[str_type].append(ds_name)

    return mapping
