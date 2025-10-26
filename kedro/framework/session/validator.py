"""Parameter validation for Kedro sessions."""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any, get_type_hints

from kedro.framework.hooks import hook_impl


class KedroValidationHook:
    """Validate params against dataclasses or Pydantic models referenced by node functions."""

    def __init__(self):
        self.validated_models = {}

    def _get_nested_param(self, params: dict[str, Any], param_key: str) -> Any:
        """Get parameter value supporting nested paths"""
        if "." not in param_key:
            return params.get(param_key)

        keys = param_key.split(".")
        value = params
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    @hook_impl
    def after_context_created(self, context) -> None:
        """
        Runs early — context.params is available.
        It inspects pipeline nodes, finds inputs of the form "params:<key>"
        and validates them against function annotations.
        """
        params: dict[str, Any] = context.params
        try:
            from kedro.framework.project import pipelines
        except Exception:
            pipelines = {}

        problems = []

        for pipeline_name, pipeline in (
            pipelines.items()
            if hasattr(pipelines, "items")
            else getattr(pipelines, "__dict__", {}).items()
        ):
            for node in getattr(pipeline, "nodes", []):
                func = getattr(node, "func", None)
                if func is None:
                    continue
                sig = inspect.signature(func)
                type_hints = get_type_hints(func, include_extras=False)

                dataset_to_arg = {}
                node_inputs = getattr(node, "inputs", None)
                if isinstance(node_inputs, dict):
                    dataset_to_arg.update(node_inputs)
                elif isinstance(node_inputs, list) or isinstance(node_inputs, tuple):
                    param_names = list(sig.parameters.keys())
                    for idx, ds in enumerate(node_inputs):
                        if idx < len(param_names):
                            dataset_to_arg[ds] = param_names[idx]

                # Inspect params:* dataset inputs
                for ds_name, arg_name in dataset_to_arg.items():
                    if not isinstance(ds_name, str):
                        continue
                    if not ds_name.startswith("params:"):
                        continue

                    # extract param key (strip prefix)
                    param_key = ds_name.split(":", 1)[1]

                    # support nested lookups like "params:project.database" -> context.params['project']['database']
                    raw_value = self._get_nested_param(params, param_key)
                    if raw_value is None:
                        # If param absent, collect problem (could be optional)
                        problems.append(
                            {
                                "node": node.name
                                or getattr(func, "__name__", "<unknown>"),
                                "pipeline": pipeline_name,
                                "param_key": param_key,
                                "error": "missing parameter",
                            }
                        )
                        continue

                    # find expected type for arg_name
                    expected = type_hints.get(arg_name)
                    if expected is None:
                        # no annotation — skip or optionally warn
                        continue

                    # handle pydantic models
                    try:
                        import pydantic

                        BaseModel = pydantic.BaseModel
                    except Exception:
                        BaseModel = None

                    try:
                        if (
                            BaseModel
                            and inspect.isclass(expected)
                            and issubclass(expected, BaseModel)
                        ):
                            # instantiate/validate
                            try:
                                validated_instance = expected.model_validate(raw_value)
                                # Store the validated model instance
                                self.validated_models[param_key] = validated_instance
                            except Exception as exc:
                                problems.append(
                                    {
                                        "node": node.name
                                        or getattr(func, "__name__", "<unknown>"),
                                        "pipeline": pipeline_name,
                                        "param_key": param_key,
                                        "error": f"pydantic validation failed: {exc}",
                                    }
                                )
                        elif dataclasses.is_dataclass(expected):
                            # For dataclasses: try to instantiate
                            try:
                                validated_instance = expected(
                                    **(raw_value if isinstance(raw_value, dict) else {})
                                )
                                # Store the validated dataclass instance
                                self.validated_models[param_key] = validated_instance
                            except Exception as exc:
                                problems.append(
                                    {
                                        "node": node.name
                                        or getattr(func, "__name__", "<unknown>"),
                                        "pipeline": pipeline_name,
                                        "param_key": param_key,
                                        "error": f"dataclass instantiation failed: {exc}",
                                    }
                                )
                        else:
                            # typed dicts or plain dicts only for static checking.
                            # [TODO: Not sure if the plugin should do anything here]
                            pass
                    except Exception as exc:
                        problems.append(
                            {
                                "node": node.name
                                or getattr(func, "__name__", "<unknown>"),
                                "pipeline": pipeline_name,
                                "param_key": param_key,
                                "error": f"unexpected error during validation: {exc}",
                            }
                        )

        if problems:
            # Format a message and raise so Kedro CLI fails fast
            lines = ["Parameter validation failed:"]
            for p in problems:
                lines.append(
                    f"- pipeline={p['pipeline']} node={p['node']} param={p['param_key']}: {p['error']}"
                )
            raise RuntimeError("\n".join(lines))

    @hook_impl
    def before_node_run(self, node, catalog, inputs, is_async, run_id):
        """Replace parameter inputs with validated model instances if available."""
        if not hasattr(node, "inputs") or not node.inputs or not inputs:
            return inputs

        # Create a copy of inputs to modify
        modified_inputs = dict(inputs)
        inputs_changed = False

        # For parameter datasets, replace the raw value with validated model instance
        for input_key, input_value in list(modified_inputs.items()):
            # Check if this input corresponds to a parameter dataset
            if isinstance(input_key, str) and input_key.startswith("params:"):
                param_key = input_key.split(":", 1)[1]
                if param_key in self.validated_models:
                    modified_inputs[input_key] = self.validated_models[param_key]
                    inputs_changed = True

        return modified_inputs if inputs_changed else inputs
