"""Parameter validator using type extraction and model instantiation."""

from __future__ import annotations

import copy
import logging
from typing import Any

from kedro.framework.validation import (
    ModelFactory,
    ParameterSourceFilter,
    TypeExtractor,
    ValidationError,
)


class ParameterValidator:
    """Parameter validator that combines type extraction and model instantiation."""

    def __init__(self) -> None:
        """Initialize parameter validator."""
        self.type_extractor = TypeExtractor(ParameterSourceFilter())
        self.model_factory = ModelFactory()
        self.logger = logging.getLogger(__name__)

    def get_pipeline_requirements(self) -> dict[str, type]:
        """Get all parameter type requirements from available pipelines.

        Returns:
            Dictionary mapping parameter keys to their expected types
        """
        return self.type_extractor.extract_types_from_pipelines()

    def apply_validation(self, raw_params: dict, requirements: dict) -> dict:
        """Apply validation to parameters and return transformed dictionary.

        Args:
            raw_params: Original parameters dictionary
            requirements: Dictionary mapping parameter keys to expected types

        Returns:
            Transformed parameters dictionary with validated models

        Raises:
            ValidationError: If validation fails
        """
        # Work on a deep copy to avoid modifying the original
        transformed_params = copy.deepcopy(raw_params)

        validation_errors = []
        instantiated_count = 0

        # Process each parameter requirement
        for param_key, expected_type in requirements.items():
            try:
                # Get the raw parameter value
                raw_value = self.type_extractor.resolve_nested_path(
                    raw_params, param_key
                )

                if raw_value is None:
                    # We shouldn't count this as an error because users might not be running the pipeline or the params is optional.
                    self.logger.debug(
                        f"Parameter '{param_key}' not found in config, skipping validation"
                    )
                    continue

                # Attempt to instantiate the model
                validated_instance = self.model_factory.instantiate(
                    param_key, raw_value, expected_type
                )

                # Only update if we got a different object (i.e., actual model instantiation occurred)
                if validated_instance is not raw_value:
                    self.type_extractor.set_nested_value(
                        transformed_params, param_key, validated_instance
                    )
                    instantiated_count += 1
                    self.logger.debug(
                        f"Successfully instantiated {expected_type.__name__} for parameter '{param_key}'"
                    )

            except Exception as exc:
                error_msg = f"Parameter '{param_key}': {exc}"
                validation_errors.append(error_msg)
                self.logger.error(error_msg)

        # Log success summary
        if instantiated_count > 0:
            self.logger.info(
                f"Successfully instantiated {instantiated_count} parameter models"
            )

        # Handle validation errors
        if validation_errors:
            error_message = "Parameter validation failed:\n" + "\n".join(
                f"- {error}" for error in validation_errors
            )
            raise ValidationError(error_message, errors=validation_errors)

        return transformed_params

    def validate_raw_params(self, raw_params: dict) -> dict[str, Any]:
        """Validate raw parameters before they are assigned to context.

        Args:
            raw_params: Parameters from config loader includes config and runtime parameters

        Returns:
            Dictionary of validated and transformed parameters

        Raises:
            ValidationError: If validation fails
        """
        # Get parameter requirements
        requirements = self.get_pipeline_requirements()

        if not requirements:
            self.logger.info(
                "No typed parameter requirements found, returning original parameters"
            )
            return raw_params

        # Apply validation and transformation
        return self.apply_validation(raw_params, requirements)
