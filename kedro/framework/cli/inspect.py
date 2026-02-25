"""CLI commands for `kedro inspect`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata
    from kedro.inspection.models import ProjectSnapshot

DEFAULT_OUTPUT_FILE = "inspect_snapshot.json"


def _resolve_output_path(
    output: Path | None, project_path: Path, default_name: str
) -> Path:
    out_path = output if output is not None else project_path / default_name
    if not Path(out_path).is_absolute():
        out_path = project_path / out_path
    return Path(out_path)


def _warn_missing_deps(snapshot: ProjectSnapshot) -> None:
    if snapshot.has_missing_deps:
        click.secho(
            "Warning: Some project dependencies were mocked (has_missing_deps=true).",
            fg="yellow",
        )
        if snapshot.mocked_dependencies:
            click.secho(
                f"Mocked: {', '.join(snapshot.mocked_dependencies)}",
                fg="yellow",
            )


@click.group(name="inspect", invoke_without_command=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help=f"Output file path. Default: {DEFAULT_OUTPUT_FILE} in project root.",
)
@click.option(
    "--env",
    "-e",
    type=str,
    default=None,
    help="Kedro environment name. Default: local.",
)
@click.pass_obj
@click.pass_context
def inspect(
    ctx: click.Context,
    metadata: ProjectMetadata | None,
    output: Path | None,
    env: str | None,
) -> None:
    """Inspect a Kedro project and export structural information as JSON."""
    if metadata is None:
        raise click.UsageError(
            "Not in a Kedro project. Run this from the project root (where pyproject.toml is)."
        )
    ctx.ensure_object(dict)
    ctx.obj["metadata"] = metadata
    ctx.obj["output"] = output
    ctx.obj["env"] = env or "local"
    if ctx.invoked_subcommand is None:
        ctx.invoke(snapshot)


@inspect.command("snapshot", hidden=True)
@click.pass_context
def snapshot(ctx: click.Context) -> None:
    """Export full project snapshot (default when no subcommand is given)."""
    from kedro.inspection import get_snapshot

    metadata = ctx.obj["metadata"]
    project_path = metadata.project_path
    env = ctx.obj["env"]
    out_path = _resolve_output_path(
        ctx.obj["output"], project_path, DEFAULT_OUTPUT_FILE
    )

    click.echo(f"Inspecting project at {project_path}...")
    snap = get_snapshot(project_path, env=env)
    out_path.write_text(snap.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Snapshot written to {out_path}")


@inspect.command("metadata")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Default: inspect_metadata.json in project root.",
)
@click.pass_obj
def metadata_cmd(obj: dict, output: Path | None) -> None:
    """Export project metadata (project_name, package_name, kedro_version).

    Reads pyproject.toml only — no pipeline imports, no catalog loading.
    """
    from kedro.inspection.snapshot import build_metadata_snapshot

    metadata = obj["metadata"]
    out_path = _resolve_output_path(
        output or obj.get("output"), metadata.project_path, "inspect_metadata.json"
    )

    snap = build_metadata_snapshot(metadata)
    out_path.write_text(json.dumps(snap.model_dump(), indent=2), encoding="utf-8")
    click.echo(f"Metadata written to {out_path}")


@inspect.command("datasets")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Default: inspect_datasets.json in project root.",
)
@click.option(
    "--env",
    "-e",
    type=str,
    default=None,
    help="Kedro environment name. Default: local.",
)
@click.pass_obj
def datasets(obj: dict, output: Path | None, env: str | None) -> None:
    """Export dataset types and parameter keys from catalog.yml.

    Reads catalog.yml and parameters.yml only — no pipeline imports required.
    """
    from kedro.inspection.snapshot import build_catalog_snapshot

    metadata = obj["metadata"]
    project_path = metadata.project_path
    out_path = _resolve_output_path(
        output or obj.get("output"), project_path, "inspect_datasets.json"
    )

    ds_map, parameter_keys = build_catalog_snapshot(project_path, env or obj["env"])
    data = {
        "datasets": {
            k: v.model_dump(exclude={"is_free_input"}) for k, v in ds_map.items()
        },
        "parameter_keys": parameter_keys,
    }
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    click.echo(f"Datasets written to {out_path}")


@inspect.command("pipelines")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Default: inspect_pipelines.json in project root.",
)
@click.pass_obj
def pipelines(obj: dict, output: Path | None) -> None:
    """Export pipeline and node structure.

    Executes register_pipelines() — requires project dependencies to be installed.
    """
    from kedro.inspection.snapshot import build_pipeline_snapshots

    metadata = obj["metadata"]
    out_path = _resolve_output_path(
        output or obj.get("output"), metadata.project_path, "inspect_pipelines.json"
    )

    pipeline_snapshots = build_pipeline_snapshots()
    data = {"pipelines": [p.model_dump() for p in pipeline_snapshots]}
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    click.echo(f"Pipelines written to {out_path}")
