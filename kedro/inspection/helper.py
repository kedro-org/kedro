"""Helper utilities for assembling Kedro inspection snapshots."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from kedro.config import MissingConfigException
from kedro.framework.project import settings
from kedro.inspection.models import DatasetSnapshot
from kedro.io.catalog_config_resolver import CatalogConfigResolver

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.config import AbstractConfigLoader
    from kedro.inspection.models import PipelineSnapshot


def _make_config_loader(
    project_path: Path,
    env: str | None = None,
    conf_source: str | None = None,
) -> AbstractConfigLoader:
    """Instantiate the project's configured config loader.

    Args:
        project_path: Absolute path to the project root directory.
        env: Optional run environment override (e.g. ``"staging"``).
            When ``None`` the default run environment from
            ``CONFIG_LOADER_ARGS`` is used.
        conf_source: Optional path to the configuration directory.
            When ``None``, defaults to ``<project_path>/<settings.CONF_SOURCE>``.

    Returns:
        An initialised config loader instance.
    """
    resolved_conf_source = (
        conf_source
        if conf_source is not None
        else str(project_path / settings.CONF_SOURCE)
    )
    config_loader_class = settings.CONFIG_LOADER_CLASS
    return config_loader_class(  # type: ignore[no-any-return]
        conf_source=resolved_conf_source,
        env=env,
        **settings.CONFIG_LOADER_ARGS,
    )


def _get_parameter_keys(config_loader: AbstractConfigLoader) -> list[str]:
    """Return sorted parameter key strings from the project configuration.

    Args:
        config_loader: Config loader instance.

    Returns:
        Sorted list of top-level parameter key strings.
        Returns an empty list when no parameters configuration is found.
    """
    try:
        params: dict = config_loader["parameters"]
    except (KeyError, MissingConfigException):
        return []
    return sorted(params.keys())


def _resolve_factory_patterns(
    catalog_config: dict[str, Any],
    datasets: dict[str, DatasetSnapshot],
    pipelines: list[PipelineSnapshot],
) -> dict[str, DatasetSnapshot]:
    """Enrich the datasets mapping with concrete entries derived from factory patterns.

    Args:
        catalog_config: Raw catalog configuration dict, used to extract factory
            pattern configs for full placeholder interpolation.
        datasets: Mapping of dataset name (or factory pattern) to its snapshot,
            as returned by ``_build_dataset_snapshots``.
        pipelines: List of pipeline snapshots whose node inputs/outputs are inspected.

    Returns:
        A new mapping containing only concrete dataset entries
    """
    pattern_configs = {
        name: config
        for name, config in catalog_config.items()
        if CatalogConfigResolver.is_pattern(name)
    }
    if not pattern_configs:
        return datasets

    sorted_patterns = CatalogConfigResolver._sort_patterns(pattern_configs)

    # Collect every concrete dataset name referenced across all pipeline nodes.
    pipeline_ds_names: set[str] = set()
    for pipeline_snapshot in pipelines:
        for node_snapshot in pipeline_snapshot.nodes:
            pipeline_ds_names.update(node_snapshot.inputs)
            pipeline_ds_names.update(node_snapshot.outputs)

    # Start from non-pattern entries
    result = {
        name: snap
        for name, snap in datasets.items()
        if not CatalogConfigResolver.is_pattern(name)
    }

    for ds_name in pipeline_ds_names:
        if ds_name in result:
            continue  # direct catalog entry

        matched = next(
            CatalogConfigResolver._get_matches(sorted_patterns, ds_name), None
        )
        if matched is None:
            continue

        resolved_config = CatalogConfigResolver._resolve_dataset_config(
            ds_name, matched, copy.deepcopy(sorted_patterns[matched])
        )

        result[ds_name] = DatasetSnapshot.from_config(ds_name, resolved_config)

    return result
