"""On-demand validation of catalog datasets, outside the load/save funnel.

These functions never raise for validation outcomes — every outcome is
reported as a `ValidationResult` — and explicit calls always validate,
ignoring both the catalog-level and spec-level enabled flags.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

from kedro.validation.core import _VALID_MODES, resolve_validator
from kedro.validation.exceptions import (
    CheckFailure,
    DataValidationError,
    ValidationConfigurationError,
)


class _UnsetType:
    """Sentinel type distinguishing 'no data passed' from `None` data."""

    def __repr__(self) -> str:
        return "<unset>"


_UNSET = _UnsetType()

ValidationStatus = Literal["passed", "failed", "skipped", "errored"]


def _json_safe(value: Any) -> Any:
    """Coerce a value to a strict-JSON-safe primitive, falling back to `repr`.

    Non-finite floats become strings, since `NaN` and `Infinity` are not
    valid JSON and would break strict parsers.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, str | bool | int | float):
        return value
    return repr(value)


def _failure_to_dict(failure: CheckFailure) -> dict[str, Any]:
    """Convert a `CheckFailure` to a JSON-safe dictionary."""
    return {
        "message": failure.message,
        "check": failure.check,
        "column": failure.column,
        "failure_count": failure.failure_count,
        "failure_examples": [
            _json_safe(example) for example in failure.failure_examples
        ],
    }


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a single catalog dataset.

    Truthy when the dataset is not known to be bad (`passed` or `skipped`).

    Attributes:
        dataset_name: Name of the validated dataset.
        validator: Class path of the declared validator, if any.
        status: One of `"passed"`, `"failed"`, `"skipped"` or `"errored"`.
        failures: Structured check failures when `status == "failed"`.
        message: Rendered error/failure message, if any.
        reason: Why validation was skipped, if `status == "skipped"`.
        error_type: For `"errored"`: `"missing_dependency"`,
            `"unresolvable_validator"` or `"dataset_error"`.
        enabled: The spec's enabled flag (explicit calls validate regardless).
        data: The validated, possibly coerced, data when `status == "passed"`.
    """

    dataset_name: str
    validator: str | None
    status: ValidationStatus
    failures: list[CheckFailure] = field(default_factory=list)
    message: str | None = None
    reason: str | None = None
    error_type: str | None = None
    enabled: bool = True
    data: Any | None = None

    def __bool__(self) -> bool:
        return self.status in ("passed", "skipped")

    def raise_if_failed(self) -> None:
        """Raise `DataValidationError` if the result is failed or errored."""
        if self.status in ("failed", "errored"):
            raise DataValidationError(
                self.message
                or f"Validation {self.status} for dataset '{self.dataset_name}'",
                dataset_name=self.dataset_name,
                mode="api",
                validator=self.validator,
                failures=list(self.failures),
                error_type=self.error_type,
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation (excludes `data`)."""
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


def _error_type_for(exc: ValidationConfigurationError) -> str:
    """Classify a resolution failure by walking its cause chain."""
    cause = exc.__cause__
    while cause is not None:
        if isinstance(cause, ModuleNotFoundError):
            return "missing_dependency"
        cause = cause.__cause__
    return "unresolvable_validator"


def _lookup_spec(catalog: Any, name: str) -> tuple[Any, ValidationResult | None]:
    """Look up the parsed validator spec for `name`.

    Dataset factory patterns only capture their validator spec when the
    dataset is materialised, so an unknown name that the catalog can resolve
    is materialised first. Returns the spec (or `None`) and an early
    `ValidationResult` when the dataset is missing or cannot be created.
    """
    spec = catalog.validator_specs.get(name)
    if spec is not None:
        return spec, None
    try:
        in_catalog = name in catalog
    except Exception as exc:
        return None, ValidationResult(
            dataset_name=name,
            validator=None,
            status="errored",
            message=(
                f"Could not check whether dataset '{name}' exists "
                f"in the catalog: {exc}"
            ),
            error_type="dataset_error",
        )
    if not in_catalog:
        return None, ValidationResult(
            dataset_name=name,
            validator=None,
            status="errored",
            message=f"Dataset '{name}' not found in the catalog.",
            error_type="dataset_error",
        )
    try:
        catalog.get(name)
    except Exception as exc:
        return None, ValidationResult(
            dataset_name=name,
            validator=None,
            status="errored",
            message=f"Dataset '{name}' exists but could not be created: {exc}",
            error_type="dataset_error",
        )
    return catalog.validator_specs.get(name), None


def _gate_on_declared_modes(spec: Any, name: str, on: str) -> ValidationResult | None:
    """Skip when the validator is not declared for the requested mode."""
    if on in spec.on:
        return None
    declared = " and ".join(spec.on)
    return ValidationResult(
        dataset_name=name,
        validator=spec.class_path,
        status="skipped",
        reason=f"validator declared for {declared} only",
        enabled=spec.enabled,
    )


def _resolve_or_error(spec: Any, name: str) -> tuple[Any, ValidationResult | None]:
    """Resolve the validator, reporting resolution failures as `errored`."""
    try:
        return resolve_validator(spec), None
    except ValidationConfigurationError as exc:
        return None, ValidationResult(
            dataset_name=name,
            validator=spec.class_path,
            status="errored",
            message=str(exc),
            error_type=_error_type_for(exc),
            enabled=spec.enabled,
        )


def _load_or_error(
    catalog: Any, spec: Any, name: str, version: str | None
) -> tuple[Any, ValidationResult | None]:
    """Load the dataset's data, reporting load failures as `errored`."""
    try:
        from kedro.io import Version

        dataset = catalog.get(name, version=Version(version, None) if version else None)
        if dataset is None:
            return None, ValidationResult(
                dataset_name=name,
                validator=spec.class_path,
                status="errored",
                message=f"Dataset '{name}' not found in catalog.",
                error_type="dataset_error",
                enabled=spec.enabled,
            )
        return dataset.load(), None
    except Exception as exc:
        return None, ValidationResult(
            dataset_name=name,
            validator=spec.class_path,
            status="errored",
            message=str(exc),
            error_type="dataset_error",
            enabled=spec.enabled,
        )


def _apply_validator(
    validator: Any, spec: Any, name: str, data: Any
) -> ValidationResult:
    """Run the validator on `data` and report `passed` or `failed`."""
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
    except Exception as exc:
        # Any other raise counts as a validation failure, matching the funnel.
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


def validate_dataset(  # noqa: PLR0911
    catalog: Any,
    name: str,
    data: Any = _UNSET,
    *,
    on: str = "load",
    version: str | None = None,
) -> ValidationResult:
    """Validate one catalog dataset against its declared validator.

    This never raises for validation outcomes. Explicit calls always
    validate, ignoring `catalog.validation_enabled` and the spec's
    `enabled` flag (the result carries the spec's `enabled` value for
    information). The spec's `severity` is not applied either: a failing
    validator declared with `severity: warn` reports `status="failed"`
    here, where `catalog.load()` would log a warning and continue.

    Args:
        catalog: A `DataCatalog` (or compatible) instance.
        name: Name of the dataset to validate.
        data: In-memory data to validate. When omitted, the data is loaded
            from the catalog (raw load, bypassing the validation funnel).
        on: Which declared mode to check the validator against
            (`"load"` or `"save"`).
        version: Optional dataset version to load when `data` is omitted.

    Returns:
        A `ValidationResult` describing the outcome.

    Raises:
        ValueError: If `on` is invalid, or `on="save"` without `data`.
    """
    if on not in _VALID_MODES:
        raise ValueError(f"'on' must be 'load' or 'save', got {on!r}.")
    if on == "save" and data is _UNSET:
        raise ValueError("data must be provided when validating with on='save'.")

    if getattr(catalog, "validator_specs", None) is None:
        return ValidationResult(
            dataset_name=name,
            validator=None,
            status="skipped",
            reason="catalog does not support declared validators",
        )

    spec, early_result = _lookup_spec(catalog, name)
    if early_result is not None:
        return early_result
    if spec is None:
        return ValidationResult(
            dataset_name=name,
            validator=None,
            status="skipped",
            reason="no validator declared",
        )

    skipped = _gate_on_declared_modes(spec, name, on)
    if skipped is not None:
        return skipped

    validator, errored = _resolve_or_error(spec, name)
    if errored is not None:
        return errored

    if data is _UNSET:
        data, errored = _load_or_error(catalog, spec, name, version)
        if errored is not None:
            return errored

    return _apply_validator(validator, spec, name, data)


def validate_catalog(
    catalog: Any, names: list[str] | None = None
) -> dict[str, ValidationResult]:
    """Validate multiple catalog datasets against their declared validators.

    Batch validation always checks against the `load` declaration, because
    save-mode validation needs in-memory data that a batch call cannot
    supply. Validators declared with `on: [save]` only are reported as
    `skipped`; use `validate_dataset` with `data=` and `on="save"` to check
    those.

    Args:
        catalog: A `DataCatalog` (or compatible) instance.
        names: Dataset names to validate. Defaults to every dataset whose
            validator spec has been captured — explicit catalog entries, plus
            any dataset factory entries already materialised. Pass names
            explicitly to include factory datasets that have not been
            materialised yet.

    Returns:
        Mapping of dataset name to its `ValidationResult`.
    """
    if names is None:
        names = sorted(getattr(catalog, "validator_specs", None) or ())
    return {name: validate_dataset(catalog, name) for name in names}
