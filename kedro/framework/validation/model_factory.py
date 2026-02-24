"""Model factory for instantiating various model types."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from .exceptions import ModelInstantiationError
from .utils import is_pydantic_class

logger = logging.getLogger(__name__)


class ModelFactory:
    """Handles instantiation of various model types like Pydantic models and dataclasses.

    Example:
    ```python
    from pydantic import BaseModel


    class ModelOptions(BaseModel):
        test_size: float
        random_state: int


    factory = ModelFactory()
    raw = {"test_size": 0.2, "random_state": 3}
    instance = factory.instantiate("model_options", raw, ModelOptions)
    # instance is ModelOptions(test_size=0.2, random_state=3)
    ```
    """

    def instantiate(self, source_key: str, raw_value: Any, model_type: type) -> Any:
        """Instantiate model from raw value, raise error on failure.

        Supports Pydantic models, Python dataclasses, and falls back to returning
        the raw value for unsupported types (e.g. builtins like ``int``, ``str``).

        Args:
            source_key: The source key being processed (e.g. ``"model_options"``).
            raw_value: The raw value from source (typically a dict from YAML).
            model_type: The target model type to instantiate.

        Returns:
            Instantiated model object, or the raw value if the type is unsupported.

        Raises:
            ModelInstantiationError: If instantiation fails.

        Example:
        ```python
        factory = ModelFactory()
        # Pydantic model
        factory.instantiate("opts", {"x": 1}, MyPydanticModel)
        # Dataclass
        factory.instantiate("cfg", {"name": "a"}, MyDataclass)
        # Unsupported type - returns raw value unchanged
        factory.instantiate("threshold", 0.5, float)  # returns 0.5
        ```
        """
        try:
            if is_pydantic_class(model_type):
                return self._instantiate_pydantic(raw_value, model_type)
            elif dataclasses.is_dataclass(model_type):
                return self._instantiate_dataclass(raw_value, model_type)
            else:
                logger.debug(
                    "Source '%s' type %s is not a supported model type, using raw value",
                    source_key,
                    model_type.__name__,
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

    def _instantiate_pydantic(self, raw_value: Any, model_type: type) -> Any:
        """Handle Pydantic model instantiation.

        Args:
            raw_value: Raw value (typically a dict).
            model_type: Pydantic model type.

        Returns:
            Validated Pydantic model instance.
        """
        return model_type.model_validate(raw_value)  # type: ignore[attr-defined]

    def _instantiate_dataclass(self, raw_value: Any, model_type: type) -> Any:
        """Handle dataclass instantiation.

        Args:
            raw_value: Raw value (typically a dict).
            model_type: Dataclass type.

        Returns:
            Instantiated dataclass.
        """
        if isinstance(raw_value, dict):
            return model_type(**raw_value)
        else:
            return model_type()
