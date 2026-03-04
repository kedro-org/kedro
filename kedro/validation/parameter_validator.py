"""Parameter validator using type extraction and model instantiation."""

from __future__ import annotations

import copy
import logging
from typing import Any

from .exceptions import ValidationError
from .model_factory import ModelFactory
from .source_filters import ParameterSourceFilter
from .type_extractor import TypeExtractor

logger = logging.getLogger(__name__)


class ParameterValidator:
    """Orchestrates type extraction and model instantiation for parameters."""

    def __init__(self) -> None:
        """Initialize parameter validator."""
        self.type_extractor = TypeExtractor(ParameterSourceFilter())
        self.model_factory = ModelFactory()

    def get_pipeline_requirements(self) -> dict[str, type]:
        """Get all parameter type requirements from available pipelines."""
        return self.type_extractor.extract_types_from_pipelines()

    def apply_validation(self, raw_params: dict, requirements: dict) -> dict:
        """Apply validation to parameters and return transformed dictionary.

        Args:
            raw_params: Original parameters dictionary.
            requirements: Dictionary mapping parameter keys to expected types.

        Returns:
            Transformed parameters dictionary with validated models.

        Raises:
            ValidationError: If any parameter fails validation.
        """
        transformed_params = copy.deepcopy(raw_params)

        validation_errors = []
        instantiated_count = 0

        for param_key, expected_type in requirements.items():
            try:
                raw_value = self.type_extractor.resolve_nested_path(
                    raw_params, param_key
                )

                if raw_value is None:
                    logger.debug(
                        "Parameter '%s' not found in config, skipping validation",
                        param_key,
                    )
                    continue

                validated_instance = self.model_factory.instantiate(
                    param_key, raw_value, expected_type
                )

                if validated_instance is not raw_value:
                    self.type_extractor.set_nested_value(
                        transformed_params, param_key, validated_instance
                    )
                    instantiated_count += 1
                    logger.debug(
                        "Successfully instantiated %s for parameter '%s'",
                        expected_type.__name__,
                        param_key,
                    )

            except Exception as exc:
                error_msg = f"Parameter '{param_key}': {exc}"
                validation_errors.append(error_msg)
                logger.error(error_msg)

        if instantiated_count > 0:
            logger.debug(
                "Successfully instantiated %d parameter models", instantiated_count
            )

        if validation_errors:
            error_message = "Parameter validation failed:\n" + "\n".join(
                f"- {error}" for error in validation_errors
            )
            raise ValidationError(error_message)

        return transformed_params

    def validate_raw_params(self, raw_params: dict) -> dict[str, Any]:
        """Validate raw parameters and return transformed dictionary.

        Args:
            raw_params: Parameters from config loader (merged with runtime params).

        Returns:
            Validated and transformed parameters.

        Raises:
            ValidationError: If validation fails.
        """
        requirements = self.get_pipeline_requirements()

        if not requirements:
            logger.info(
                "No typed parameter requirements found, returning original parameters"
            )
            return raw_params

        return self.apply_validation(raw_params, requirements)
