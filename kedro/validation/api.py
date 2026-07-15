"""Standalone validation API for catalog-declared validators.

These functions validate catalog datasets on demand, outside the catalog's
load/save funnel. They NEVER raise for validation outcomes — every outcome is
reported as a :class:`ValidationResult` — and explicit calls always validate,
ignoring both the catalog-level and spec-level enabled flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kedro.validation.core import (
    CheckFailure,
    DataValidationError,
    ValidationConfigurationError,
    resolve_validator,
)


class _UnsetType:
    """Sentinel type distinguishing 'no data passed' from ``None`` data."""

    def __repr__(self) -> str:
        return "<unset>"


_UNSET = _UnsetType()


def _json_safe(value: Any) -> Any:
    """Coerce a value to a JSON-safe primitive, falling back to ``repr``."""
    if value is None or isinstance(value, str | bool | int | float):
        return value
    return repr(value)


def _failure_to_dict(failure: CheckFailure) -> dict[str, Any]:
    """Convert a ``CheckFailure`` to a JSON-safe dictionary."""
    return {
        "message": failure.message,
        "check": failure.check,
        "column": failure.column,
        "failure_count": failure.failure_count,
        "failure_examples": [
            _json_safe(example) for example in failure.failure_examples
        ],
        "index": _json_safe(failure.index),
    }


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a single catalog dataset.

    Attributes:
        dataset_name: Name of the validated dataset.
        validator: Class path of the declared validator, if any.
        status: One of ``"passed"``, ``"failed"``, ``"skipped"``
            or ``"errored"``.
        failures: Structured check failures when ``status == "failed"``.
        message: Rendered error/failure message, if any.
        reason: Why validation was skipped, if ``status == "skipped"``.
        error_type: For ``"errored"``: ``"missing_dependency"``,
            ``"unresolvable_validator"`` or ``"dataset_error"``.
        enabled: The spec's enabled flag (explicit calls validate regardless).
        data: The validated/coerced data when ``status == "passed"``.
    """

    dataset_name: str
    validator: str | None
    status: str
    failures: list = field(default_factory=list)
    message: str | None = None
    reason: str | None = None
    error_type: str | None = None
    enabled: bool = True
    data: Any | None = None

    def __bool__(self) -> bool:
        return self.status in ("passed", "skipped")

    def raise_if_failed(self) -> None:
        """Raise ``DataValidationError`` if the result is failed or errored."""
        if self.status in ("failed", "errored"):
            raise DataValidationError(
                self.message
                or f"Validation {self.status} for dataset '{self.dataset_name}'",
                dataset_name=self.dataset_name,
                mode="api",
                validator=self.validator,
                failures=list(self.failures),
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation (excludes ``data``)."""
        return {
            "dataset_name": self.dataset_name,
            "validator": self.validator,
            "status": self.status,
            "failures": [_failure_to_dict(failure) for failure in self.failures],
            "message": self.message,
            "reason": self.reason,
            "error_type": self.error_type,
            "enabled": self.enabled,
        }


def validate_catalog_dataset(  # noqa: PLR0911
    catalog: Any,
    name: str,
    data: Any = _UNSET,
    *,
    on: str = "load",
    version: str | None = None,
) -> ValidationResult:
    """Validate one catalog dataset against its declared validator.

    This NEVER raises for validation outcomes. Explicit calls always validate,
    ignoring ``catalog.validation_enabled`` and the spec's ``enabled`` flag
    (the result carries the spec's ``enabled`` value for information).

    Args:
        catalog: A ``DataCatalog`` (or compatible) instance.
        name: Name of the dataset to validate.
        data: In-memory data to validate. When omitted, the data is loaded
            from the catalog (raw load, bypassing the validation funnel).
        on: Which declared mode to check the validator against
            (``"load"`` or ``"save"``).
        version: Optional dataset version to load when ``data`` is omitted.

    Returns:
        A ``ValidationResult`` describing the outcome.

    Raises:
        ValueError: If ``on`` is invalid, or ``on="save"`` without ``data``.
    """
    if on not in ("load", "save"):
        raise ValueError(f"'on' must be 'load' or 'save', got {on!r}.")
    if on == "save" and data is _UNSET:
        raise ValueError("data must be provided when validating with on='save'.")

    spec = catalog._validator_specs.get(name)
    if spec is None:
        return ValidationResult(
            dataset_name=name,
            validator=None,
            status="skipped",
            reason="no validator declared",
        )

    if on not in spec.on:
        declared = " and ".join(spec.on)
        return ValidationResult(
            dataset_name=name,
            validator=spec.class_path,
            status="skipped",
            reason=f"validator declared for {declared} only",
            enabled=spec.enabled,
        )

    try:
        validator = resolve_validator(spec)
    except ValidationConfigurationError as exc:
        error_type = "unresolvable_validator"
        cause = exc.__cause__
        while cause is not None:
            if isinstance(cause, ModuleNotFoundError):
                error_type = "missing_dependency"
                break
            cause = cause.__cause__
        return ValidationResult(
            dataset_name=name,
            validator=spec.class_path,
            status="errored",
            message=str(exc),
            error_type=error_type,
            enabled=spec.enabled,
        )

    if data is _UNSET:
        try:
            from kedro.io import Version

            dataset = catalog.get(
                name, version=Version(version, None) if version else None
            )
            if dataset is None:
                return ValidationResult(
                    dataset_name=name,
                    validator=spec.class_path,
                    status="errored",
                    message=f"Dataset '{name}' not found in catalog.",
                    error_type="dataset_error",
                    enabled=spec.enabled,
                )
            data = dataset.load()
        except Exception as exc:
            return ValidationResult(
                dataset_name=name,
                validator=spec.class_path,
                status="errored",
                message=str(exc),
                error_type="dataset_error",
                enabled=spec.enabled,
            )

    try:
        validated = validator.validate(data)
    except DataValidationError as exc:
        exc.dataset_name = exc.dataset_name or name
        exc.mode = "api"
        return ValidationResult(
            dataset_name=name,
            validator=spec.class_path,
            status="failed",
            failures=list(exc.failures),
            message=str(exc),
            enabled=spec.enabled,
        )
    except Exception as exc:  # wrap non-DataValidationError like the funnel does
        wrapped = DataValidationError(
            str(exc),
            dataset_name=name,
            mode="api",
            validator=spec.class_path,
        )
        wrapped.__cause__ = exc
        return ValidationResult(
            dataset_name=name,
            validator=spec.class_path,
            status="failed",
            failures=list(wrapped.failures),
            message=str(wrapped),
            enabled=spec.enabled,
        )

    return ValidationResult(
        dataset_name=name,
        validator=spec.class_path,
        status="passed",
        enabled=spec.enabled,
        data=validated,
    )


def validate_catalog(
    catalog: Any, names: list[str] | None = None
) -> dict[str, ValidationResult]:
    """Validate multiple catalog datasets against their declared validators.

    Args:
        catalog: A ``DataCatalog`` (or compatible) instance.
        names: Dataset names to validate. Defaults to every dataset with a
            declared validator.

    Returns:
        Mapping of dataset name to its ``ValidationResult``.
    """
    # TODO(prototype): only explicit `validator:` entries materialised in
    # catalog._validator_specs are enumerated; dataset factory patterns
    # carrying validators are not expanded here (pattern-level enumeration
    # is out of prototype scope).
    if names is None:
        names = list(catalog._validator_specs)
    return {name: validate_catalog_dataset(catalog, name) for name in names}
