"""Parameter validator using type extraction and model instantiation."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any

from .exceptions import ParameterValidationError
from .model_factory import instantiate_model
from .type_extractor import TypeExtractor
from .utils import resolve_nested_dict_path, set_nested_dict_value

if TYPE_CHECKING:
    from kedro.pipeline import Pipeline

logger = logging.getLogger(__name__)


class ParameterValidator:
    """Orchestrates type extraction and model instantiation for parameters."""

    def __init__(self, pipelines: dict[str, Pipeline]) -> None:
        """Initialise parameter validator.

        Args:
            pipelines: Dictionary of registered pipelines to inspect for type hints.
        """
        self.type_extractor = TypeExtractor(pipelines)

    def _apply_validation(self, raw_params: dict, requirements: dict) -> dict:
        """Apply validation to parameters and return transformed dictionary.

        Args:
            raw_params: Original parameters dictionary.
            requirements: Dictionary mapping parameter keys to expected types.

        Returns:
            Transformed parameters dictionary with validated models.

        Raises:
            ParameterValidationError: If any parameter fails validation.
        """
        transformed_params = copy.deepcopy(raw_params)

        validation_errors = []
        instantiated_count = 0

        for param_key, expected_type in requirements.items():
            try:
                raw_value = resolve_nested_dict_path(raw_params, param_key)

                if raw_value is None:
                    logger.debug(
                        "Parameter '%s' not found in config, skipping validation",
                        param_key,
                    )
                    continue

                validated_instance = instantiate_model(
                    param_key, raw_value, expected_type
                )

                if validated_instance is not raw_value:
                    set_nested_dict_value(
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
            raise ParameterValidationError(error_message)

        return transformed_params

    def validate_raw_params(self, raw_params: dict) -> dict[str, Any]:
        """Validate raw parameters and return transformed dictionary.

        Args:
            raw_params: Parameters from config loader (merged with runtime params).

        Returns:
            Validated and transformed parameters.

        Raises:
            ParameterValidationError: If validation fails.
        """
        requirements = self.type_extractor.extract_types_from_pipelines()

        if not requirements:
            logger.info(
                "No typed parameter requirements found, returning original parameters"
            )
            return raw_params

        return self._apply_validation(raw_params, requirements)
