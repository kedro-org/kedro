"""Parameter validation for Kedro sessions."""

from __future__ import annotations

import dataclasses
import inspect
import logging
from typing import Any, get_type_hints

from kedro.framework.hooks import hook_impl


class ParameterModelUtils:
    """Shared utilities for parameter model handling."""

    @staticmethod
    def get_nested_param(params: dict[str, Any], param_key: str) -> Any:
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

    @staticmethod
    def get_node_param_requirements(node) -> dict[str, type]:
        """Extract parameter requirements from node function annotations."""
        func = getattr(node, "func", None)
        if func is None:
            return {}

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

        # Extract params:* dataset inputs and their expected types
        param_requirements = {}
        for ds_name, arg_name in dataset_to_arg.items():
            if not isinstance(ds_name, str) or not ds_name.startswith("params:"):
                continue

            param_key = ds_name.split(":", 1)[1]
            expected_type = type_hints.get(arg_name)
            if expected_type:
                param_requirements[param_key] = expected_type

        return param_requirements

    @staticmethod
    def get_all_pipeline_param_requirements(
        pipelines, include_default: bool = True
    ) -> dict[str, type]:
        """Extract all parameter requirements from all pipelines."""
        all_param_requirements = {}

        pipeline_dict = dict(pipelines)
        for pipeline_name, pipeline in pipeline_dict.items():
            if not include_default and pipeline_name == "__default__":
                continue

            for node in getattr(pipeline, "nodes", []):
                node_requirements = ParameterModelUtils.get_node_param_requirements(
                    node
                )
                all_param_requirements.update(node_requirements)

        return all_param_requirements

    @staticmethod
    def instantiate_model(
        param_key: str,
        raw_value: Any,
        expected_type: type,
        warn_on_failure: bool = False,
    ) -> tuple[Any, str | None]:
        """Instantiate and validate a model from raw parameter value.

        Returns:
            tuple: (validated_instance_or_None, error_message_or_None)
        """
        # Handle pydantic models
        try:
            import pydantic

            BaseModel = pydantic.BaseModel
        except Exception:
            BaseModel = None

        error_msg = None
        try:
            if (
                BaseModel
                and inspect.isclass(expected_type)
                and issubclass(expected_type, BaseModel)
            ):
                # Instantiate/validate pydantic model
                return expected_type.model_validate(raw_value), None
            elif dataclasses.is_dataclass(expected_type):
                # For dataclasses: try to instantiate
                return expected_type(
                    **(raw_value if isinstance(raw_value, dict) else {})
                ), None
            else:
                # Not a supported model type
                return None, f"Unsupported model type: {expected_type}"
        except Exception as exc:
            error_msg = f"Failed to instantiate {expected_type.__name__} for param '{param_key}': {exc}"
            if warn_on_failure:
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Parameter validation warning: {error_msg}. Falling back to raw dictionary."
                )
            return None, error_msg


class KedroParameterHook:
    """Hook for parameter processing that runs always."""

    def __init__(self):
        self.validated_models = {}
        self._context_params = None

    @hook_impl
    def after_context_created(self, context) -> None:
        """Store context params for later use in before_node_run."""
        self._context_params = context.params

    @hook_impl
    def before_node_run(self, node, catalog, inputs, is_async, run_id):
        """Replace parameter inputs with validated model instances if available."""
        if (
            not hasattr(node, "inputs")
            or not node.inputs
            or not inputs
            or not self._context_params
        ):
            return inputs

        # Get parameter requirements for this node
        param_requirements = ParameterModelUtils.get_node_param_requirements(node)
        if not param_requirements:
            return inputs

        # Create a copy of inputs to modify
        modified_inputs = dict(inputs)
        inputs_changed = False

        # For parameter datasets, instantiate models if needed
        for input_key, input_value in list(modified_inputs.items()):
            # Check if this input corresponds to a parameter dataset
            if isinstance(input_key, str) and input_key.startswith("params:"):
                param_key = input_key.split(":", 1)[1]

                # Check if we already have a validated model
                if param_key in self.validated_models:
                    modified_inputs[input_key] = self.validated_models[param_key]
                    inputs_changed = True
                elif param_key in param_requirements:
                    # Try to instantiate the model from raw parameter value
                    raw_value = ParameterModelUtils.get_nested_param(
                        self._context_params, param_key
                    )
                    if raw_value is not None:
                        expected_type = param_requirements[param_key]
                        validated_instance, error_msg = (
                            ParameterModelUtils.instantiate_model(
                                param_key,
                                raw_value,
                                expected_type,
                                warn_on_failure=True,
                            )
                        )
                        if validated_instance is not None:
                            self.validated_models[param_key] = validated_instance
                            modified_inputs[input_key] = validated_instance
                            inputs_changed = True
                        # If instantiation failed, warning was already logged, continue with raw value

        return modified_inputs if inputs_changed else inputs


class KedroValidationHook:
    """Validate params against dataclasses or Pydantic models referenced by node functions."""

    def __init__(self, parameter_hook: KedroParameterHook | None = None):
        # Keep our own validated models and reference to parameter hook
        self.validated_models = {}
        self._parameter_hook = parameter_hook

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

        # Get all parameter requirements from all pipelines
        all_param_requirements = (
            ParameterModelUtils.get_all_pipeline_param_requirements(
                pipelines, include_default=False
            )
        )

        # Validate each required parameter
        for param_key, expected_type in all_param_requirements.items():
            # support nested lookups like "params:project.database" -> context.params['project']['database']
            raw_value = ParameterModelUtils.get_nested_param(params, param_key)
            if raw_value is None:
                # If param absent, collect problem (could be optional)
                problems.append(
                    {
                        "param_key": param_key,
                        "error": "missing parameter",
                    }
                )
                continue

            # Try to instantiate and validate the model
            validated_instance, error_msg = ParameterModelUtils.instantiate_model(
                param_key, raw_value, expected_type, warn_on_failure=False
            )

            if validated_instance is not None:
                # Store the validated model instance
                self.validated_models[param_key] = validated_instance
            elif error_msg and "Unsupported model type" not in error_msg:
                # Only report real validation failures, not unsupported types
                problems.append(
                    {
                        "param_key": param_key,
                        "error": error_msg,
                    }
                )

        if problems:
            # Format a message and raise so Kedro CLI fails fast
            lines = ["Parameter validation failed:"]
            for p in problems:
                lines.append(f"- param={p['param_key']}: {p['error']}")
            raise RuntimeError("\n".join(lines))

        # Share validated models with parameter hook if it exists
        if self._parameter_hook is not None:
            self._parameter_hook.validated_models.update(self.validated_models)
