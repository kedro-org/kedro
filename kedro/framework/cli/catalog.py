"""A collection of CLI commands for working with Kedro catalog."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import yaml
from click import secho

from kedro.framework.cli.utils import env_option, split_string
from kedro.framework.session import KedroSession

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata


def _create_session(package_name: str, **kwargs: Any) -> KedroSession:
    kwargs.setdefault("save_on_close", False)
    return KedroSession.create(**kwargs)


@click.group(name="kedro")
def catalog_cli() -> None:  # pragma: no cover
    pass


@catalog_cli.group()
def catalog() -> None:
    """Commands for working with catalog."""


@catalog.command("describe-datasets")
@env_option
@click.option(
    "--pipeline",
    "-p",
    type=str,
    default="",
    help="Name of the modular pipeline to run. If not set, "
    "the project pipeline is run by default.",
    callback=split_string,
)
@click.pass_obj
def describe_datasets(metadata: ProjectMetadata, pipeline: str, env: str) -> None:
    """
    Describe datasets used in the specified pipelines, grouped by type.\n

    This command provides a structured overview of datasets used in the selected pipelines,
    categorizing them into three groups:\n
    - `datasets`: Datasets explicitly defined in the catalog.\n
    - `factories`: Datasets resolved from dataset factory patterns.\n
    - `defaults`: Datasets that do not match any pattern or explicit definition.\n
    """
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    p = pipeline or None
    datasets_dict = context.catalog.describe_datasets(p)  # type: ignore

    secho(yaml.dump(datasets_dict))


@catalog.command("list-patterns")
@env_option
@click.pass_obj
def list_patterns(metadata: ProjectMetadata, env: str) -> None:
    """
    List all dataset factory patterns in the catalog, ranked by priority.

    This method retrieves all dataset factory patterns defined in the catalog,
    ordered by the priority in which they are matched.
    """
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    click.echo(yaml.dump(context.catalog.list_patterns()))  # type: ignore


@catalog.command("resolve-patterns")
@env_option
@click.option(
    "--pipeline",
    "-p",
    type=str,
    default="",
    help="Name of the modular pipeline to run. If not set, "
    "the project pipeline is run by default.",
    callback=split_string,
)
@click.pass_obj
def resolve_patterns(metadata: ProjectMetadata, pipeline: str, env: str) -> None:
    """
    Resolve dataset factory patterns against pipeline datasets.

    This method resolves dataset factory patterns for datasets used in the specified pipelines.
    It includes datasets explicitly defined in the catalog as well as those resolved
    from dataset factory patterns.
    """
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    p = pipeline or None
    datasets_dict = context.catalog.resolve_patterns(p)  # type: ignore

    secho(yaml.dump(datasets_dict))


@catalog.command("create-params")
@env_option
@click.option(
    "--filepath",
    "-f",
    type=click.Path(),
    help="Path to create the parameters file. If not specified, will auto-generate based on pipeline usage.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing parameter file if it exists.",
)
@click.pass_obj
def create_params(
    metadata: ProjectMetadata, env: str, filepath: str | None, overwrite: bool
) -> None:
    """
    Generate parameter files from node function type hints and default values.

    This command analyzes all pipeline nodes to extract parameter type hints and default values,
    then generates YAML parameter files. The file location is determined by:

    - If --filepath is provided: Use the specified path
    - If parameter is used in a single pipeline: conf/base/parameters_{pipeline_name}.yml
    - If parameter is used in multiple pipelines: conf/base/parameters.yml

    Examples:
        kedro catalog create-params
        kedro catalog create-params --filepath conf/base/my_params.yml
        kedro catalog create-params --overwrite
    """

    from collections import defaultdict
    from typing import get_type_hints

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    # Import pipelines
    try:
        from kedro.framework.project import pipelines
    except Exception:
        secho("No pipelines found in the project.", fg="yellow")
        return

    # Extract parameters from all nodes
    param_info = defaultdict(
        lambda: {
            "type_hint": None,
            "default_value": None,
            "pipelines": set(),
            "description": None,
        }
    )

    # Process all pipelines and nodes
    pipeline_dict = dict(pipelines)

    for pipeline_name, pipeline in pipeline_dict.items():
        if pipeline_name == "__default__":
            continue

        nodes = getattr(pipeline, "nodes", [])

        for node in nodes:
            func = getattr(node, "func", None)
            if func is None:
                continue

            sig = inspect.signature(func)
            type_hints = get_type_hints(func, include_extras=False)

            # Map dataset names to function argument names
            dataset_to_arg = {}
            node_inputs = getattr(node, "inputs", None)

            if isinstance(node_inputs, dict):
                dataset_to_arg.update(node_inputs)
            elif isinstance(node_inputs, (list, tuple)):
                param_names = list(sig.parameters.keys())
                for idx, ds in enumerate(node_inputs):
                    if idx < len(param_names):
                        dataset_to_arg[ds] = param_names[idx]

            # Process params:* inputs
            for ds_name, arg_name in dataset_to_arg.items():
                if not isinstance(ds_name, str) or not ds_name.startswith("params:"):
                    continue

                param_key = ds_name.split(":", 1)[1]
                param_info[param_key]["pipelines"].add(pipeline_name)

                # Get type hint
                if arg_name in type_hints:
                    param_info[param_key]["type_hint"] = type_hints[arg_name]

                # Get default value from function signature
                if arg_name in sig.parameters:
                    param = sig.parameters[arg_name]
                    if param.default != inspect.Parameter.empty:
                        param_info[param_key]["default_value"] = param.default

                # Add description from docstring if available
                if func.__doc__ and not param_info[param_key]["description"]:
                    param_info[param_key]["description"] = (
                        f"Parameter for {func.__name__}"
                    )

    if not param_info:
        secho("No parameters with type hints found in any pipeline nodes.", fg="yellow")
        return

    # Generate parameter values from type hints and defaults
    generated_params = {}

    for param_key, info in param_info.items():
        # Pass the final field name for heuristics when generating example values
        field_name = param_key.split(".")[-1]
        param_value = _generate_param_value(
            info["type_hint"], info["default_value"], field_name
        )
        if param_value is not None:
            # Handle nested parameter keys like 'project.database'
            _set_nested_param(generated_params, param_key, param_value)

    # Determine output file path
    if filepath:
        output_path = Path(filepath)
    else:
        # Auto-determine based on pipeline usage
        conf_base = Path("conf") / "base"

        # Group parameters by pipeline usage
        single_pipeline_params = {}
        multi_pipeline_params = {}

        for param_key, info in param_info.items():
            if len(info["pipelines"]) == 1:
                pipeline_name = next(iter(info["pipelines"]))
                if pipeline_name not in single_pipeline_params:
                    single_pipeline_params[pipeline_name] = {}
                _set_nested_param(
                    single_pipeline_params[pipeline_name],
                    param_key,
                    _get_nested_param(generated_params, param_key),
                )
            else:
                _set_nested_param(
                    multi_pipeline_params,
                    param_key,
                    _get_nested_param(generated_params, param_key),
                )

        # Create parameter files
        created_files = []

        # Create pipeline-specific parameter files
        for pipeline_name, params in single_pipeline_params.items():
            if params:  # Only create if there are parameters
                pipeline_file = conf_base / f"parameters_{pipeline_name}.yml"
                if _write_param_file(pipeline_file, params, overwrite):
                    created_files.append(str(pipeline_file))

        # Create general parameters file for multi-pipeline params
        if multi_pipeline_params:
            general_file = conf_base / "parameters.yml"
            if _write_param_file(general_file, multi_pipeline_params, overwrite):
                created_files.append(str(general_file))

        if created_files:
            secho("Created parameter files:", fg="green")
            for file_path in created_files:
                secho(f"  - {file_path}", fg="green")
        return

    # Write to specified filepath
    if _write_param_file(output_path, generated_params, overwrite):
        secho(f"Created parameter file: {output_path}", fg="green")


def _default_for_type(
    type_hint: type | None, field_info: Any = None, field_name: str | None = None
) -> Any:
    """Return a simple default value for a given type_hint.

    This respects basic Pydantic field constraints when provided via field_info
    (numeric bounds: ge/gt/le/lt, string min_length/max_length). Otherwise it
    returns a type-consistent zero/empty value.
    """
    from typing import get_args, get_origin

    # Basic fallback when no type hint
    if type_hint is None:
        return ""  # default to empty string when unknown

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Handle Optional/Union by using first non-None
    import typing as _typing

    if origin is _typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _default_for_type(non_none[0], field_info, field_name)
        return ""

    # Lists/Tuples: empty list
    if origin in (list, tuple):
        return []

    # Dicts: empty dict
    if origin is dict:
        return {}

    # Numeric and basic types: consider constraints in field_info if present
    # Extract possible constraints from pydantic field info
    def _extract(finfo: Any, name: str):
        if finfo is None:
            return None
        # For pydantic v2 FieldInfo/ModelField, constraint attributes (ge, gt, min_length, etc.)
        # are available directly on the finfo object. We assume pydantic v2 only.
        return getattr(finfo, name, None)

    if type_hint in (int,):
        ge = _extract(field_info, "ge")
        gt = _extract(field_info, "gt")
        if ge is not None:
            try:
                return int(ge)
            except Exception:
                return 0
        if gt is not None:
            try:
                return int(gt) + 1
            except Exception:
                return 1
        return 0

    if type_hint in (float,):
        ge = _extract(field_info, "ge")
        gt = _extract(field_info, "gt")
        if ge is not None:
            try:
                return float(ge)
            except Exception:
                return 0.0
        if gt is not None:
            try:
                return float(gt) + 1e-6
            except Exception:
                return 1.0
        return 0.0

    if type_hint in (str,):
        min_len = _extract(field_info, "min_length") or _extract(
            field_info, "min_length"
        )
        if min_len:
            try:
                return "a" * int(min_len)
            except Exception:
                return ""
        return ""

    if type_hint is bool:
        return False

    # Fallback for other builtins
    if type_hint is list:
        return []
    if type_hint is dict:
        return {}

    return ""


def _generate_param_value(
    type_hint: type | None,
    default_value: Any,
    field_name: str | None = None,
    field_info: Any = None,
) -> Any:
    """Generate a parameter value from type hint and default value.

    Uses _default_for_type for basic defaults, and recursively expands nested
    Pydantic models and dataclasses. If a default_value is provided, it is used.
    """
    import dataclasses
    from typing import get_args, get_origin

    # If we have a default value, use it
    if default_value is not None and default_value != inspect.Parameter.empty:
        return default_value

    # If no type hint, return a placeholder
    if type_hint is None:
        return "# TODO: Add parameter value"

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    import typing as _typing

    # Handle Optional / Union types: prefer first non-None arg
    if origin is _typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _generate_param_value(non_none[0], None, field_name, field_info)
        return "# TODO: Add parameter value"

    # Handle lists/tuples
    if origin in (list, tuple):
        return []

    # Handle dicts
    if origin is dict:
        return {}

    # Handle Pydantic models (v2: model_fields, v1: __fields__)
    try:
        import pydantic

        BaseModel = pydantic.BaseModel
    except Exception:
        BaseModel = None  # type: ignore

    # Only support pydantic v2: expect `model_fields` on the model class
    if (
        BaseModel is not None
        and inspect.isclass(type_hint)
        and issubclass(type_hint, BaseModel)
    ):
        example = {}
        if hasattr(type_hint, "model_fields"):
            for fname, finfo in type_hint.model_fields.items():
                # finfo typically exposes annotation, default and default_factory in pydantic v2
                ftype = getattr(finfo, "annotation", None)
                if ftype is None and hasattr(type_hint, "__annotations__"):
                    ftype = type_hint.__annotations__.get(fname)

                default = getattr(finfo, "default", pydantic.fields.PydanticUndefined)
                default_factory = getattr(finfo, "default_factory", None)

                if default is not pydantic.fields.PydanticUndefined:
                    example[fname] = default
                elif default_factory is not None:
                    try:
                        example[fname] = default_factory()
                    except Exception:
                        example[fname] = _generate_param_value(
                            ftype, None, fname, finfo
                        )
                else:
                    example[fname] = _generate_param_value(ftype, None, fname, finfo)
        else:
            # If model_fields not present, fall back to annotations only
            for fname, ftype in getattr(type_hint, "__annotations__", {}).items():
                example[fname] = _generate_param_value(ftype, None, fname, None)

        return example

    # Handle dataclasses
    if dataclasses.is_dataclass(type_hint):
        example = {}
        for field in dataclasses.fields(type_hint):
            if field.default != dataclasses.MISSING:
                example[field.name] = field.default
            elif (
                getattr(field, "default_factory", dataclasses.MISSING)
                is not dataclasses.MISSING
            ):
                try:
                    example[field.name] = field.default_factory()
                except Exception:
                    example[field.name] = _generate_param_value(
                        field.type, None, field.name, None
                    )
            else:
                example[field.name] = _generate_param_value(
                    field.type, None, field.name, None
                )
        return example

    # For basic types, use the simple default generator which respects pydantic constraints
    return _default_for_type(type_hint, field_info, field_name)


def _set_nested_param(params_dict: dict[str, Any], param_key: str, value: Any) -> None:
    """Set a nested parameter value using dot notation."""
    if "." not in param_key:
        params_dict[param_key] = value
        return

    keys = param_key.split(".")
    current = params_dict
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _get_nested_param(params_dict: dict[str, Any], param_key: str) -> Any:
    """Get a nested parameter value using dot notation."""
    if "." not in param_key:
        return params_dict.get(param_key)

    keys = param_key.split(".")
    current = params_dict
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _write_param_file(filepath: Path, params: dict[str, Any], overwrite: bool) -> bool:
    """Write parameters to a YAML file.

    Returns:
        bool: True if file was created/overwritten, False if skipped due to existing file.
    """
    # Create directory if it doesn't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists and handle overwrite
    if filepath.exists() and not overwrite:
        secho(
            f"File {filepath} already exists. Use --overwrite to replace it.",
            fg="yellow",
        )
        return False

    # Write YAML file with nice formatting
    with open(filepath, "w") as f:
        f.write("# Auto-generated parameter file from type hints\n")
        f.write("# Generated by: kedro catalog create-params\n")
        f.write("# Please review and update the values as needed\n\n")
        yaml.dump(params, f, default_flow_style=False, sort_keys=False, indent=2)

    return True
