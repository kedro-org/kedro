"""Helper utilities for assembling Kedro inspection snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from parse import parse

from kedro.config import MissingConfigException
from kedro.framework.project import settings
from kedro.inspection.models import DatasetSnapshot
from kedro.io.catalog_config_resolver import CatalogConfigResolver

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.config import AbstractConfigLoader
    from kedro.inspection.models import PipelineSnapshot


def _make_config_loader(project_path: Path) -> AbstractConfigLoader:
    """Instantiate the project's configured config loader.

    Args:
        project_path: Absolute path to the project root directory.

    Returns:
        An initialised config loader instance.
    """
    conf_source = str(project_path / settings.CONF_SOURCE)
    config_loader_class = settings.CONFIG_LOADER_CLASS
    return config_loader_class(  # type: ignore[no-any-return]
        conf_source=conf_source,
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
    datasets: dict[str, DatasetSnapshot],
    pipelines: list[PipelineSnapshot],
) -> dict[str, DatasetSnapshot]:
    """Enrich the datasets mapping with concrete entries derived from factory patterns.

    Args:
        datasets: Mapping of dataset name (or factory pattern) to its snapshot,
            as returned by ``_build_dataset_snapshots``.
        pipelines: List of pipeline snapshots whose node inputs/outputs are inspected.

    Returns:
        A new mapping that contains all original entries plus any newly resolved
        concrete dataset entries derived from factory patterns.
    """
    factory_patterns = {
        ds_key: ds_value
        for ds_key, ds_value in datasets.items()
        if CatalogConfigResolver.is_pattern(ds_key)
    }
    if not factory_patterns:
        return datasets

    # Collect every concrete dataset name referenced across all pipeline nodes.
    pipeline_ds_names: set[str] = set()
    for pipeline_snapshot in pipelines:
        for node_snapshot in pipeline_snapshot.nodes:
            pipeline_ds_names.update(node_snapshot.inputs)
            pipeline_ds_names.update(node_snapshot.outputs)

    # Sort patterns using the same specificity rules as CatalogConfigResolver
    sorted_factory_patterns = sorted(
        factory_patterns.items(),
        key=lambda item: (
            -CatalogConfigResolver._pattern_specificity(item[0]),
            -item[0].count("{"),
            item[0],
        ),
    )

    result = dict(datasets)

    for ds_name in pipeline_ds_names:
        if ds_name in result:
            continue  # direct catalog entry

        for pattern, pattern_snapshot in sorted_factory_patterns:
            parsed = parse(pattern, ds_name)
            if parsed is None:
                continue

            # Interpolate the filepath template if present.
            resolved_filepath: str | None = None
            if pattern_snapshot.filepath:
                try:
                    resolved_filepath = pattern_snapshot.filepath.format_map(
                        parsed.named
                    )
                except KeyError:
                    resolved_filepath = pattern_snapshot.filepath

            result[ds_name] = DatasetSnapshot(
                name=ds_name,
                type=pattern_snapshot.type,
                filepath=resolved_filepath,
            )
            break  # use the first (most specific) matching pattern

    return result
