"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kedro.config import MissingConfigException
from kedro.config.omegaconf_config import OmegaConfigLoader
from kedro.framework.project import settings
from kedro.inspection.models import DatasetSnapshot, ProjectMetadataSnapshot
from kedro.io.catalog_config_resolver import CatalogConfigResolver

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.framework.startup import ProjectMetadata


def _build_project_metadata_snapshot(
    metadata: ProjectMetadata,
) -> ProjectMetadataSnapshot:
    """Build `ProjectMetadataSnapshot` from `ProjectMetadata` NamedTuple.

    Args:
        metadata: Project metadata NamedTuple.

    Returns:
        Read-only snapshot of the project's metadata.
    """
    return ProjectMetadataSnapshot(
        project_name=metadata.project_name,
        package_name=metadata.package_name,
        kedro_version=metadata.kedro_init_version,
    )


def _is_parameter(name: str) -> bool:
    """Check whether a dataset name refers to parameters.

    Args:
        name: Dataset name to check.

    Returns:
        ``True`` if the name is ``"parameters"`` or starts with ``"params:"``.
    """
    return name == "parameters" or name.startswith("params:")


def _make_config_loader(project_path: Path, env: str) -> OmegaConfigLoader:
    """Create an ``OmegaConfigLoader`` for the given project and environment.

    Args:
        project_path: Root directory of the Kedro project.
        env: Configuration environment to load.

    Returns:
        Configured ``OmegaConfigLoader`` instance.
    """
    conf_source = str(project_path / settings.CONF_SOURCE)
    return OmegaConfigLoader(
        conf_source=conf_source, env=env, **settings.CONFIG_LOADER_ARGS
    )


def _load_config_section(config_loader: OmegaConfigLoader, key: str) -> dict[str, Any]:
    """Load a configuration section, returning an empty dict when absent."""
    try:
        return config_loader[key]
    except (KeyError, MissingConfigException):
        return {}


def _flatten_parameter_keys(params: dict[str, Any], prefix: str = "") -> list[str]:
    """Recursively collect parameter keys in ``params:`` notation.

    Args:
        params: Parameters dictionary to flatten.
        prefix: Current dotted key prefix.

    Returns:
        List of ``"params:..."`` keys.
    """
    keys: list[str] = []
    for param_name, param_value in params.items():
        full_key = f"{prefix}.{param_name}" if prefix else param_name
        keys.append(f"params:{full_key}")
        if isinstance(param_value, dict):
            keys.extend(_flatten_parameter_keys(param_value, full_key))
    return keys


def _build_catalog_snapshot(
    project_path: Path, env: str
) -> tuple[dict[str, DatasetSnapshot], list[str]]:
    """Build dataset snapshots and parameter keys from project configuration.

    Args:
        project_path: Root directory of the Kedro project.
        env: Configuration environment to load.

    Returns:
        A tuple of (datasets dict, sorted parameter keys).
    """
    config_loader = _make_config_loader(project_path, env)
    conf_catalog = _load_config_section(config_loader, "catalog")
    conf_creds = _load_config_section(config_loader, "credentials")

    # Resolve catalog entries
    datasets: dict[str, DatasetSnapshot] = {}
    if conf_catalog:
        resolver = CatalogConfigResolver(
            config=conf_catalog,
            credentials=conf_creds,
            default_runtime_patterns={},
        )
        for ds_name, ds_config in resolver.config.items():
            datasets[ds_name] = DatasetSnapshot(
                name=ds_name,
                type=ds_config.get("type", ""),
                filepath=ds_config.get("filepath"),
            )

    params = _load_config_section(config_loader, "parameters")
    parameter_keys: list[str] = []
    if params:
        parameter_keys.append("parameters")
        parameter_keys.extend(_flatten_parameter_keys(params))
        parameter_keys.sort()

    return datasets, parameter_keys
