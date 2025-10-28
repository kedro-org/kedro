"""Parameter validation for Kedro sessions."""

from __future__ import annotations

import dataclasses
import inspect
import logging
from typing import Any, get_type_hints

from kedro.framework.hooks import hook_impl


class ParameterValidator:
    """Central parameter validation and model instantiation."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_nested_param(self, params: dict[str, Any], param_key: str) -> Any:
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

    def set_nested_param(
        self, params: dict[str, Any], param_key: str, value: Any
    ) -> None:
        """Set parameter value supporting nested paths"""
        if "." not in param_key:
            params[param_key] = value
            return

        keys = param_key.split(".")
        current = params

        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                # Can't set nested value if intermediate value is not a dict
                return
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def get_all_pipeline_param_requirements(
        self, pipelines, include_default: bool = True
    ) -> dict[str, type]:
        """Extract all parameter requirements from all pipelines."""
        all_param_requirements = {}

        pipeline_dict = dict(pipelines)
        for pipeline_name, pipeline in pipeline_dict.items():
            if not include_default and pipeline_name == "__default__":
                continue

            for node in getattr(pipeline, "nodes", []):
                node_requirements = self.get_node_param_requirements(node)
                all_param_requirements.update(node_requirements)

        return all_param_requirements

    def get_node_param_requirements(self, node) -> dict[str, type]:
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

    def instantiate_model(
        self, param_key: str, raw_value: Any, expected_type: type
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
                # Not a supported model type - return raw value
                return raw_value, None
        except Exception as exc:
            error_msg = f"Failed to instantiate {expected_type.__name__} for param '{param_key}': {exc}"
            return None, error_msg

    def validate_and_transform_params(
        self, params: dict[str, Any], pipelines
    ) -> dict[str, Any]:
        """Validate and transform parameters, returning modified params dict.

        Args:
            params: Original parameters dictionary
            pipelines: Available pipelines to analyze

        Returns:
            Modified parameters dictionary with instantiated models

        Raises:
            RuntimeError: If any parameter validation fails
        """
        # Work on a deep copy to avoid modifying the original
        import copy

        modified_params = copy.deepcopy(params)

        # Get all parameter requirements
        param_requirements = self.get_all_pipeline_param_requirements(
            pipelines, include_default=False
        )

        problems = []
        instantiated_count = 0

        # Process each required parameter
        for param_key, expected_type in param_requirements.items():
            raw_value = self.get_nested_param(params, param_key)

            if raw_value is None:
                problems.append(f"Missing parameter: {param_key}")
                continue

            # Try to instantiate the model
            validated_instance, error_msg = self.instantiate_model(
                param_key, raw_value, expected_type
            )

            if validated_instance is not None and validated_instance is not raw_value:
                # Replace the raw value with the validated model in the params dict
                self.set_nested_param(modified_params, param_key, validated_instance)
                instantiated_count += 1
                self.logger.debug(
                    f"Successfully instantiated {expected_type.__name__} for parameter '{param_key}'"
                )
            elif error_msg:
                problems.append(f"Parameter '{param_key}': {error_msg}")

        if instantiated_count > 0:
            self.logger.info(
                f"Successfully instantiated {instantiated_count} parameter models"
            )

        # Always fail on validation errors - no fallback to raw values
        if problems:
            error_message = "Parameter validation failed:\n" + "\n".join(
                f"- {p}" for p in problems
            )
            raise RuntimeError(error_message)

        return modified_params


class KedroParameterValidationHook:
    """Hook for parameter validation that modifies context parameters directly."""

    def __init__(self):
        self.validator = ParameterValidator()

    @hook_impl
    def after_context_created(self, context) -> None:
        """Validate and transform parameters directly in the context."""
        try:
            from kedro.framework.project import pipelines
        except Exception:
            pipelines = {}

        if not pipelines:
            return

        # Get original parameters
        original_params = dict(context.params)

        # Validate and transform parameters - fail fast on validation errors
        try:
            transformed_params = self.validator.validate_and_transform_params(
                original_params, pipelines
            )

            # Store transformed params directly on the context instance
            context._transformed_params = transformed_params

            # Store reference to original params method
            if not hasattr(context, "_original_params_method"):
                context._original_params_method = context.__class__.params.fget

            # Create a new property that returns transformed params if available
            def patched_params(self):
                if hasattr(self, "_transformed_params"):
                    return self._transformed_params
                else:
                    return self._original_params_method(self)

            # Replace the property on the class
            context.__class__.params = property(patched_params)

        except Exception as exc:
            # Re-raise validation errors - fail fast
            self.validator.logger.error(f"Parameter validation failed: {exc}")
            raise
