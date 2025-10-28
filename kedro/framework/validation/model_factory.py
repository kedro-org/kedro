"""Model factory for instantiating various model types."""

from __future__ import annotations

import dataclasses
import inspect
import logging
from typing import Any

from .exceptions import ModelInstantiationError


class ModelFactory:
    """Handles instantiation of various model types like Pydantic models and dataclasses."""

    def __init__(self):
        """Initialize the model factory."""
        self.logger = logging.getLogger(__name__)

    def instantiate(self, source_key: str, raw_value: Any, model_type: type) -> Any:
        """Instantiate model from raw value, raise error on failure.

        Args:
            source_key: The source key being processed
            raw_value: The raw value from source
            model_type: The target model type to instantiate

        Returns:
            Instantiated model object

        Raises:
            ModelInstantiationError: If instantiation fails
        """
        try:
            # Handle Pydantic models
            if self._is_pydantic_model(model_type):
                return self.instantiate_pydantic(raw_value, model_type)

            # Handle dataclasses
            elif dataclasses.is_dataclass(model_type):
                return self.instantiate_dataclass(raw_value, model_type)

            # Not a supported model type - return raw value
            else:
                self.logger.debug(
                    f"Source '{source_key}' type {model_type.__name__} is not a supported model type, using raw value"
                )
                return raw_value

        except Exception as exc:
            error_msg = f"Failed to instantiate {model_type.__name__} for source '{source_key}': {exc}"
            raise ModelInstantiationError(
                error_msg,
                source_key=source_key,
                model_type=model_type,
                original_error=exc,
            ) from exc

    def instantiate_pydantic(self, raw_value: Any, model_type: type) -> Any:
        """Handle Pydantic model instantiation.

        Args:
            raw_value: Raw value
            model_type: Pydantic model type

        Returns:
            Validated Pydantic model instance
        """
        return model_type.model_validate(raw_value)

    def instantiate_dataclass(self, raw_value: Any, model_type: type) -> Any:
        """Handle dataclass instantiation.

        Args:
            raw_value: Raw value
            model_type: Dataclass type

        Returns:
            Instantiated dataclass
        """
        if isinstance(raw_value, dict):
            return model_type(**raw_value)
        else:
            # If raw_value is not a dict, try to instantiate with empty dict
            # This will likely fail but provides a clear error message
            return model_type()

    def _is_pydantic_model(self, model_type: type) -> bool:
        """Check if the given type is a Pydantic model.

        Args:
            model_type: Type to check

        Returns:
            True if it's a Pydantic model, False otherwise
        """
        try:
            import pydantic

            return inspect.isclass(model_type) and issubclass(
                model_type, pydantic.BaseModel
            )
        except ImportError:
            return False
