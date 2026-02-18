"""CLI command for `kedro inspect`: export project snapshot as JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

from kedro.inspection import get_snapshot

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata
    from kedro.inspection.models import ProjectSnapshot

DEFAULT_OUTPUT_FILE = "inspect_snapshot.json"


def _resolve_output_path(
    output: Path | None, project_path: Path, default_name: str
) -> Path:
    out_path = output if output is not None else Path(project_path) / default_name
    out_path = Path(out_path)
    if not out_path.is_absolute():
        out_path = Path(project_path) / out_path
    return out_path


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
    help=f"Output file path. Default: {DEFAULT_OUTPUT_FILE} in project root for full snapshot.",
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
    """Export project snapshot as JSON (Kedro-native structure, no project deps required)."""
    if metadata is None:
        raise click.UsageError(
            "Not in a Kedro project. Run this from the project root (where pyproject.toml is)."
        )
    ctx.ensure_object(dict)
    ctx.obj["metadata"] = metadata
    ctx.obj["output"] = output
    ctx.obj["env"] = env or "local"
    if ctx.invoked_subcommand is None:
        ctx.invoke(full_snapshot)


@inspect.command("full", hidden=True)
@click.pass_context
def full_snapshot(ctx: click.Context) -> None:
    """Export full project snapshot (default when no subcommand is given)."""
    metadata = ctx.obj["metadata"]
    output = ctx.obj["output"]
    env = ctx.obj["env"]
    project_path = metadata.project_path
    out_path = _resolve_output_path(output, project_path, DEFAULT_OUTPUT_FILE)

    click.echo(f"Inspecting project at {project_path}...")
    snapshot = get_snapshot(project_path, env=env)
    out_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Snapshot written to {out_path}")
    _warn_missing_deps(snapshot)


@inspect.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Default: inspect_metadata.json in project root.",
)
@click.option(
    "--env",
    "-e",
    type=str,
    default=None,
    help="Kedro environment name. Default: local.",
)
@click.pass_obj
def metadata_cmd(obj: dict, output: Path | None, env: str | None) -> None:
    """Export only project metadata (project_name, package_name, paths, etc.)."""
    metadata = obj["metadata"]
    project_path = metadata.project_path
    out_path = _resolve_output_path(
        output or obj.get("output"), project_path, "inspect_metadata.json"
    )

    click.echo(f"Inspecting project at {project_path}...")
    snapshot = get_snapshot(project_path, env=env or obj["env"])
    data = snapshot.metadata.model_dump()
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    click.echo(f"Metadata written to {out_path}")
    _warn_missing_deps(snapshot)


@inspect.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Default: inspect_pipelines.json in project root.",
)
@click.option(
    "--env",
    "-e",
    type=str,
    default=None,
    help="Kedro environment name. Default: local.",
)
@click.pass_obj
def pipelines(obj: dict, output: Path | None, env: str | None) -> None:
    """Export only pipelines (and nodes) information."""
    metadata = obj["metadata"]
    project_path = metadata.project_path
    out_path = _resolve_output_path(
        output or obj.get("output"), project_path, "inspect_pipelines.json"
    )

    click.echo(f"Inspecting project at {project_path}...")
    snapshot = get_snapshot(project_path, env=env or obj["env"])
    data = {"pipelines": [p.model_dump() for p in snapshot.pipelines]}
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    click.echo(f"Pipelines written to {out_path}")
    _warn_missing_deps(snapshot)


@inspect.command()
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
    """Export datasets and parameters catalog information."""
    metadata = obj["metadata"]
    project_path = metadata.project_path
    out_path = _resolve_output_path(
        output or obj.get("output"), project_path, "inspect_datasets.json"
    )

    click.echo(f"Inspecting project at {project_path}...")
    snapshot = get_snapshot(project_path, env=env or obj["env"])
    data = {
        "datasets": {k: v.model_dump() for k, v in snapshot.datasets.items()},
        "parameters": snapshot.parameters,
    }
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    click.echo(f"Datasets and parameters written to {out_path}")
    _warn_missing_deps(snapshot)
