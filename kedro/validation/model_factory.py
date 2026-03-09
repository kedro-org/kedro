"""Model factory for instantiating various model types."""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from .exceptions import ModelInstantiationError
from .utils import is_pydantic_class

logger = logging.getLogger(__name__)


def instantiate_model(source_key: str, raw_value: Any, model_type: type) -> Any:
    """Instantiate a typed model from a raw value.

    Supports Pydantic models and dataclasses. Returns the raw value
    unchanged for unsupported types.

    Args:
        source_key: The source key being processed.
        raw_value: The raw value from config.
        model_type: The target model type to instantiate.

    Returns:
        Instantiated model object, or the raw value if unsupported.

    Raises:
        ModelInstantiationError: If instantiation fails.
    """
    try:
        if is_pydantic_class(model_type):
            return _instantiate_pydantic(raw_value, model_type)
        elif dataclasses.is_dataclass(model_type):
            return _instantiate_dataclass(raw_value, model_type)
        else:
            logger.debug(
                "Source '%s' type %s is not a Pydantic model or dataclass, "
                "skipping validation",
                source_key,
                model_type.__name__,
            )
            return raw_value

    except ModelInstantiationError:
        raise
    except Exception as exc:
        raise ModelInstantiationError(
            f"Failed to instantiate {model_type.__name__} for "
            f"source '{source_key}': {exc}"
        ) from exc


def _instantiate_pydantic(raw_value: Any, model_type: type) -> Any:
    """Handle Pydantic model instantiation.

    Note: Requires Pydantic v2+ (uses `model_validate`).
    """
    return model_type.model_validate(raw_value)  # type: ignore[attr-defined]


def _instantiate_dataclass(raw_value: Any, model_type: type) -> Any:
    """Handle dataclass instantiation."""
    if isinstance(raw_value, dict):
        return model_type(**raw_value)
    raise ModelInstantiationError(
        f"Expected dict for dataclass {model_type.__name__}, "
        f"got {type(raw_value).__name__}"
    )
